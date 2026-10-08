from typing import Any, Dict, Literal

from pydantic import BaseModel, Field


AgentAction = Literal[
    "search_knowledge",
    "get_order_status",
    "get_product_info",
    "check_return_eligibility",
    "ask_clarification",
    "final_answer",
]


class AgentDecision(BaseModel):
    """
    Structured decision produced by the W16 agent.

    The LLM proposes an action, but the application validates this
    structure before any tool is executed.
    """

    action: AgentAction = Field(
        description="The next action the agent wants to perform."
    )

    arguments: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arguments required by the selected action."
    )

    reason: str = Field(
        min_length=1,
        description="Brief operational justification for the selected action."
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Agent confidence in the proposed next action."
    )
