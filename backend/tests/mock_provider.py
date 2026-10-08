from typing import Any, Dict, List


class MockAgentProvider:
    """
    Deterministic provider for W16 evaluation.

    Separate queues are maintained for decisions and final answers.
    Token usage is estimated deterministically so evaluation metrics
    can be calculated without using Gemini API quota.
    """

    def __init__(
        self,
        decisions: List[Dict[str, Any]],
        final_answer: str = "Mock verified answer.",
    ):
        self.decisions = list(
            decisions
        )

        self.final_answer = final_answer

        self.decision_index = 0

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        top_p: float = 0.9,
        tools=None,
    ) -> Dict[str, Any]:

        if (
            "final response generator"
            in system_prompt.lower()
        ):

            output = {
                "answer": self.final_answer,
            }

            return self._with_usage(
                output,
                system_prompt,
                user_prompt,
                self.final_answer,
            )

        if (
            self.decision_index
            >= len(self.decisions)
        ):

            raise RuntimeError(
                "Mock provider has no remaining decisions."
            )

        decision = self.decisions[
            self.decision_index
        ]

        self.decision_index += 1

        output_text = str(
            decision
        )

        return self._with_usage(
            decision,
            system_prompt,
            user_prompt,
            output_text,
        )

    @staticmethod
    def _with_usage(
        result: Dict[str, Any],
        system_prompt: str,
        user_prompt: str,
        output_text: str,
    ) -> Dict[str, Any]:

        input_tokens = max(
            1,
            (
                len(
                    system_prompt
                    + "\n"
                    + user_prompt
                )
                + 3
            )
            // 4,
        )

        output_tokens = max(
            1,
            (
                len(output_text)
                + 3
            )
            // 4,
        )

        result = dict(result)

        result["_usage"] = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": (
                input_tokens
                + output_tokens
            ),
            "estimated": True,
        }

        return result
