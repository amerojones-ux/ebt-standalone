"""Fail-closed live provider gate: only preapproved, secret-free request plans.

The caller must inject a vetted read-only endpoint and provider-specific auth
headers from a secret store. This module neither reads secrets nor makes
network calls until execute() is explicitly invoked.
"""
from dataclasses import dataclass
from provider_intake import PROVIDERS
from provider_endpoint_policy import EndpointPolicy, verify_url
from secure_provider_collector import CollectorConfig, CollectorResult, collect

@dataclass(frozen=True)
class LivePlan:
    provider: str
    policy: EndpointPolicy
    url: str
    auth_header_name: str
    contract_id: str
    approval_id: str
    max_requests: int = 1

def validate_plan(plan: LivePlan, *, approved_contracts: frozenset[str],
                  approved_approvals: frozenset[str],
                  approved_auth_bindings: frozenset[tuple[str,str,str]] = frozenset()) -> tuple[str,str]:
    if plan.provider not in PROVIDERS or plan.policy.provider != plan.provider:
        return ("FAIL","PROVIDER_MISMATCH")
    if not plan.contract_id or plan.contract_id not in approved_contracts:
        return ("HOLD","CONTRACT_NOT_APPROVED")
    if not plan.approval_id or plan.approval_id not in approved_approvals:
        return ("HOLD","LIVE_REQUEST_NOT_APPROVED")
    if plan.max_requests != 1:
        return ("FAIL","REQUEST_BUDGET_INVALID")
    if plan.auth_header_name.lower() not in ("authorization","x-api-key","x-rapidapi-key"):
        return ("FAIL","AUTH_HEADER_NOT_APPROVED")
    if (plan.provider,plan.contract_id,plan.auth_header_name.lower()) not in approved_auth_bindings:
        return ("HOLD","AUTH_BINDING_NOT_APPROVED")
    return verify_url(plan.policy,plan.url)

def execute(plan: LivePlan, *, credential: str,
            approved_contracts: frozenset[str],
            approved_approvals: frozenset[str],
            approved_auth_bindings: frozenset[tuple[str,str,str]] = frozenset(),
            config: CollectorConfig = CollectorConfig()) -> CollectorResult:
    status, reason = validate_plan(plan,approved_contracts=approved_contracts,
                                   approved_approvals=approved_approvals,
                                   approved_auth_bindings=approved_auth_bindings)
    if status != "PASS":
        return CollectorResult("HOLD",None,None,reason)
    if not isinstance(credential,str) or not credential or any(ord(c)<33 or ord(c)>126 for c in credential):
        return CollectorResult("HOLD",None,None,"CREDENTIAL_MISSING_OR_INVALID")
    # Never persist, print, or return the credential.
    return collect(plan.policy,plan.url,config=config,
                   headers={plan.auth_header_name:credential,"Accept":"application/json"})
