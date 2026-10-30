"""Offline cross-provider reconciliation; no data access or forecast approval.

Upstream adapters must independently authenticate and verify licenses and IDs.
This module compares *already validated* research observations.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime, timezone
from math import isfinite
from typing import Mapping, Sequence
from extensions.provider_gateway import PROVIDERS, ProviderGateError, _utc


def reconcile_numeric(observations: Sequence[Mapping], *, as_of_utc: str,
                      max_age_seconds: int = 3600,
                      absolute_tolerance: float = 0.0,
                      min_independent_providers: int = 2) -> dict:
    """Return research consensus only for matching IDs, units and close values.

    Duplicate rows from the same provider count once, not as independent votes.
    This does not prove canonical identity, data accuracy or legal rights.
    """
    now = _utc(as_of_utc)
    if not isinstance(observations, (list, tuple)) or not observations:
        raise ProviderGateError("missing observations")
    if type(min_independent_providers) is not int or min_independent_providers < 2:
        raise ProviderGateError("at least two independent providers required")
    if type(max_age_seconds) is not int or max_age_seconds < 0:
        raise ProviderGateError("invalid freshness window")
    if type(absolute_tolerance) not in (float, int) or not isfinite(absolute_tolerance) or absolute_tolerance < 0:
        raise ProviderGateError("invalid tolerance")
    required = ("league_id", "event_id", "team_id", "player_id", "stat", "unit")
    baseline = None
    by_provider = defaultdict(list)
    for row in observations:
        if not isinstance(row, Mapping):
            raise ProviderGateError("invalid observation")
        provider = row.get("provider")
        if not isinstance(provider, str) or provider not in PROVIDERS:
            raise ProviderGateError("unknown provider")
        if row.get("status") != "FOUND":
            raise ProviderGateError("non-FOUND source")
        identity = tuple(row.get(k) for k in required)
        if any(not isinstance(v, str) or not v.strip() for v in identity):
            raise ProviderGateError("invalid observation identity or unit")
        if baseline is None:
            baseline = identity
        elif identity != baseline:
            raise ProviderGateError("cross-source identity, metric or unit conflict")
        value = row.get("value")
        if type(value) not in (int, float) or not isfinite(value):
            raise ProviderGateError("nonfinite or nonnumeric value")
        ts = _utc(row.get("source_as_of_utc"))
        age = (now - ts).total_seconds()
        if age < 0 or age > max_age_seconds:
            raise ProviderGateError("future or stale source")
        by_provider[provider].append(float(value))
    # Multiple conflicting records from one provider are not silently averaged.
    values = {}
    for provider, samples in by_provider.items():
        if max(samples) - min(samples) > absolute_tolerance:
            raise ProviderGateError("internal provider disagreement")
        values[provider] = samples[-1]
    if len(values) < min_independent_providers:
        raise ProviderGateError("insufficient independent providers")
    if max(values.values()) - min(values.values()) > absolute_tolerance:
        raise ProviderGateError("cross-provider value disagreement")
    return {"status": "RESEARCH_CONSENSUS", "forecast": "HOLD",
            "wager": "NOT APPROVED", "provider_count": len(values),
            "provider_names": sorted(values), "value": sum(values.values()) / len(values),
            "unit": baseline[-1], "stat": baseline[-2]}
