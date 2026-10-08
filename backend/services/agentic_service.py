import time
from typing import Any, Dict

from backend.agents.agent import AgentDecisionEngine
from backend.agents.evidence import compact_observation
from backend.agents.executor import AgentActionExecutor
from backend.agents.state import AgentState
from backend.agents.prompts import FINAL_ANSWER_SYSTEM_PROMPT


MAX_ITERATIONS = 6


class AgenticService:
    """
    Executes the bounded W16 agentic loop.

    The LLM decides what action should happen next.
    The application validates and executes that action.
    """

    def __init__(
        self,
        decision_engine: AgentDecisionEngine,
        executor: AgentActionExecutor,
        provider,
    ):
        self.decision_engine = decision_engine
        self.executor = executor
        self.provider = provider

    def process(
        self,
        user_query: str,
    ) -> Dict[str, Any]:

        state = AgentState(
            user_query=user_query
        )

        started = time.perf_counter()

        while (
            state.iteration
            < MAX_ITERATIONS
        ):

            state.iteration += 1

            try:
                decision = (
                    self.decision_engine.decide(
                        state
                    )
                )

            except Exception as exc:

                state.mark_failed()

                state.add_trajectory_step(
                    {
                        "type": "hard_failure",
                        "iteration": state.iteration,
                        "error": (
                            f"{type(exc).__name__}: "
                            f"{exc}"
                        ),
                    }
                )

                break

            action = decision.action

            if action == "final_answer":

                answer = self._generate_final_answer(
                    state
                )

                state.mark_completed(
                    answer
                )

                break

            if action == "ask_clarification":

                observation = (
                    self.executor.execute(
                        action,
                        decision.arguments,
                    )
                )

                evidence = compact_observation(
                    action,
                    observation,
                )

                state.add_evidence(
                    evidence
                )

                state.mark_clarification_required()

                state.final_answer = (
                    observation.get(
                        "message",
                        "Please provide more information.",
                    )
                )

                break

            action_started = time.perf_counter()

            try:

                observation = (
                    self.executor.execute(
                        action,
                        decision.arguments,
                    )
                )

            except Exception as exc:

                observation = {
                    "success": False,
                    "error": (
                        f"{type(exc).__name__}: "
                        f"{exc}"
                    ),
                }

            action_latency = (
                time.perf_counter()
                - action_started
            ) * 1000

            evidence = compact_observation(
                action,
                observation,
            )

            state.add_evidence(
                evidence
            )

            state.add_trajectory_step(
                {
                    "type": "tool_execution",
                    "iteration": state.iteration,
                    "action": action,
                    "arguments": decision.arguments,
                    "success": observation.get(
                        "success",
                        False,
                    ),
                    "latency_ms": round(
                        action_latency,
                        3,
                    ),
                    "error": observation.get(
                        "error"
                    ),
                }
            )

        if (
            state.status == "running"
        ):

            state.mark_max_iterations()

            state.final_answer = (
                "I could not safely complete "
                "the request within the allowed "
                "number of reasoning steps."
            )

        state.total_latency_ms = (
            time.perf_counter()
            - started
        ) * 1000

        tool_calls = sum(
            1
            for item in state.trajectory
            if item.get("type")
            == "tool_execution"
        )

        decision_steps = sum(
            1
            for item in state.trajectory
            if item.get("type")
            == "decision"
        )

        return {
            "answer": state.final_answer,
            "status": state.status,
            "iterations": state.iteration,
            "tool_calls": tool_calls,
            "decision_steps": decision_steps,
            "total_tokens": state.total_tokens,
            "total_latency_ms": round(
                state.total_latency_ms,
                3,
            ),
            "sources": state.sources,
            "trajectory": state.trajectory,
            "evidence": state.evidence,
        }

    def _generate_final_answer(
        self,
        state: AgentState,
    ) -> str:

        prompt = self._build_final_prompt(
            state
        )

        started = time.perf_counter()

        result = self.provider.generate(
            system_prompt=FINAL_ANSWER_SYSTEM_PROMPT,
            user_prompt=prompt,
            temperature=0.1,
            top_p=0.9,
        )

        latency = (
            time.perf_counter()
            - started
        ) * 1000

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

        answer = result.get(
            "answer",
            "I could not produce a verified answer.",
        )

        state.add_trajectory_step(
            {
                "type": "final_answer_generation",
                "iteration": state.iteration,
                "latency_ms": round(
                    latency,
                    3,
                ),
                "tokens": usage,
            }
        )

        return answer

    @staticmethod
    def _build_final_prompt(
        state: AgentState,
    ) -> str:

        import json

        return json.dumps(
            {
                "user_query": state.user_query,
                "verified_evidence": state.evidence,
                "sources": state.sources,
                "conflicts": state.conflicts,
                "unresolved_questions": (
                    state.unresolved_questions
                ),
            },
            indent=2,
        )
