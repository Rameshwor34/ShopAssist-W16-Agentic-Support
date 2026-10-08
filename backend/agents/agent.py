import json
from typing import Any, Dict

from backend.agents.prompts import AGENT_SYSTEM_PROMPT
from backend.agents.schemas import AgentDecision
from backend.agents.state import AgentState


class AgentDecisionEngine:
    """
    LLM-driven decision engine for the bounded W16 agentic loop.
    """

    def __init__(self, provider):
        self.provider = provider

    def decide(
        self,
        state: AgentState,
    ) -> AgentDecision:

        context = self._build_context(state)

        result = self.provider.generate(
            system_prompt=AGENT_SYSTEM_PROMPT,
            user_prompt=context,
            temperature=0.1,
            top_p=0.9,
        )

        usage = result.pop(
            "_usage",
            {},
        )

        state.total_tokens += int(
            usage.get(
                "total_tokens",
                0,
            )
        )

        decision = AgentDecision.model_validate(
            result
        )

        state.add_trajectory_step(
            {
                "type": "decision",
                "iteration": state.iteration,
                "action": decision.action,
                "arguments": decision.arguments,
                "reason": decision.reason,
                "confidence": decision.confidence,
                "tokens": usage,
            }
        )

        return decision

    def _build_context(
        self,
        state: AgentState,
    ) -> str:

        evidence = state.evidence[-6:]

        trajectory = state.trajectory[-6:]

        return json.dumps(
            {
                "user_query": state.user_query,
                "iteration": state.iteration,
                "evidence": evidence,
                "unresolved_questions": (
                    state.unresolved_questions
                ),
                "conflicts": state.conflicts,
                "recent_trajectory": trajectory,
            },
            indent=2,
        )
