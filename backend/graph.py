from langgraph.graph import StateGraph,START,END
from langgraph.checkpoint.sqlite import SqliteSaver
import os

from state import IncidentState
from process.agents.triage import build_triage_graph
from process.agents.remediation import propose_remediation,human_approval,execute_action
from guardrails import guardrail_check
from mcp_client import call_mcp_tool


checkpointer = SqliteSaver
Store = SqliteSaver
SLACK_CHANNEL = os.environ.get("SLACK_APPROVAL_CHANNEL", "#incidents")

def route_by_severity(state: IncidentState) -> str:
    # P1: get a human's attention immediately, in parallel with starting
    # to investigate. P3: investigate fully first, only loop in a human
    # once there's an actual proposal to approve (the existing flow).
    return "notify_immediately" if state.get("severity") == "P1" else "triage"

async def notify_immediately(state: IncidentState) -> dict:
    try:
        await call_mcp_tool(
            "chat_post_message",
            {"channel": SLACK_CHANNEL,
             "text": f":red_circle: P1 alert, investigating now: {state['alert']}"},
            server="slack",
        )
    except Exception as e:
        print(f"[warn] Slack P1 notification failed, continuing without it: {e}")
    return {"timeline": state["timeline"] + ["P1: immediate notification sent"]}


def route_after_guardrail(state : IncidentState) -> str:
    return "human_approval" if state["guardrail_result"]["allowed"] else "stop_incident"

def route_after_approval(state : IncidentState)-> str:
    return "execute_action" if state["approved"] else "stop_incident"

def stop_incident(state : IncidentState) -> dict:
    reason = state.get("stop_reason","unknown")
    return {"timeline":state["timeline"]+[f"Incident stopped : {reason}"]}

def build_incident_graph(checkpointer=None):
    triage_subgraph = build_triage_graph()

    graph = StateGraph(IncidentState)

    graph.add_node("triage", triage_subgraph)
    graph.add_node("notify_immediately",notify_immediately)
    graph.add_node("propose_remediation", propose_remediation)
    graph.add_node("guardrail_check", guardrail_check)
    graph.add_node("human_approval", human_approval)
    graph.add_node("execute_action", execute_action)
    graph.add_node("stop_incident", stop_incident)

    graph.add_conditional_edges(
        START,route_by_severity,{
            "notify_immediately" : "notify_immediately" ,"triage":"triage"
        },
    )
    graph.add_edge("notify_immediately", "triage")
    graph.add_edge("triage", "propose_remediation")
    graph.add_edge("propose_remediation", "guardrail_check")

    graph.add_conditional_edges("guardrail_check",route_after_guardrail,{
        "human_approval" : "human_approval","stop_incident":"stop_incident"
    })
    graph.add_conditional_edges("human_approval", route_after_approval,
        {"execute_action": "execute_action", "stop_incident": "stop_incident"})
    graph.add_edge("execute_action", END)
    graph.add_edge("stop_incident", END)

    return graph.compile(checkpointer=checkpointer,store=Store)
