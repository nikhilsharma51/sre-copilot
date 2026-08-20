from langgraph.graph import StateGraph,START,END
from langgraph.store.memory import InMemoryStore

from state import IncidentState
from process.agents.triage import build_triage_graph
from process.agents.remediation import propose_remediation,human_approval,execute_action
from guardrails import guardrail_check


checkpointer = InMemoryStore()
store = InMemoryStore()

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
    graph.add_node("propose_remediation", propose_remediation)
    graph.add_node("guardrail_check", guardrail_check)
    graph.add_node("human_approval", human_approval)
    graph.add_node("execute_action", execute_action)
    graph.add_node("stop_incident", stop_incident)
    graph.add_edge(START, "triage")
    graph.add_edge("triage", "propose_remediation")
    graph.add_edge("propose_remediation", "guardrail_check")

    graph.add_conditional_edges("guardrail_check",route_after_guardrail,{
        "human_approval" : "human_approval","stop_incident":"stop_incident"
    })
    graph.add_conditional_edges("human_approval", route_after_approval,
        {"execute_action": "execute_action", "stop_incident": "stop_incident"})
    graph.add_edge("execute_action", END)
    graph.add_edge("stop_incident", END)

    return graph.compile(checkpointer=checkpointer,store=store)
