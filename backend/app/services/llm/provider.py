"""
Abstract Base Class for LLM Providers.
Ensures the rest of the application does not depend on a specific LLM API.
"""
from abc import ABC, abstractmethod
import json
from collections.abc import Iterable


def artifact_mapping_schema(filenames: Iterable[str]) -> dict:
    """Build a strict JSON Schema for the exact artifact paths requested."""
    names = sorted(set(filenames))
    return {
        "type": "object",
        "properties": {name: {"type": "string"} for name in names},
        "required": names,
        "additionalProperties": False,
    }

class LLMProvider(ABC):
    """
    Interface for LLM interactions.
    All providers must implement generate_structured_json.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name/model of the provider (e.g., 'gpt-4o', 'claude-3-sonnet')."""
        pass

    @abstractmethod
    async def generate_structured_json(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: dict | None = None,
    ) -> dict:
        """
        Generate structured JSON based on the provided prompts.
        Must guarantee that the output is a valid Python dictionary parsed from JSON.
        """
        pass
