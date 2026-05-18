from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from pydantic import BaseModel, Field


class PlanStep(BaseModel):
    """One investigation step produced by the Planner."""
    step_id: str = Field(description="Unique ID like 'step_1', 'step_2'")
    sub_question: str = Field(description="The specific sub-question this step answers")
    tool: str = Field(description="Registered tool name to use")
    finding_key: str = Field(description="Key under which result is stored in findings")
    depends_on: List[str] = Field(default_factory=list, description="step_ids that must finish first")
    priority: int = Field(default=1, description="Execution ordering hint (lower = earlier)")
    weight: float = Field(description="Contribution to coverage score; all weights sum to 1.0")


class InvestigationPlan(BaseModel):
    """Full investigation plan produced by the Planner."""
    steps: List[PlanStep] = Field(description="Between 6 and 10 investigation steps")

    def normalize_weights(self) -> None:
        total = sum(s.weight for s in self.steps)
        if total > 0:
            for s in self.steps:
                s.weight = round(s.weight / total, 4)


@dataclass
class ToolResult:
    content: str
    sources: List[str] = field(default_factory=list)
    credibility_score: float = 0.70


@dataclass
class Finding:
    step_id: str
    sub_question: str
    tool: str
    finding_key: str
    content: str
    sources: List[str] = field(default_factory=list)
    credibility_score: float = 0.70
    status: str = "pending"
    error: Optional[str] = None
