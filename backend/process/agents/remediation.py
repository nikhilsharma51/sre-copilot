from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq
from langgraph.types import interrupt
import os
MODEL_NAME = os.getenv("MODEL")

from process.mock_ops.tools import restart_service as _restart_service
from process.mock_ops.data import RECENT_DEPLOY
from models import RemediationProposal
from state import IncidentState
from mcp_client import call_mcp_tool
from dotenv import load_dotenv
load_dotenv()

ALLOWED_ACTIONS = {"restart_service" ,"open_revert_pr", "clear_old_logs"}

SLACK_CHANNEL = os.environ.get("SLACK_APPROVAL_CHANNEL", "#incidents")

remediation_llm = ChatGroq(model=MODEL_NAME,temperature=0)
remediation_structured = remediation_llm.with_structured_output(RemediationProposal,
                                                                method="json_schema")

PROPOSAL_PROMPT = (
    "You are the remediation half of an SRE copilot. Given the triage "
    "hypothesis below, propose exactly one action from this allowed list: "
    f"{sorted(ALLOWED_ACTIONS)}. restart_service is a quick mitigation for "
    "connection pool issues. open_revert_pr addresses the root cause if a "
    "recent deploy is implicated. clear_old_logs fixes disk-space "
    "exhaustion. If nothing in the allowed list actually addresses the "
    "hypothesis, still propose the closest one but say so honestly in "
    "your reasoning."
)


def propose_remediation(state:IncidentState) -> dict:
    hyp = state["hypothesis"]
    prompt = (
        f"{PROPOSAL_PROMPT}\n\n"
        f"Hypothesis: {hyp.root_cause}\n"
        f"Evidence: {hyp.evidence}\n"
        f"Confidence: {hyp.confidence}"
    )

    proposal = remediation_structured.invoke([HumanMessage(prompt)]).model_dump()
    return {
        "proposal" : proposal,
        "timeline" : state["timeline"]
        +[f"proposed: {proposal['action']}({proposal['target']}), because {proposal['reasoning']}"],
    }

async def human_approval(state: IncidentState) -> dict:
    proposal = state["proposal"]

    try :
        await call_mcp_tool(
            "chat_post_message",{
                "channel": SLACK_CHANNEL,
                "text": (
                    f":rotating_light: Approval needed: *{proposal['action']}*"
                    f"({proposal['target']})\nReasoning: {proposal['reasoning']}\n"
                    f"Reply here with `approve` or `deny` in the thread."
                ),
            },
            server="slack"
        )

    except Exception as e:
        print(f"[warn] Slack notification failed, continuing without it: {e}")

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

async def _open_revert_pr(target: str) -> dict:
    deploy = RECENT_DEPLOY.get(target)
    if not deploy:
        return {"status": "error", "detail": f"no deploy record for '{target}'"}

    owner, repo, commit = deploy["owner"], deploy["repo"], deploy["bad_commit"]
    branch = f"revert-{commit}"

    await call_mcp_tool("create_branch", {"owner": owner, "repo": repo, "branch": branch}, server="github")
    await call_mcp_tool(
        "create_or_update_file",
        {
            "owner": owner, "repo": repo, "branch": branch,
            "path": "INCIDENT_NOTES.md",
            "message": f"Flag suspected bad deploy {commit} for revert",
            "content": (
                f"# Incident-flagged revert\n\nDeploy `{commit}` is suspected of causing a "
                f"connection pool exhaustion incident. Opened automatically by SRE Copilot "
                f"after human approval. Please complete the actual revert and request review "
                f"before merging."
            ),
        },
        server="github",
    )
    pr = await call_mcp_tool(
        "create_pull_request",
        {
            "owner": owner, "repo": repo, "base": "main", "head": branch,
            "title": f"Revert suspected bad deploy {commit}",
            "body": "Opened automatically following an approved SRE Copilot incident. "
                    "This PR flags the change for a human to complete the revert.",
        },
        server="github",
    )
    return {"status": "ok", "detail": f"PR opened: {pr.get('html_url', pr)}"}



async def execute_action(state: IncidentState) -> dict:
    proposal = state["proposal"]
    action, target = proposal["action"], proposal["target"]

    if action == "restart_service":
        result = await call_mcp_tool("restart_service", {"service": target})
    elif action == "open_revert_pr":
        result = await _open_revert_pr(target)
    elif action == "clear_old_logs":
        result = await call_mcp_tool("clear_old_logs", {"service": target})
    else:
        result = {"status": "error", "detail": f"no executor wired for action '{action}'"}

    return {
        "result": result,
        "actions_taken": state["actions_taken"] + [{"action": action, "target": target, "result": result}],
        "timeline": state["timeline"] + [f"executed {action}({target}) -> {result['status']}"],
    }