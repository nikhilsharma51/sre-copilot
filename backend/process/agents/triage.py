import os
from typing import Annotated,TypedDict,Optional,cast
from langchain_core.messages import AnyMessage,HumanMessage,SystemMessage
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langgraph.graph import START,END,StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode,tools_condition

from mcp_client import call_mcp_tool


MODEL_NAME = os.getenv("MODEL")
from dotenv import load_dotenv
load_dotenv()

from state import IncidentState
from process.mock_ops.tools import get_logs as _get_logs ,get_metrics as _get_metrics 
from models import Hypothesis

@tool
async def get_logs(service : str) -> list[str]:
    """Get recent log lines for a service."""
    result = await call_mcp_tool("get_logs",{"service":service})

    return cast(list[str],result)

@tool
async def get_metrics(service : str) -> dict:
    """Get the current metrics snapshot for a service."""
    result = await call_mcp_tool("get_metrics",{"service":service})

    return cast(dict,result) 

@tool
async def get_disk_usage(service: str) -> dict:
    """Get disk usage for a service, if it tracks disk metrics."""
    result = await call_mcp_tool("get_disk_usage", {"service": service})
    return cast(dict,result)

TOOLS = [get_logs,get_metrics]

# class TriageState(TypedDict):
#     messages : Annotated[list[AnyMessage],add_messages]
#     alert : str
#     hypothesis : Optional[Hypothesis]
#     timeline : list[str]

llm = ChatGroq(model=MODEL_NAME,temperature=0)
llm_with_tools = llm.bind_tools(TOOLS)
llm_structured = llm.with_structured_output(Hypothesis,method="function_calling")

SYSTEM_PROMPT = (
    "You are an SRE triage agent investigating a production alert. You "
    "have three read-only tools: get_logs, get_metrics (error rate / "
    "latency), and get_disk_usage. Not every tool is relevant to every "
    "alert -- read the alert text and only call the ones that plausibly "
    "apply before concluding anything. Only call each tool once unless "
    "you have a specific reason to call it again."  
)



def triage_agent(state : IncidentState) -> dict :

    messages = state["messages"]
    humMess = state["alert"]
    
    if not messages :
        messages = [SystemMessage(content=SYSTEM_PROMPT) , HumanMessage(content=humMess)]
    response = llm_with_tools.invoke(messages)

    if not state["messages"]:
        return {
            "messages" : [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=state["alert"]),
                response,
            ]
        }
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

