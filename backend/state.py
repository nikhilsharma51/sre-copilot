from typing import Annotated,TypedDict , Optional
from models import Hypothesis
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

class IncidentState(TypedDict):
    messages : Annotated[list[AnyMessage],add_messages]
    alert : str
    severity:str
    hypothesis : Optional[Hypothesis]
    proposal : Optional[dict]
    guardrail_result : Optional[dict]
    approved : Optional[bool]
    result : Optional[dict]
    actions_taken : list[dict]
    stop_reason : Optional[str]
    timeline : list[str]

    