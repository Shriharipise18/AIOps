"""
OpenAI implementation of the LLMProvider.
Requires OPENAI_API_KEY environment variable.
"""
import json
from openai import AsyncOpenAI

from app.services.llm.provider import LLMProvider
from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)

class OpenAIProvider(LLMProvider):
    def __init__(self, model: str = "gpt-4o"):
        self.model = model
        api_key = settings.OPENAI_API_KEY.get_secret_value() if settings.OPENAI_API_KEY else None
        if not api_key:
            logger.warning("OPENAI_API_KEY not set. OpenAIProvider will fail if called.")
        self.client = AsyncOpenAI(api_key=api_key)

    @property
    def name(self) -> str:
        return self.model

    async def generate_structured_json(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: dict | None = None,
    ) -> dict:
        try:
            response_format = (
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
            )
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format=response_format,
                temperature=0.2, # Low temperature for more deterministic outputs
            )
            
            content = response.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            logger.error("OpenAI generation failed: %s", e)
            raise ValueError(f"Failed to generate valid JSON from OpenAI: {e}")
