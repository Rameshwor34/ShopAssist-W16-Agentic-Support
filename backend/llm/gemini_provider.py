import json
import os
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from google import genai

load_dotenv(override=True)


class GeminiProvider:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError("GEMINI_API_KEY is not configured")

        self.model = os.getenv(
            "GEMINI_MODEL",
            "gemini-3.6-flash",
        )

        self.client = genai.Client(
            api_key=api_key
        )

        self.last_usage: Dict[str, Any] = {}

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
        top_p: float = 0.9,
        tools: Optional[list] = None,
    ) -> Dict[str, Any]:

        try:
            interaction = self.client.interactions.create(
                model=self.model,
                input=user_prompt,
                system_instruction=system_prompt,
                generation_config={
                    "temperature": temperature,
                    "top_p": top_p,
                },
            )

            output_text = getattr(
                interaction,
                "output_text",
                None,
            )

            if not output_text:
                raise RuntimeError(
                    "Gemini returned no output_text"
                )

            output_text = output_text.strip()

            usage = self._extract_usage(
                interaction,
                system_prompt,
                user_prompt,
                output_text,
            )

            self.last_usage = usage

            try:
                result = json.loads(output_text)

            except json.JSONDecodeError:
                result = {
                    "intent": "general_support",
                    "answer": output_text,
                    "confidence": 0.8,
                    "sources": [],
                    "tool_used": "none",
                }

            result["_usage"] = usage

            return result

        except Exception as exc:
            print(
                f"Gemini request failed: "
                f"{type(exc).__name__}: {exc}"
            )
            raise

    def _extract_usage(
        self,
        interaction: Any,
        system_prompt: str,
        user_prompt: str,
        output_text: str,
    ) -> Dict[str, Any]:

        usage = getattr(
            interaction,
            "usage",
            None,
        )

        if usage is not None:

            input_tokens = self._first_int(
                usage,
                [
                    "input_tokens",
                    "prompt_tokens",
                    "input_token_count",
                ],
            )

            output_tokens = self._first_int(
                usage,
                [
                    "output_tokens",
                    "completion_tokens",
                    "output_token_count",
                ],
            )

            total_tokens = self._first_int(
                usage,
                [
                    "total_tokens",
                    "total_token_count",
                ],
            )

            if total_tokens is None:
                if (
                    input_tokens is not None
                    and output_tokens is not None
                ):
                    total_tokens = (
                        input_tokens
                        + output_tokens
                    )

            if total_tokens is not None:

                return {
                    "input_tokens": input_tokens or 0,
                    "output_tokens": output_tokens or 0,
                    "total_tokens": total_tokens,
                    "estimated": False,
                }

        return self._estimate_tokens(
            system_prompt,
            user_prompt,
            output_text,
        )

    @staticmethod
    def _first_int(
        obj: Any,
        names: list,
    ) -> Optional[int]:

        for name in names:
            value = getattr(
                obj,
                name,
                None,
            )

            if isinstance(value, int):
                return value

        return None

    @staticmethod
    def _estimate_tokens(
        system_prompt: str,
        user_prompt: str,
        output_text: str,
    ) -> Dict[str, Any]:

        input_chars = len(
            system_prompt
            + "\n"
            + user_prompt
        )

        output_chars = len(
            output_text
        )

        input_tokens = max(
            1,
            (input_chars + 3) // 4,
        )

        output_tokens = max(
            1,
            (output_chars + 3) // 4,
        )

        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": (
                input_tokens
                + output_tokens
            ),
            "estimated": True,
        }
