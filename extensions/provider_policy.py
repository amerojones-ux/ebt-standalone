"""Fail-closed provider data-plane policy for EBT.ai research.

The provider's market quotes MUST NOT enter independent projection features.
No caller assertion can approve licensed ingestion or wagering.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping
from extensions.provider_gateway import PROVIDERS, ProviderGateError

MARKET_ONLY = frozenset({"therundown", "theoddsapi"})
STAT_CANDIDATES = frozenset({"sportsdata", "apisports", "sportradar"})
CONTEXT_ONLY = frozenset({"weather"})
ROUTER_ONLY = frozenset({"rapidapi"})
ALL = MARKET_ONLY | STAT_CANDIDATES | CONTEXT_ONLY | ROUTER_ONLY
assert ALL == frozenset(PROVIDERS)

@dataclass(frozen=True)
class DataUseDecision:
    provider: str
    purpose: str
    status: str
    reason: str
    forecast: str = "HOLD"
    wager: str = "NOT APPROVED"


def evaluate_use(provider: str, purpose: str, *,
                 upstream_provider: str | None = None,
                 documented_entitlement: bool = False) -> DataUseDecision:
    """Research routing only; never authorizes access, training or forecast activation.

    RapidAPI is a marketplace, not a single feed. Its actual upstream API must
    be identified and classified separately. Entitlement flag is diagnostic only.
    """
    if not isinstance(provider, str) or provider not in PROVIDERS:
        raise ProviderGateError("unknown provider")
    if not isinstance(purpose, str) or purpose not in {
        "independent_projection", "market_comparison", "environmental_context",
        "historical_training", "live_ingestion"
    }:
        raise ProviderGateError("unsupported data use")
    if provider == "rapidapi":
        if not isinstance(upstream_provider, str) or not upstream_provider.strip():
            return DataUseDecision(provider, purpose, "BLOCKED", "RapidAPI upstream feed unidentified")
        # A user-entered upstream label must never be treated as a certified
        # statistical provider; requires explicit separate adapter review.
        return DataUseDecision(provider, purpose, "BLOCKED", "RapidAPI upstream unverified")
    if purpose == "independent_projection" and provider in MARKET_ONLY:
        return DataUseDecision(provider, purpose, "DENIED", "market data prohibited as model feature")
    if purpose == "independent_projection" and provider in CONTEXT_ONLY:
        return DataUseDecision(provider, purpose, "BLOCKED", "environmental data requires reviewed feature mapping")
    if purpose == "market_comparison" and provider not in MARKET_ONLY:
        return DataUseDecision(provider, purpose, "BLOCKED", "market quote source not approved")
    # Even an asserted entitlement cannot establish real contractual permission.
    return DataUseDecision(provider, purpose, "BLOCKED", "independent contract and feed verification pending")
