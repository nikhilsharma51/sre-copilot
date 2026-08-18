from pydantic import BaseModel,Field

class Hypothesis(BaseModel):
    root_cause : str =Field(description="One-sentence best guess at what's wrong")
    evidence: list[str] = Field(description="Specific log lines or metric values that support this")
    confidence: float = Field(ge=0, le=1, description="0-1 confidence in this hypothesis")
    