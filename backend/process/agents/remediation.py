from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq
from langgraph.types import interrupt

from mock_ops.tools import restart_service as _restart_service
from models import RemediationProposal
from state import IncidentState

ALLOWED_ACTIONS = {"restart_service"}

remediation_llm = ChatGroq(model="",temperature=0)
remediation_structured = remediation_llm.with_structured_output(RemediationProposal)

PROPOSAL_PROMPT = (
     "You are the remediation half of an SRE copilot. Given the triage "
    "hypothesis below, propose exactly one action from this allowed list: "
    f"{sorted(ALLOWED_ACTIONS)}. If nothing in the allowed list actually "
    "addresses the hypothesis, still propose the closest one but say so "
    "honestly in your reasoning."
)

def propose_remediation(state:IncidentState) -> dict:
    hyp = state["hypothesis"]
    prompt = (
        f"{PROPOSAL_PROMPT}\n\n"
        f"Hypothesis: {hyp['root_cause']}\n"
        f"Evidence: {hyp['evidence']}\n"
        f"Confidence: {hyp['confidence']}"
    )

    proposal = remediation_structured.invoke([HumanMessage(prompt)]).model_dump()
    return {
        "proposal" : proposal,
        "timeline" : state["timeline"]
        +[f"proposed: {proposal['action']}({proposal['target']}), because {proposal['reasoning']}"],
    }

def human_approval(state: IncidentState) -> dict:
    proposal = state["proposal"]
    decision = interrupt({
        "question": "Approve this remediation action?",
        "action": proposal["action"],
        "target": proposal["target"],
        "reasoning": proposal["reasoning"]
    })

    approved = bool(decision.get("approved",False))
    note = decision.get("reason")
    entry = f"human approval : {'approved' if approved else 'denied'}"
    if note :
        entry += f"({note})"
    update = {"approved": approved, "timeline":state["timeline"]+[entry]}
    if not approved :
        update["stop_reason"] = note or "human denied th proposed action"
    return update         

def execute_action(state: IncidentState) -> dict:
    proposal = state["proposal"]
    if proposal["action"] == "restart_service":
        result = _restart_service(proposal["target"])
    else:
        result = {"status": "error", "detail": f"no executor wired for action '{proposal['action']}'"}
    return {
        "result": result,
        "actions_taken": state["actions_taken"]
        + [{"action": proposal["action"], "target": proposal["target"], "result": result}],
        "timeline": state["timeline"]
        + [f"executed {proposal['action']}({proposal['target']}) -> {result['status']}"],
    }