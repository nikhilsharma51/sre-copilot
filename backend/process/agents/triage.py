from typing import Annotated,TypedDict,Optional
from langchain_core.messages import AnyMessage,HumanMessage,SystemMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import START,END,StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode,tools_condition
import os

from state import IncidentState
from process.mock_ops.tools import get_logs as _get_logs ,get_metrics as _get_metrics 
from models import Hypothesis

@tool
def get_logs(service : str) -> list[str]:
    """Get recent log lines for a service."""
    return _get_logs(service)

@tool
def get_metrics(service : str) -> dict:
    """Get the current metrics snapshot for a service."""
    return _get_metrics(service)

TOOLS = [get_logs,get_metrics]

# class TriageState(TypedDict):
#     messages : Annotated[list[AnyMessage],add_messages]
#     alert : str
#     hypothesis : Optional[Hypothesis]
#     timeline : list[str]

llm = ChatGoogleGenerativeAI(model="gemini-3.6-flash",temperature=0,api_key=os.getenv("GEMINI_API_KEY"))
llm_with_tools = llm.bind_tools(TOOLS)
llm_structured = llm.with_structured_output(Hypothesis)

SYSTEM_PROMPT = (
    "You are an SRE triage agent investigating a production alert. "
    "Use get_logs and get_metrics to gather evidence before concluding "
    "anything. Only call each tool once unless you have a specific reason "
    "to call it again."
)

def triage_agent(state : IncidentState) -> dict :
    messages = state["messages"]
    if not messages :
        messages = [SystemMessage(SYSTEM_PROMPT) , HumanMessage(state["alert"])]
    response = llm_with_tools.invoke(messages)
    return {"messages" : [response]}

def summarize_hypothesis(state : IncidentState) -> dict :
    hypothesis = llm_structured.invoke(
        state["messages"]+[HumanMessage("Based on everything above, give your final hypothesis.")]
    )
    return {
        "hypothesis" : hypothesis,
        "timeline" : state["timeline"] + [f"triage hypothesis : {hypothesis.root_cause}"],
    }

def build_triage_graph():
    graph = StateGraph(IncidentState)
    graph.add_node("triage_agent", triage_agent)
    graph.add_node("tools", ToolNode(TOOLS))
    graph.add_node("summarize_hypothesis", summarize_hypothesis)

    graph.add_edge(START, "triage_agent")
    graph.add_conditional_edges(
        "triage_agent",
        tools_condition,
        {"tools": "tools", END: "summarize_hypothesis"},
    )
    graph.add_edge("tools", "triage_agent")
    graph.add_edge("summarize_hypothesis", END)

    return graph.compile()

