"""Bayesian rare-event research distributions for Black Diamond.

Two distinct families are implemented:
1) Dirichlet competing-event posteriors for first basket/TD/goal markets.
2) Beta-Bernoulli binary posteriors for exact early-window/rare binary events.

All inputs must be pre-event evidence. Sportsbook odds/prices are forbidden.
Posterior uncertainty is research-only and is not calibrated hit probability.
"""
from array import array
from datetime import datetime, timezone
from decimal import Decimal
import random
from typing import Any, Dict, Mapping, Sequence

from .underperformance import num

SCENARIOS=("baseline","adversarial","scenario")


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


def _fair_decimal(probability: Decimal):
    if probability<=0:
        return None
    return str(Decimal(1)/probability)


def fit_competing_event_posterior(
    rows: Sequence[Mapping[str,Any]],
    *,
    cutoff: str,
    residual_category_id: str,
    candidate_universe_complete: bool,
) -> Dict[str,Any]:
    """Fit a categorical Dirichlet posterior from mutually exclusive event counts."""
    if candidate_universe_complete is not True:
        raise ValueError("complete candidate universe with residual category required")
    if not isinstance(residual_category_id,str) or not residual_category_id.strip():
        raise ValueError("residual_category_id required")
    if not isinstance(rows,(list,tuple)) or len(rows)<2:
        raise ValueError("at least two competing categories required")
    at=_clock(cutoff,"cutoff")
    required={
        "candidate_id","prior_alpha","historical_first_events","evidence_available_at",
    }
    posterior={}
    historical={}
    priors={}
    seen=set()
    for row in rows:
        if not isinstance(row,Mapping) or set(row)!=required:
            raise ValueError("exact competing-event row schema required")
        cid=row["candidate_id"]
        if not isinstance(cid,str) or not cid.strip() or cid in seen:
            raise ValueError("unique candidate_id required")
        seen.add(cid)
        prior=num(row["prior_alpha"])
        count=row["historical_first_events"]
        if prior<=0:
            raise ValueError("positive prior_alpha required")
        if type(count) is not int or count<0:
            raise ValueError("historical_first_events must be nonnegative integer")
        if _clock(row["evidence_available_at"],f"{cid}.evidence_available_at")>at:
            raise ValueError("post-cutoff rare-event evidence rejected")
        priors[cid]=prior
        historical[cid]=count
        posterior[cid]=prior+Decimal(count)
    if residual_category_id not in posterior:
        raise ValueError("residual category must be included in competing universe")
    sample_total=sum(historical.values())
    if sample_total<=0:
        raise ValueError("settled historical first-event sample required")
    alpha_total=sum(posterior.values(),Decimal(0))
    mean={cid:posterior[cid]/alpha_total for cid in posterior}
    return {
        "mode":"BAYESIAN_COMPETING_RARE_EVENT_POSTERIOR",
        "cutoff":at.isoformat(),
        "residual_category_id":residual_category_id,
        "candidate_universe_complete":True,
        "historical_event_count":sample_total,
        "prior_alpha":{cid:str(v) for cid,v in priors.items()},
        "historical_first_events":historical,
        "posterior_alpha":{cid:str(v) for cid,v in posterior.items()},
        "posterior_mean_probability":{cid:float(v) for cid,v in mean.items()},
        "fair_decimal_odds_from_posterior_mean":{
            cid:_fair_decimal(mean[cid]) for cid in mean
        },
        "price_inputs_used":False,
        "calibration_verified":False,
        "forecast_status":"HOLD",
        "wager_status":"NOT APPROVED",
    }


def _quantile(sorted_values, fraction: float):
    if not sorted_values:
        raise ValueError("empty posterior samples")
    if not 0<=fraction<=1:
        raise ValueError("quantile fraction outside [0,1]")
    index=int(round((len(sorted_values)-1)*fraction))
    return float(sorted_values[index])


def simulate_competing_posterior_uncertainty(
    posterior: Mapping[str,Any],
    *,
    trials: int,
    seed: int,
) -> Dict[str,Any]:
    """Sample uncertainty in latent competing-event probabilities, not game outcomes."""
    if not isinstance(posterior,Mapping) or posterior.get("mode")!="BAYESIAN_COMPETING_RARE_EVENT_POSTERIOR":
        raise ValueError("competing posterior required")
    if type(trials) is not int or trials<100000:
        raise ValueError("at least 100000 posterior trials required")
    if type(seed) is not int:
        raise ValueError("integer deterministic seed required")
    raw=posterior.get("posterior_alpha")
    if not isinstance(raw,Mapping) or len(raw)<2:
        raise ValueError("posterior alpha mapping required")
    alpha={cid:num(value) for cid,value in raw.items()}
    if any(v<=0 for v in alpha.values()):
        raise ValueError("positive posterior alpha required")
    ids=sorted(alpha)
    rng=random.Random(seed)
    samples={cid:array("d") for cid in ids}
    rank1={cid:0 for cid in ids}
    for _ in range(trials):
        draws={cid:rng.gammavariate(float(alpha[cid]),1.0) for cid in ids}
        total=sum(draws.values())
        if total<=0:
            raise ValueError("invalid gamma draw total")
        best=max(ids,key=lambda cid:draws[cid])
        rank1[best]+=1
        for cid in ids:
            samples[cid].append(draws[cid]/total)
    summaries={}
    for cid in ids:
        ordered=sorted(samples[cid])
        summaries[cid]={
            "posterior_mean_analytic":posterior["posterior_mean_probability"][cid],
            "probability_p05":_quantile(ordered,.05),
            "probability_p50":_quantile(ordered,.50),
            "probability_p95":_quantile(ordered,.95),
            "posterior_rank1_probability":rank1[cid]/trials,
        }
    return {
        "mode":"BAYESIAN_COMPETING_RARE_EVENT_UNCERTAINTY",
        "trials":trials,
        "seed":seed,
        "candidates":summaries,
        "uncertainty_semantics":"posterior uncertainty in latent event probabilities",
        "game_outcome_monte_carlo":False,
        "calibration_verified":False,
        "forecast_status":"HOLD",
        "wager_status":"NOT APPROVED",
    }


def run_three_competing_event_scenarios(
    posteriors: Mapping[str,Mapping[str,Any]],
    *,
    trials: int,
    seeds: Mapping[str,int],
) -> Dict[str,Any]:
    """Run baseline/adversarial/scenario posterior uncertainty and expose floors."""
    if not isinstance(posteriors,Mapping) or set(posteriors)!=set(SCENARIOS):
        raise ValueError("baseline/adversarial/scenario posteriors required")
    if not isinstance(seeds,Mapping) or set(seeds)!=set(SCENARIOS):
        raise ValueError("distinct baseline/adversarial/scenario seeds required")
    if len(set(seeds.values()))!=3 or any(type(x) is not int for x in seeds.values()):
        raise ValueError("three distinct integer seeds required")
    candidate_sets=[]
    residuals=[]
    runs={}
    for name in SCENARIOS:
        p=posteriors[name]
        candidate_sets.append(set(p.get("posterior_alpha",{})))
        residuals.append(p.get("residual_category_id"))
        runs[name]=simulate_competing_posterior_uncertainty(
            p,trials=trials,seed=seeds[name])
    if any(s!=candidate_sets[0] for s in candidate_sets[1:]):
        raise ValueError("scenario candidate universes must match exactly")
    if len(set(residuals))!=1:
        raise ValueError("scenario residual category must match")
    candidates={}
    for cid in sorted(candidate_sets[0]):
        means=[posteriors[name]["posterior_mean_probability"][cid] for name in SCENARIOS]
        p05=[runs[name]["candidates"][cid]["probability_p05"] for name in SCENARIOS]
        p95=[runs[name]["candidates"][cid]["probability_p95"] for name in SCENARIOS]
        rank1=[runs[name]["candidates"][cid]["posterior_rank1_probability"] for name in SCENARIOS]
        candidates[cid]={
            "scenario_mean_probabilities":dict(zip(SCENARIOS,means)),
            "scenario_p05":dict(zip(SCENARIOS,p05)),
            "scenario_p95":dict(zip(SCENARIOS,p95)),
            "mean_probability_floor":min(means),
            "posterior_p05_floor":min(p05),
            "posterior_p95_ceiling":max(p95),
            "rank1_probability_floor":min(rank1),
        }
    return {
        "mode":"THREE_SCENARIO_BAYESIAN_COMPETING_RARE_EVENT",
        "trials_each":trials,
        "seeds":dict(seeds),
        "runs":runs,
        "candidates":candidates,
        "calibration_verified":False,
        "forecast_status":"HOLD",
        "wager_status":"NOT APPROVED",
    }


def fit_binary_rare_event_posterior(
    *,
    event_definition: str,
    prior_alpha: Any,
    prior_beta: Any,
    successes: int,
    failures: int,
    evidence_available_at: str,
    cutoff: str,
) -> Dict[str,Any]:
    """Fit a Beta posterior for one exact predeclared binary rare-event definition."""
    if not isinstance(event_definition,str) or not event_definition.strip():
        raise ValueError("event_definition required")
    a=num(prior_alpha)
    b=num(prior_beta)
    if a<=0 or b<=0:
        raise ValueError("positive Beta priors required")
    if type(successes) is not int or successes<0 or type(failures) is not int or failures<0:
        raise ValueError("successes/failures must be nonnegative integers")
    if successes+failures<=0:
        raise ValueError("settled binary history required")
    available=_clock(evidence_available_at,"evidence_available_at")
    at=_clock(cutoff,"cutoff")
    if available>at:
        raise ValueError("post-cutoff binary rare-event evidence rejected")
    pa=a+Decimal(successes)
    pb=b+Decimal(failures)
    mean=pa/(pa+pb)
    return {
        "mode":"BAYESIAN_BINARY_RARE_EVENT_POSTERIOR",
        "event_definition":event_definition.strip(),
        "cutoff":at.isoformat(),
        "successes":successes,
        "failures":failures,
        "prior_alpha":str(a),
        "prior_beta":str(b),
        "posterior_alpha":str(pa),
        "posterior_beta":str(pb),
        "posterior_mean_probability":float(mean),
        "fair_decimal_odds_from_posterior_mean":_fair_decimal(mean),
        "price_inputs_used":False,
        "calibration_verified":False,
        "forecast_status":"HOLD",
        "wager_status":"NOT APPROVED",
    }


def simulate_binary_posterior_uncertainty(
    posterior: Mapping[str,Any],
    *,
    trials: int,
    seed: int,
) -> Dict[str,Any]:
    if not isinstance(posterior,Mapping) or posterior.get("mode")!="BAYESIAN_BINARY_RARE_EVENT_POSTERIOR":
        raise ValueError("binary rare-event posterior required")
    if type(trials) is not int or trials<100000:
        raise ValueError("at least 100000 posterior trials required")
    if type(seed) is not int:
        raise ValueError("integer deterministic seed required")
    a=num(posterior.get("posterior_alpha"))
    b=num(posterior.get("posterior_beta"))
    if a<=0 or b<=0:
        raise ValueError("positive posterior parameters required")
    rng=random.Random(seed)
    values=array("d")
    for _ in range(trials):
        ga=rng.gammavariate(float(a),1.0)
        gb=rng.gammavariate(float(b),1.0)
        total=ga+gb
        if total<=0:
            raise ValueError("invalid beta gamma draw")
        values.append(ga/total)
    ordered=sorted(values)
    return {
        "mode":"BAYESIAN_BINARY_RARE_EVENT_UNCERTAINTY",
        "event_definition":posterior["event_definition"],
        "trials":trials,
        "seed":seed,
        "posterior_mean_analytic":posterior["posterior_mean_probability"],
        "probability_p05":_quantile(ordered,.05),
        "probability_p50":_quantile(ordered,.50),
        "probability_p95":_quantile(ordered,.95),
        "uncertainty_semantics":"posterior uncertainty in latent binary event probability",
        "game_outcome_monte_carlo":False,
        "calibration_verified":False,
        "forecast_status":"HOLD",
        "wager_status":"NOT APPROVED",
    }
