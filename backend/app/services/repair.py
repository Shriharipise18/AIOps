"""
AI Repair Engine.
Handles automatic correction of generated artifacts based on deterministic validation errors.
"""
from typing import List, Dict, Any

from app.services.llm.provider import LLMProvider, artifact_mapping_schema
from app.core.logging import get_logger
import json

logger = get_logger(__name__)

MAX_REPAIR_ATTEMPTS = 3


async def attempt_repair(
    provider: LLMProvider,
    spec: Dict[str, Any],
    failed_artifacts: Dict[str, str],
    errors: List[Dict[str, str]]
) -> Dict[str, str]:
    """
    Given the spec, the previous artifacts, and the validation errors,
    ask the LLM to fix the issues and return the corrected artifacts.
    """
    
    system_prompt = """You are an expert DevOps Architect and automated repair engine.
Your previous generation failed deterministic validation. You must fix the errors and output the corrected configuration files.

Output ONLY a JSON object where the keys are filenames and the values are the raw text content of those files.
Do not include any explanation or markdown outside of the JSON object.
Ensure ALL required files are returned, not just the fixed ones.
"""

    error_summary = json.dumps(errors, indent=2)
    artifacts_summary = json.dumps(failed_artifacts, indent=2)
    spec_summary = json.dumps(spec, indent=2)

    user_prompt = f"""Deployment Specification:
{spec_summary}

Previous Artifacts that failed:
{artifacts_summary}

Validation Errors to fix:
{error_summary}

Please generate the corrected JSON mapping of filenames to file contents.
"""

    logger.info("Requesting repair from %s for %d errors...", provider.name, len(errors))
    corrected_artifacts = await provider.generate_structured_json(
        system_prompt,
        user_prompt,
        response_schema=artifact_mapping_schema(failed_artifacts.keys()),
    )
    logger.info("Successfully received repaired artifacts from %s", provider.name)
    
    return corrected_artifacts
