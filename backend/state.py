from typing import Annotated,TypedDict , Optional

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

class IncidentState(TypedDict):
    messages : Annotated[list[AnyMessage],add_messages]
    alert : str
    hypothesis : Optional[dict]
    proposal : Optional[dict]
    guardrail_result : Optional[dict]
    approved : Optional[bool]
    result : Optional[dict]
    actions_taken : list[dict]
    stop_reason : Optional[dict]
    timeline : list[str]

    