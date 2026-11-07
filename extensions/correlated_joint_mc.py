"""Dependency-preserving combo and joint Monte Carlo research engine.

Caller supplies locked complete marginal count PMFs and a pre-event latent
Gaussian-copula correlation matrix. The matrix is an input model assumption;
this module does not estimate or calibrate it. Sportsbook prices are forbidden.
"""
import bisect
import hashlib
import json
import math
import random
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence

from .underperformance import num, validated_pmf

SCENARIOS=("baseline","adversarial","scenario")
COMPARATORS={"GE","GT","LT","LE"}
SHA64=set("0123456789abcdef")


def _clock(value: Any, field: str):
    if not isinstance(value,str) or not value.strip():
        raise ValueError(f"{field} timezone-aware ISO time required")
    try:
        dt=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} invalid ISO time") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError(f"{field} timezone-aware ISO time required")
    return dt.astimezone(timezone.utc)


def _sha(value: Any, field: str):
    if (
        not isinstance(value,str) or len(value)!=64
        or any(ch not in SHA64 for ch in value)
    ):
        raise ValueError(f"{field} lowercase SHA-256 required")
    return value


def _cholesky(matrix):
    n=len(matrix)
    out=[[0.0]*n for _ in range(n)]
    for i in range(n):
        for j in range(i+1):
            value=matrix[i][j]-sum(out[i][k]*out[j][k] for k in range(j))
            if i==j:
                if value<=1e-12:
                    raise ValueError("latent correlation matrix must be positive definite")
                out[i][j]=math.sqrt(value)
            else:
                out[i][j]=value/out[j][j]
    return out


def _joint_model(raw: Mapping[str,Any]):
    required={
        "variables","variable_order","latent_correlation",
        "model_locked_at","source_evidence_sha256",
    }
    if not isinstance(raw,Mapping) or set(raw)!=required:
        raise ValueError("exact joint model schema required")
    variables=raw["variables"]
    order=raw["variable_order"]
    if not isinstance(variables,Mapping) or len(variables)<1:
        raise ValueError("variables mapping required")
    if (
        not isinstance(order,list) or len(order)!=len(variables)
        or len(order)!=len(set(order)) or set(order)!=set(variables)
        or any(not isinstance(x,str) or not x.strip() for x in order)
    ):
        raise ValueError("variable_order must exactly cover unique variable IDs")
    pmfs={var:validated_pmf(variables[var]) for var in order}
    matrix_raw=raw["latent_correlation"]
    if not isinstance(matrix_raw,list) or len(matrix_raw)!=len(order):
        raise ValueError("square latent correlation matrix required")
    matrix=[]
    for i,row in enumerate(matrix_raw):
        if not isinstance(row,list) or len(row)!=len(order):
            raise ValueError("square latent correlation matrix required")
        vals=[float(num(x)) for x in row]
        if any(not -1<=x<=1 for x in vals):
            raise ValueError("correlations must be in [-1,1]")
        if abs(vals[i]-1.0)>1e-12:
            raise ValueError("correlation matrix diagonal must equal one")
        matrix.append(vals)
    for i in range(len(order)):
        for j in range(len(order)):
            if abs(matrix[i][j]-matrix[j][i])>1e-12:
                raise ValueError("correlation matrix must be symmetric")
    chol=_cholesky(matrix)
    locked=_clock(raw["model_locked_at"],"model_locked_at")
    evidence=_sha(raw["source_evidence_sha256"],"source_evidence_sha256")
    return {
        "variables":pmfs,
        "variable_order":list(order),
        "latent_correlation":matrix,
        "cholesky":chol,
        "model_locked_at":locked.isoformat(),
        "source_evidence_sha256":evidence,
    }


def _leg(raw: Mapping[str,Any], variable_ids):
    required={"leg_id","terms","comparator","threshold"}
    if not isinstance(raw,Mapping) or set(raw)!=required:
        raise ValueError("exact joint leg schema required")
    leg_id=raw["leg_id"]
    if not isinstance(leg_id,str) or not leg_id.strip():
        raise ValueError("nonblank leg_id required")
    terms=raw["terms"]
    if not isinstance(terms,Mapping) or not terms:
        raise ValueError("nonempty leg terms required")
    normalized={}
    for var,coef_raw in terms.items():
        if var not in variable_ids:
            raise ValueError("leg references unknown variable")
        coef=num(coef_raw)
        if coef<=0:
            raise ValueError("leg coefficients must be positive")
        normalized[var]=coef
    comparator=raw["comparator"]
    if comparator not in COMPARATORS:
        raise ValueError("unsupported leg comparator")
    threshold=num(raw["threshold"])
    if threshold<0:
        raise ValueError("nonnegative leg threshold required")
    return {
        "leg_id":leg_id,
        "terms":normalized,
        "comparator":comparator,
        "threshold":threshold,
    }


def _legs(raw: Sequence[Mapping[str,Any]], variable_ids):
    if not isinstance(raw,(list,tuple)) or not raw:
        raise ValueError("nonempty legs required")
    result=[_leg(row,variable_ids) for row in raw]
    ids=[row["leg_id"] for row in result]
    if len(ids)!=len(set(ids)):
        raise ValueError("unique leg_id required")
    return result


def _cdf(pmf):
    items=sorted(pmf.items())
    outcomes=[outcome for outcome,_ in items]
    cumulative=[]
    total=0.0
    for _,mass in items:
        total+=float(mass)
        cumulative.append(total)
    cumulative[-1]=1.0
    return outcomes,cumulative


def _draw_joint(model,rng,prepared):
    eps=[rng.gauss(0.0,1.0) for _ in model["variable_order"]]
    values={}
    for i,var in enumerate(model["variable_order"]):
        z=sum(model["cholesky"][i][k]*eps[k] for k in range(i+1))
        u=0.5*(1.0+math.erf(z/math.sqrt(2.0)))
        if u>=1.0:
            u=math.nextafter(1.0,0.0)
        elif u<0.0:
            u=0.0
        outcomes,cumulative=prepared[var]
        index=bisect.bisect_left(cumulative,u)
        if index>=len(outcomes):
            index=len(outcomes)-1
        values[var]=outcomes[index]
    return values


def _settle(value: Decimal, comparator: str, threshold: Decimal):
    if comparator=="GE":
        return "HIT" if value>=threshold else "MISS"
    if comparator=="LE":
        return "HIT" if value<=threshold else "MISS"
    if value==threshold:
        return "PUSH"
    if comparator=="GT":
        return "HIT" if value>threshold else "MISS"
    return "HIT" if value<threshold else "MISS"


def _leg_value(leg,values):
    return sum(
        (coef*Decimal(values[var]) for var,coef in leg["terms"].items()),
        Decimal(0),
    )


def _canonical_model(model):
    return {
        "variables":{
            var:[(outcome,str(mass)) for outcome,mass in sorted(model["variables"][var].items())]
            for var in model["variable_order"]
        },
        "variable_order":model["variable_order"],
        "latent_correlation":[[str(x) for x in row] for row in model["latent_correlation"]],
        "model_locked_at":model["model_locked_at"],
        "source_evidence_sha256":model["source_evidence_sha256"],
    }


def _canonical_legs(legs):
    return [
        {
            "leg_id":leg["leg_id"],
            "terms":{var:str(coef) for var,coef in sorted(leg["terms"].items())},
            "comparator":leg["comparator"],
            "threshold":str(leg["threshold"]),
        }
        for leg in legs
    ]


def _leg_definition_sha(legs):
    return hashlib.sha256(
        json.dumps(
            _canonical_legs(legs),sort_keys=True,separators=(",",":"),allow_nan=False
        ).encode()
    ).hexdigest()


def _scenario_receipt_body(receipt):
    keys=(
        "trials_each","seeds","joint_probability_by_scenario",
        "scenario_floor_joint_probability","leg_hit_probability_floor",
        "dominant_failure_leg_by_scenario","leg_definition_sha256","variable_ids",
    )
    return {key:receipt.get(key) for key in keys}


def decompose_combo_leg(
    raw_model: Mapping[str,Any],
    raw_leg: Mapping[str,Any],
) -> Dict[str,Any]:
    """Describe a combo leg's locked components and latent dependence."""
    model=_joint_model(raw_model)
    leg=_leg(raw_leg,set(model["variable_order"]))
    if len(leg["terms"])<2:
        raise ValueError("combo decomposition requires at least two terms")
    index={var:i for i,var in enumerate(model["variable_order"])}
    terms=[]
    for var,coef in leg["terms"].items():
        pmf=model["variables"][var]
        mean=sum((Decimal(outcome)*mass for outcome,mass in pmf.items()),Decimal(0))
        terms.append({
            "variable_id":var,
            "coefficient":str(coef),
            "marginal_mean":float(mean),
            "mean_contribution":float(coef*mean),
        })
    pairs=[]
    vars_=list(leg["terms"])
    for i in range(len(vars_)):
        for j in range(i+1,len(vars_)):
            a,b=vars_[i],vars_[j]
            corr=model["latent_correlation"][index[a]][index[b]]
            pairs.append({"a":a,"b":b,"latent_correlation":corr})
    return {
        "mode":"COMBO_PROP_COMPONENT_DECOMPOSITION",
        "leg_id":leg["leg_id"],
        "terms":terms,
        "pairwise_latent_correlations":pairs,
        "max_absolute_latent_correlation":max(abs(x["latent_correlation"]) for x in pairs),
        "correlation_required":any(abs(x["latent_correlation"])>1e-12 for x in pairs),
        "market_price_inputs_used":False,
        "calibration_verified":False,
        "forecast_status":"HOLD",
        "wager_status":"NOT APPROVED",
    }


def simulate_joint_model(
    raw_model: Mapping[str,Any],
    raw_legs: Sequence[Mapping[str,Any]],
    *,
    trials: int,
    seed: int,
    label: str,
) -> Dict[str,Any]:
    """Simulate all variables/legs jointly under one locked dependence model."""
    if type(trials) is not int or not 100000<=trials<=2000000:
        raise ValueError("100000..2000000 joint trials required")
    if type(seed) is not int or not 0<=seed<2**63:
        raise ValueError("deterministic integer seed required")
    if not isinstance(label,str) or not label.strip():
        raise ValueError("simulation label required")
    model=_joint_model(raw_model)
    legs=_legs(raw_legs,set(model["variable_order"]))
    prepared={var:_cdf(model["variables"][var]) for var in model["variable_order"]}
    rng=random.Random(seed)
    hit={leg["leg_id"]:0 for leg in legs}
    push={leg["leg_id"]:0 for leg in legs}
    miss={leg["leg_id"]:0 for leg in legs}
    all_hit=0
    any_push_no_miss=0
    independent_single_miss=0
    failure_clusters=Counter()

    for _ in range(trials):
        values=_draw_joint(model,rng,prepared)
        states={}
        for leg in legs:
            state=_settle(_leg_value(leg,values),leg["comparator"],leg["threshold"])
            states[leg["leg_id"]]=state
            if state=="HIT":
                hit[leg["leg_id"]]+=1
            elif state=="PUSH":
                push[leg["leg_id"]]+=1
            else:
                miss[leg["leg_id"]]+=1
        missed=tuple(sorted(k for k,v in states.items() if v=="MISS"))
        pushed=tuple(sorted(k for k,v in states.items() if v=="PUSH"))
        if not missed and not pushed:
            all_hit+=1
        elif not missed and pushed:
            any_push_no_miss+=1
        if len(missed)==1:
            independent_single_miss+=1
        if missed:
            failure_clusters[missed]+=1

    used=sorted({var for leg in legs for var in leg["terms"]})
    idx={var:i for i,var in enumerate(model["variable_order"])}
    offdiag=[
        abs(model["latent_correlation"][idx[a]][idx[b]])
        for i,a in enumerate(used) for b in used[i+1:]
    ]
    leg_rows={}
    for leg in legs:
        lid=leg["leg_id"]
        leg_rows[lid]={
            "hits":hit[lid],"pushes":push[lid],"misses":miss[lid],
            "hit_rate":hit[lid]/trials,
            "push_rate":push[lid]/trials,
            "miss_rate":miss[lid]/trials,
        }
    dominant=max(leg_rows,key=lambda lid:leg_rows[lid]["miss_rate"])
    top_clusters=[
        {
            "missed_legs":list(cluster),
            "count":count,
            "rate":count/trials,
        }
        for cluster,count in failure_clusters.most_common(10)
    ]
    canonical={
        "model":_canonical_model(model),
        "legs":_canonical_legs(legs),
        "trials":trials,"seed":seed,"label":label,
    }
    input_sha=hashlib.sha256(
        json.dumps(canonical,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    ).hexdigest()
    code_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    return {
        "mode":"DEPENDENCY_PRESERVING_JOINT_MC",
        "simulation_label":label,
        "simulation_kind":"GAUSSIAN_COPULA_DISCRETE_MARGINAL_RESEARCH",
        "trials":trials,
        "seed":seed,
        "input_sha256":input_sha,
        "code_sha256":code_sha,
        "model_locked_at":model["model_locked_at"],
        "source_evidence_sha256":model["source_evidence_sha256"],
        "legs":leg_rows,
        "all_legs_hit":all_hit,
        "joint_probability":all_hit/trials,
        "any_push_no_miss":any_push_no_miss,
        "any_push_no_miss_rate":any_push_no_miss/trials,
        "single_miss_trials":independent_single_miss,
        "single_miss_rate":independent_single_miss/trials,
        "dominant_failure_leg":dominant,
        "top_failure_clusters":top_clusters,
        "mean_absolute_latent_correlation":sum(offdiag)/len(offdiag) if offdiag else 0.0,
        "max_absolute_latent_correlation":max(offdiag) if offdiag else 0.0,
        "joint_probability_is_direct_all_hit_frequency":True,
        "individual_probabilities_multiplied":False,
        "market_price_inputs_used":False,
        "calibration_verified":False,
        "forecast_status":"HOLD",
        "wager_status":"NOT APPROVED",
    }


def compare_combo_correlated_vs_independent(
    raw_model: Mapping[str,Any],
    raw_combo_leg: Mapping[str,Any],
    *,
    trials: int,
    correlated_seed: int,
    independent_seed: int,
) -> Dict[str,Any]:
    """Quantify how much the latent dependence assumption moves a combo hit rate."""
    if correlated_seed==independent_seed:
        raise ValueError("correlated and independent seeds must differ")
    model=_joint_model(raw_model)
    leg=_leg(raw_combo_leg,set(model["variable_order"]))
    if len(leg["terms"])<2:
        raise ValueError("combo comparison requires at least two terms")
    correlated=simulate_joint_model(
        raw_model,[raw_combo_leg],trials=trials,seed=correlated_seed,label="COMBO_CORRELATED")
    identity={
        "variables":{
            var:{str(k):str(v) for k,v in model["variables"][var].items()}
            for var in model["variable_order"]
        },
        "variable_order":model["variable_order"],
        "latent_correlation":[
            [1 if i==j else 0 for j in range(len(model["variable_order"]))]
            for i in range(len(model["variable_order"]))
        ],
        "model_locked_at":model["model_locked_at"],
        "source_evidence_sha256":model["source_evidence_sha256"],
    }
    independent=simulate_joint_model(
        identity,[raw_combo_leg],trials=trials,seed=independent_seed,label="COMBO_INDEPENDENT_DIAGNOSTIC")
    lid=leg["leg_id"]
    pc=correlated["legs"][lid]["hit_rate"]
    pi=independent["legs"][lid]["hit_rate"]
    return {
        "mode":"COMBO_DEPENDENCE_DIAGNOSTIC",
        "leg_id":lid,
        "correlated_hit_rate":pc,
        "independent_hit_rate":pi,
        "correlation_effect_on_hit_rate":pc-pi,
        "correlated_run":correlated,
        "independent_run":independent,
        "calibration_verified":False,
        "forecast_status":"HOLD",
        "wager_status":"NOT APPROVED",
    }


def run_three_scenario_joint_mc(
    models: Mapping[str,Mapping[str,Any]],
    raw_legs: Sequence[Mapping[str,Any]],
    *,
    trials: int,
    seeds: Mapping[str,int],
) -> Dict[str,Any]:
    """Run V7 MC-1/2/3 dependency-preserving joint scenario simulations."""
    if not isinstance(models,Mapping) or set(models)!=set(SCENARIOS):
        raise ValueError("baseline/adversarial/scenario joint models required")
    if not isinstance(seeds,Mapping) or set(seeds)!=set(SCENARIOS):
        raise ValueError("baseline/adversarial/scenario seeds required")
    if any(type(v) is not int for v in seeds.values()) or len(set(seeds.values()))!=3:
        raise ValueError("three distinct integer seeds required")
    canonical_leg_ids=None
    variable_set=None
    runs={}
    for name in SCENARIOS:
        model=_joint_model(models[name])
        legs=_legs(raw_legs,set(model["variable_order"]))
        ids=[leg["leg_id"] for leg in legs]
        if canonical_leg_ids is None:
            canonical_leg_ids=ids
            variable_set=set(model["variable_order"])
        elif ids!=canonical_leg_ids or set(model["variable_order"])!=variable_set:
            raise ValueError("scenario leg and variable universes must match")
        runs[name]=simulate_joint_model(
            models[name],raw_legs,trials=trials,seed=seeds[name],
            label={"baseline":"MC1_BASELINE","adversarial":"MC2_ADVERSARIAL","scenario":"MC3_SCENARIO_CORRELATION"}[name])
    joint={name:runs[name]["joint_probability"] for name in SCENARIOS}
    leg_floor={}
    for lid in canonical_leg_ids:
        leg_floor[lid]=min(runs[name]["legs"][lid]["hit_rate"] for name in SCENARIOS)
    receipt={
        "mode":"THREE_SCENARIO_DEPENDENCY_PRESERVING_JOINT_MC",
        "trials_each":trials,
        "seeds":dict(seeds),
        "runs":runs,
        "joint_probability_by_scenario":joint,
        "scenario_floor_joint_probability":min(joint.values()),
        "leg_hit_probability_floor":leg_floor,
        "dominant_failure_leg_by_scenario":{
            name:runs[name]["dominant_failure_leg"] for name in SCENARIOS
        },
        "leg_definition_sha256":_leg_definition_sha(legs),
        "variable_ids":sorted(variable_set),
        "final_joint_parlay_mc_still_required":True,
        "calibration_verified":False,
        "forecast_status":"HOLD",
        "wager_status":"NOT APPROVED",
    }
    receipt["scenario_receipt_sha256"]=hashlib.sha256(
        json.dumps(
            _scenario_receipt_body(receipt),
            sort_keys=True,separators=(",",":"),allow_nan=False
        ).encode()
    ).hexdigest()
    return receipt


def run_final_joint_parlay_mc(
    raw_model: Mapping[str,Any],
    raw_legs: Sequence[Mapping[str,Any]],
    scenario_receipt: Mapping[str,Any],
    *,
    trials: int,
    seed: int,
) -> Dict[str,Any]:
    """Run the separate final joint simulation required after MC-1/2/3."""
    if (
        not isinstance(scenario_receipt,Mapping)
        or scenario_receipt.get("mode")!="THREE_SCENARIO_DEPENDENCY_PRESERVING_JOINT_MC"
    ):
        raise ValueError("three-scenario joint MC receipt required")
    _sha(scenario_receipt.get("scenario_receipt_sha256"),"scenario_receipt_sha256")
    expected_receipt_sha=hashlib.sha256(
        json.dumps(
            _scenario_receipt_body(scenario_receipt),
            sort_keys=True,separators=(",",":"),allow_nan=False
        ).encode()
    ).hexdigest()
    if expected_receipt_sha!=scenario_receipt.get("scenario_receipt_sha256"):
        raise ValueError("scenario receipt hash mismatch")
    prior_seeds=scenario_receipt.get("seeds")
    if not isinstance(prior_seeds,Mapping) or seed in prior_seeds.values():
        raise ValueError("final joint MC seed must be distinct from MC-1/2/3")
    final_model=_joint_model(raw_model)
    final_legs=_legs(raw_legs,set(final_model["variable_order"]))
    if sorted(final_model["variable_order"])!=scenario_receipt.get("variable_ids"):
        raise ValueError("final variable universe differs from MC-1/2/3")
    if _leg_definition_sha(final_legs)!=scenario_receipt.get("leg_definition_sha256"):
        raise ValueError("final leg definitions differ from MC-1/2/3")
    run=simulate_joint_model(
        raw_model,raw_legs,trials=trials,seed=seed,label="FINAL_JOINT_PARLAY")
    return {
        "mode":"FINAL_DEPENDENCY_PRESERVING_JOINT_PARLAY_MC",
        "trials":trials,
        "seed":seed,
        "joint_probability":run["joint_probability"],
        "scenario_floor_joint_probability":scenario_receipt["scenario_floor_joint_probability"],
        "dominant_failure_leg":run["dominant_failure_leg"],
        "top_failure_clusters":run["top_failure_clusters"],
        "mean_absolute_latent_correlation":run["mean_absolute_latent_correlation"],
        "max_absolute_latent_correlation":run["max_absolute_latent_correlation"],
        "joint_probability_is_direct_all_hit_frequency":True,
        "individual_probabilities_multiplied":False,
        "simulation_run":run,
        "calibration_verified":False,
        "forecast_status":"HOLD",
        "wager_status":"NOT APPROVED",
    }
