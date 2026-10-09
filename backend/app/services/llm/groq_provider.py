"""Groq chat-completions implementation using Groq's OpenAI-compatible API."""
import json
from typing import Any

from openai import AsyncOpenAI

from app.core.config import settings
from app.core.logging import get_logger
from app.services.llm.provider import LLMProvider

logger = get_logger(__name__)


class GroqProvider(LLMProvider):
    def __init__(self):
        if not settings.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is not configured")
        self.model = settings.GROQ_MODEL
        self.client = AsyncOpenAI(
            api_key=settings.GROQ_API_KEY.get_secret_value(),
            base_url=settings.GROQ_BASE_URL,
        )

    @property
    def name(self) -> str:
        return f"Groq · {self.model}"

    async def generate_structured_json(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: dict | None = None,
    ) -> dict[str, str]:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        for attempt in range(2):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    response_format=(
                        {
                            "type": "json_schema",
                            "json_schema": {
                                "name": "devops_artifact_bundle",
                                "strict": True,
                                "schema": response_schema,
                            },
                        }
                        if response_schema
                        else {"type": "json_object"}
                    ),
                    max_completion_tokens=16384,
                    temperature=0.2,
                )

                content = response.choices[0].message.content
                parsed: Any = json.loads(content or "")
                if not isinstance(parsed, dict) or not parsed:
                    raise ValueError("The model response must be a non-empty JSON object")
                if any(not isinstance(filename, str) or not isinstance(body, str) for filename, body in parsed.items()):
                    raise ValueError("The model response must map artifact filenames to text contents")
                return parsed
            except Exception as exc:
                if attempt == 0 and self._is_json_validation_error(exc):
                    logger.warning("Groq rejected generated JSON; retrying once with stricter formatting instructions")
                    messages.append({
                        "role": "user",
                        "content": (
                            "Regenerate the complete requested JSON object. Return strict JSON only: "
                            "escape quotes and backslashes in every file content, encode newlines as \\n, "
                            "and do not include markdown or trailing commas."
                        ),
                    })
                    continue

                logger.error("Groq generation failed (%s)", type(exc).__name__)
                raise ValueError(f"Groq generation failed: {type(exc).__name__}") from exc

        raise ValueError("Groq generation failed: JSON validation")

    @staticmethod
    def _is_json_validation_error(exc: Exception) -> bool:
        """Groq occasionally rejects malformed JSON-mode output with a 400."""
        if isinstance(exc, json.JSONDecodeError):
            return True
        body = getattr(exc, "body", None)
        error = body.get("error", {}) if isinstance(body, dict) else {}
        return isinstance(error, dict) and error.get("code") == "json_validate_failed"
