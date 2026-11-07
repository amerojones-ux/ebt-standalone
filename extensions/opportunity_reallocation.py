"""Bayesian beneficiary competition and opportunity-share redistribution.

Research-only. Reallocates a finite displaced opportunity pool across active
players using pre-event Dirichlet-style concentration evidence plus hard
capacity caps. Sportsbook prices/lines are not inputs. Unallocated opportunity
is preserved explicitly rather than forced onto a beneficiary.
"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Iterable, Mapping, Sequence

from .underperformance import num

AVAILABILITY={"ACTIVE","OUT"}


def _clock(value: Any, field: str) -> datetime:
    if not isinstance(value,str) or not value.strip():
        raise ValueError(f"{field} timezone-aware ISO time required")
    try:
        dt=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} invalid ISO time") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError(f"{field} timezone-aware ISO time required")
    return dt.astimezone(timezone.utc)


def _roster(rows: Sequence[Mapping[str,Any]], cutoff: str):
    if not isinstance(rows,(list,tuple)) or not rows:
        raise ValueError("nonempty roster required")
    at=_clock(cutoff,"cutoff")
    required={
        "player_id","availability","baseline_units","max_units",
        "prior_alpha","context_units","evidence_available_at",
    }
    out=[]
    seen=set()
    for row in rows:
        if not isinstance(row,Mapping) or set(row)!=required:
            raise ValueError("exact beneficiary roster schema required")
        pid=row["player_id"]
        if not isinstance(pid,str) or not pid.strip() or pid in seen:
            raise ValueError("unique nonblank player_id required")
        seen.add(pid)
        availability=row["availability"]
        if availability not in AVAILABILITY:
            raise ValueError("availability must be ACTIVE or OUT for this scenario")
        baseline=num(row["baseline_units"])
        maximum=num(row["max_units"])
        prior=num(row["prior_alpha"])
        context=num(row["context_units"])
        available=_clock(row["evidence_available_at"],f"{pid}.evidence_available_at")
        if available>at:
            raise ValueError("post-cutoff beneficiary evidence rejected")
        if baseline<0 or maximum<0 or prior<0 or context<0:
            raise ValueError("nonnegative opportunity/concentration values required")
        if availability=="ACTIVE" and maximum<baseline:
            raise ValueError("active max_units cannot be below baseline_units")
        if availability=="ACTIVE" and prior+context<=0:
            raise ValueError("active beneficiary requires positive posterior concentration")
        out.append({
            "player_id":pid,
            "availability":availability,
            "baseline_units":baseline,
            "max_units":maximum,
            "prior_alpha":prior,
            "context_units":context,
            "posterior_alpha":prior+context,
            "evidence_available_at":available.isoformat(),
        })
    return out


def _allocate_capped(target: Decimal, active):
    increments={row["player_id"]:Decimal(0) for row in active}
    capacity={
        row["player_id"]:max(Decimal(0),row["max_units"]-row["baseline_units"])
        for row in active
    }
    alpha={row["player_id"]:row["posterior_alpha"] for row in active}
    remaining=target
    eligible={pid for pid in increments if capacity[pid]>0 and alpha[pid]>0}
    while remaining>Decimal("1e-18") and eligible:
        weight=sum((alpha[pid] for pid in eligible),Decimal(0))
        if weight<=0:
            break
        proposed={pid:remaining*alpha[pid]/weight for pid in eligible}
        capped=[
            pid for pid in eligible
            if proposed[pid]>=capacity[pid]-increments[pid]-Decimal("1e-18")
        ]
        if not capped:
            for pid in eligible:
                increments[pid]+=proposed[pid]
            remaining=Decimal(0)
            break
        consumed=Decimal(0)
        for pid in capped:
            room=max(Decimal(0),capacity[pid]-increments[pid])
            increments[pid]+=room
            consumed+=room
        remaining=max(Decimal(0),remaining-consumed)
        eligible-=set(capped)
    return increments, remaining


def allocate_displaced_opportunity(
    roster: Sequence[Mapping[str,Any]],
    *,
    metric: str,
    team_budget: Any,
    cutoff: str,
    redistribution_fraction: Any,
    scenario_name: str,
) -> Dict[str,Any]:
    """Allocate displaced baseline units among active beneficiaries with caps."""
    if not isinstance(metric,str) or not metric.strip():
        raise ValueError("metric required")
    if not isinstance(scenario_name,str) or not scenario_name.strip():
        raise ValueError("scenario_name required")
    rows=_roster(roster,cutoff)
    budget=num(team_budget)
    fraction=num(redistribution_fraction)
    if budget<0:
        raise ValueError("nonnegative team_budget required")
    if not Decimal(0)<=fraction<=Decimal(1):
        raise ValueError("redistribution_fraction must be in [0,1]")
    baseline_total=sum((row["baseline_units"] for row in rows),Decimal(0))
    if abs(baseline_total-budget)>Decimal("1e-10"):
        raise ValueError("baseline roster units must exactly reconcile to team_budget")

    out_rows=[row for row in rows if row["availability"]=="OUT"]
    active=[row for row in rows if row["availability"]=="ACTIVE"]
    displaced=sum((row["baseline_units"] for row in out_rows),Decimal(0))
    target=displaced*fraction
    increments,residual_target=_allocate_capped(target,active)
    allocated=sum(increments.values(),Decimal(0))
    contraction=displaced-allocated
    if contraction<Decimal("-1e-10"):
        raise ValueError("allocation exceeds displaced opportunity")

    posterior_total=sum((row["posterior_alpha"] for row in active),Decimal(0))
    result=[]
    for row in rows:
        inc=increments.get(row["player_id"],Decimal(0))
        final=(row["baseline_units"]+inc) if row["availability"]=="ACTIVE" else Decimal(0)
        posterior_share=(
            row["posterior_alpha"]/posterior_total
            if row["availability"]=="ACTIVE" and posterior_total>0 else Decimal(0)
        )
        increment_share=inc/allocated if allocated>0 else Decimal(0)
        multiplier=(
            final/row["baseline_units"]
            if row["baseline_units"]>0 and row["availability"]=="ACTIVE" else None
        )
        result.append({
            "player_id":row["player_id"],
            "availability":row["availability"],
            "baseline_units":str(row["baseline_units"]),
            "max_units":str(row["max_units"]),
            "prior_alpha":str(row["prior_alpha"]),
            "context_units":str(row["context_units"]),
            "posterior_alpha":str(row["posterior_alpha"]),
            "posterior_competition_share":float(posterior_share),
            "allocated_increment":str(inc),
            "increment_share":float(increment_share),
            "final_expected_units":str(final),
            "opportunity_multiplier":None if multiplier is None else float(multiplier),
        })

    hhi=sum(
        (Decimal(str(row["increment_share"]))**2 for row in result),
        Decimal(0),
    ) if allocated>0 else Decimal(0)
    max_share=max((Decimal(str(row["increment_share"])) for row in result),default=Decimal(0))
    ranked=sorted(
        [row for row in result if row["availability"]=="ACTIVE"],
        key=lambda row:(
            Decimal(row["allocated_increment"]),
            Decimal(row["posterior_alpha"]),
        ),
        reverse=True,
    )

    active_final=sum(
        (Decimal(row["final_expected_units"]) for row in result if row["availability"]=="ACTIVE"),
        Decimal(0),
    )
    accounted=active_final+contraction
    if abs(accounted-budget)>Decimal("1e-8"):
        raise ValueError("post-allocation accounting does not reconcile to team budget")

    return {
        "mode":"OFFLINE_BENEFICIARY_OPPORTUNITY_REALLOCATION",
        "scenario_name":scenario_name,
        "metric":metric,
        "cutoff":_clock(cutoff,"cutoff").isoformat(),
        "team_budget":str(budget),
        "baseline_total":str(baseline_total),
        "displaced_units":str(displaced),
        "redistribution_fraction":str(fraction),
        "target_redistributed_units":str(target),
        "allocated_units":str(allocated),
        "capacity_residual_from_target":str(residual_target),
        "team_contraction_or_unassigned_units":str(contraction),
        "allocation_hhi":float(hhi),
        "largest_increment_share":float(max_share),
        "beneficiary_ranking":[row["player_id"] for row in ranked],
        "players":result,
        "price_inputs_used":False,
        "calibration_verified":False,
        "forecast_status":"HOLD",
        "wager_status":"NOT APPROVED",
    }


def run_reallocation_scenarios(
    base_roster: Sequence[Mapping[str,Any]],
    scenario_specs: Mapping[str,Mapping[str,Any]],
    *,
    metric: str,
    team_budget: Any,
    cutoff: str,
) -> Dict[str,Any]:
    """Run explicit availability/redistribution scenarios and expose player floors."""
    if not isinstance(scenario_specs,Mapping) or not scenario_specs:
        raise ValueError("scenario_specs required")
    base=_roster(base_roster,cutoff)
    by_id={row["player_id"]:row for row in base}
    results={}
    for name,spec in scenario_specs.items():
        if not isinstance(name,str) or not name.strip() or not isinstance(spec,Mapping):
            raise ValueError("valid scenario name/spec required")
        if set(spec)!={"redistribution_fraction","availability_overrides"}:
            raise ValueError("exact scenario spec schema required")
        overrides=spec["availability_overrides"]
        if not isinstance(overrides,Mapping):
            raise ValueError("availability_overrides object required")
        scenario=[]
        for row in base:
            availability=overrides.get(row["player_id"],row["availability"])
            if availability not in AVAILABILITY:
                raise ValueError("scenario availability override must be ACTIVE or OUT")
            scenario.append({
                "player_id":row["player_id"],
                "availability":availability,
                "baseline_units":str(row["baseline_units"]),
                "max_units":str(row["max_units"]),
                "prior_alpha":str(row["prior_alpha"]),
                "context_units":str(row["context_units"]),
                "evidence_available_at":row["evidence_available_at"],
            })
        unknown=set(overrides)-set(by_id)
        if unknown:
            raise ValueError("availability override references unknown player")
        results[name]=allocate_displaced_opportunity(
            scenario,metric=metric,team_budget=team_budget,cutoff=cutoff,
            redistribution_fraction=spec["redistribution_fraction"],
            scenario_name=name)

    player_ids=sorted(by_id)
    stability=[]
    for pid in player_ids:
        increments=[]
        finals=[]
        for result in results.values():
            row=next(x for x in result["players"] if x["player_id"]==pid)
            increments.append(num(row["allocated_increment"]))
            finals.append(num(row["final_expected_units"]))
        stability.append({
            "player_id":pid,
            "increment_floor":str(min(increments)),
            "increment_ceiling":str(max(increments)),
            "final_units_floor":str(min(finals)),
            "final_units_ceiling":str(max(finals)),
            "positive_increment_all_scenarios":all(x>0 for x in increments),
        })
    return {
        "mode":"OFFLINE_BENEFICIARY_SCENARIO_COMPARISON",
        "metric":metric,
        "scenario_count":len(results),
        "scenarios":results,
        "player_stability":stability,
        "price_inputs_used":False,
        "calibration_verified":False,
        "forecast_status":"HOLD",
        "wager_status":"NOT APPROVED",
    }
