from pydantic import BaseModel,Field

class Hypothesis(BaseModel):
    root_cause : str =Field(description="One-sentence best guess at what's wrong")
    evidence: list[str] = Field(description="Specific log lines or metric values that support this")
    confidence: float = Field(ge=0, le=1, description="0-1 confidence in this hypothesis")

class RemediationProposal(BaseModel):
    action: str = Field(description="the action to take, e.g. 'restart_service'")
    target: str = Field(description="the service to act on")
    reasoning: str = Field(description="why this action addresses the hypothesis")
    confidence: float = Field(ge=0, le=1)