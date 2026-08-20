from dataclasses import dataclass, asdict

ALLOWED_SERVICES = {"checkout-service"}

DENIED_ACTIONS = {"drop_database", "delete_resource", "delete_service"}

MAX_ACTIONS_PER_INCIDENT = 3

@dataclass
class GuardrailResult:
    allowed: bool
    reason: str


def check_guardrails(action: str, target: str, actions_so_far: int) -> GuardrailResult:
    if action in DENIED_ACTIONS:
        return GuardrailResult(False, f"'{action}' is on the hard deny-list")
    if target not in ALLOWED_SERVICES:
        return GuardrailResult(False, f"'{target}' is outside the allowed blast radius")
    if actions_so_far >= MAX_ACTIONS_PER_INCIDENT:
        return GuardrailResult(
            False, f"rate limit hit: {MAX_ACTIONS_PER_INCIDENT} actions already taken this incident"
        )
    return GuardrailResult(True, "passed all checks")


def guardrail_check(state) -> dict:
    proposal = state["proposal"]
    result = check_guardrails(proposal["action"], proposal["target"], len(state["actions_taken"]))
    entry = (
        f"guardrail: allowed ({result.reason})"
        if result.allowed
        else f"guardrail: BLOCKED ({result.reason})"
    )
    update = {"guardrail_result": asdict(result), "timeline": state["timeline"] + [entry]}
    if not result.allowed:
        update["stop_reason"] = result.reason
    return update