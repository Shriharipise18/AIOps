"""
Anthropic Claude implementation of the LLMProvider.
Requires ANTHROPIC_API_KEY environment variable.
"""
import os
import json
import re
from anthropic import AsyncAnthropic

from app.services.llm.provider import LLMProvider
from app.core.logging import get_logger

logger = get_logger(__name__)

class ClaudeProvider(LLMProvider):
    def __init__(self, model: str = "claude-3-5-sonnet-20240620"):
        self.model = model
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            logger.warning("ANTHROPIC_API_KEY not set. ClaudeProvider will fail if called.")
        self.client = AsyncAnthropic(api_key=api_key)

    @property
    def name(self) -> str:
        return self.model

    async def generate_structured_json(self, system_prompt: str, user_prompt: str) -> dict:
        try:
            # We explicitly ask Claude to output only JSON, but we also extract it via regex just in case
            full_user_prompt = f"{user_prompt}\n\nPlease respond ONLY with valid JSON. Do not include markdown code blocks or any other text."
            
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": full_user_prompt}
                ],
                temperature=0.2,
            )
            
            content = response.content[0].text
            
            # Attempt to extract JSON if Claude added markdown fences despite instructions
            match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            if match:
                content = match.group(1)
                
            return json.loads(content)
        except Exception as e:
            logger.error("Claude generation failed: %s", e)
            raise ValueError(f"Failed to generate valid JSON from Claude: {e}")
