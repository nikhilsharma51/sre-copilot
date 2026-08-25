from state import IncidentState

def _status(state: IncidentState, interrupted: bool) -> str:
    if interrupted:
        return "PENDING APPROVAL"
    if state.get("stop_reason"):
        if state.get("approved") is False:
            return f"DENIED ({state['stop_reason']})"
        return f"BLOCKED ({state['stop_reason']})"
    result = state.get("result")
    if result and result.get("status") == "ok":
        return "RESOLVED"
    return "UNKNOWN"


def render_report(state: IncidentState, interrupted: bool = False) -> str:
    lines = ["=" * 64, "INCIDENT REPORT", "=" * 64]
    lines.append(f"Alert:   {state['alert']}")
    lines.append(f"Status:  {_status(state, interrupted)}")
    lines.append("")

    hyp = state.get("hypothesis")
    if hyp:
        lines.append("--- Triage ---")
        lines.append(f"Hypothesis:  {hyp.root_cause}")
        lines.append(f"Confidence:  {hyp.confidence}")
        lines.append("Evidence:")
        for e in hyp.evidence:
            lines.append(f"  - {e}")
        lines.append("")

    proposal = state.get("proposal")
    if proposal:
        lines.append("--- Remediation ---")
        lines.append(f"Proposed:   {proposal['action']}({proposal['target']})")
        lines.append(f"Reasoning:  {proposal['reasoning']}")

        gr = state.get("guardrail_result")
        if gr:
            verdict = "ALLOWED" if gr["allowed"] else "BLOCKED"
            lines.append(f"Guardrail:  {verdict} ({gr['reason']})")

        if state.get("approved") is not None:
            lines.append(f"Approval:   {'APPROVED' if state['approved'] else 'DENIED'}")

        result = state.get("result")
        if result:
            lines.append(f"Executed:   {proposal['action']}({proposal['target']}) -> {result['status']}")
        lines.append("")

    lines.append("--- Timeline ---")
    for i, entry in enumerate(state["timeline"], start=1):
        lines.append(f"{i}. {entry}")
    lines.append("=" * 64)

    return "\n".join(lines)