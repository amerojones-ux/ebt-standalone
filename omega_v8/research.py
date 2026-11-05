"""OMEGA V8 offline research primitives. No live wagering authorization."""
from __future__ import annotations
from dataclasses import dataclass
from math import exp, factorial, log
from random import Random
from statistics import mean
from hashlib import sha256
import json

@dataclass(frozen=True)
class Candidate:
    player: str
    team: str
    market: str
    minutes: float
    team_opportunities: float
    opportunity_share: float
    conversion: float
    role_verified: bool
    injury_status: str = "AVAILABLE"
    minutes_restricted: bool = False
    lineup_verified: bool = True

def validate(c: Candidate):
    if not c.player or not c.team or not c.market:
        raise ValueError("missing identity")
    if not (0 <= c.minutes <= 48 and c.team_opportunities >= 0 and 0 <= c.opportunity_share <= 1 and 0 <= c.conversion <= 1):
        raise ValueError("invalid opportunity parameters")
    reasons = []
    if c.injury_status != "AVAILABLE": reasons.append("availability unresolved")
    if not c.role_verified or not c.lineup_verified: reasons.append("role/lineup unverified")
    if c.minutes_restricted: reasons.append("minutes restriction")
    return reasons

def rank_beneficiaries(candidates):
    if not candidates: raise ValueError("empty candidates")
    if len({c.team for c in candidates}) != 1: raise ValueError("different teams")
    evaluated = []
    for c in candidates:
        reasons = validate(c)
        expected = c.team_opportunities * c.opportunity_share * c.conversion
        evaluated.append({"player":c.player,"market":c.market,"expected":expected,
                          "status":"HOLD" if reasons else "RESEARCH","reasons":reasons})
    return sorted(evaluated,key=lambda x:(x["status"]!="RESEARCH",-x["expected"],x["player"]))

def hurdle_survival(threshold,zero_probability,positive_intensity):
    if not isinstance(threshold,int) or threshold < 1: raise ValueError("threshold")
    if not 0 <= zero_probability <= 1 or positive_intensity <= 0: raise ValueError("parameters")
    denom = -__import__("math").expm1(-positive_intensity)
    below = sum(exp(-positive_intensity)*positive_intensity**k/factorial(k) for k in range(1,threshold))
    return max(0.,min(1.,(1-zero_probability)*(1-below/denom)))

def bayesian_zero_posterior(zero_games,total_games,alpha=2.,beta=8.):
    if not (0 <= zero_games <= total_games and total_games >= 0 and alpha > 0 and beta > 0):
        raise ValueError("posterior inputs")
    return (zero_games+alpha)/(total_games+alpha+beta)

def correlated_combo_sim(rebounds,assists,threshold,draws=100000,seed=1):
    """Paired historical component bootstrap preserves observed dependence."""
    if len(rebounds)!=len(assists) or not rebounds or draws<1: raise ValueError("paired observations")
    if any(x<0 for x in rebounds) or any(x<0 for x in assists): raise ValueError("negative components")
    rng=Random(seed)
    return sum(rebounds[i]+assists[i]>=threshold for i in (rng.randrange(len(rebounds)) for _ in range(draws)))/draws

def scenario_mc(candidates,threshold,draws=100000,seed=1,adverse_minutes_factor=.8):
    """Joint multinomial team-opportunity allocation; independent conversion conditional on share.
    Shared team opportunity count means player opportunities compete rather than duplicate.
    """
    if draws<1 or not 0<adverse_minutes_factor<=1: raise ValueError("simulation parameters")
    if not candidates: raise ValueError("empty")
    if len({c.team for c in candidates})!=1: raise ValueError("team mismatch")
    for c in candidates: validate(c)
    shares=[c.opportunity_share for c in candidates]
    if sum(shares)>1+1e-9: raise ValueError("shares exceed team opportunities")
    if len({c.team_opportunities for c in candidates})!=1: raise ValueError("inconsistent team opportunity pool")
    rng=Random(seed)
    results={}
    for scenario,factor in (("baseline",1.),("adverse",adverse_minutes_factor)):
        hits=[0]*len(candidates)
        for _ in range(draws):
            counts=[0]*len(candidates)
            opportunities=int(candidates[0].team_opportunities*factor)
            for _ in range(opportunities):
                u=rng.random(); cumulative=0.
                for i,c in enumerate(candidates):
                    cumulative+=c.opportunity_share
                    if u<cumulative:
                        if rng.random()<c.conversion: counts[i]+=1
                        break
            for i,count in enumerate(counts):
                hits[i]+=count>=threshold
        results[scenario]={c.player:h/draws for c,h in zip(candidates,hits)}
    results["status"]="HOLD" if any(validate(c) for c in candidates) else "RESEARCH_ONLY"
    return results

def backtest(rows):
    """Pre-locked historical forecasts: records must have chronological issue/settlement times."""
    if not rows: raise ValueError("no history")
    ordered=sorted(rows,key=lambda x:x["issued_at"])
    for r in ordered:
        if not (0<=r["probability"]<=1) or r["issued_at"]>=r["event_at"] or r["event_at"]>r["settled_at"]:
            raise ValueError("temporal leakage or probability")
        if r["outcome"] not in (0,1): raise ValueError("unsettled outcome")
    return {"n":len(ordered),
            "brier":mean((r["probability"]-r["outcome"])**2 for r in ordered),
            "log_loss":mean(-(r["outcome"]*log(max(1e-12,r["probability"]))+(1-r["outcome"])*log(max(1e-12,1-r["probability"]))) for r in ordered),
            "observed_hit_rate":mean(r["outcome"] for r in ordered)}

def immutable_audit_record(previous_hash,forecast,settlement):
    """Hash-chain payload for append-only storage; caller must persist and authenticate externally."""
    payload={"previous_hash":previous_hash,"forecast":forecast,"settlement":settlement}
    canonical=json.dumps(payload,sort_keys=True,separators=(",",":"),allow_nan=False)
    return {"payload":payload,"sha256":sha256(canonical.encode()).hexdigest()}
