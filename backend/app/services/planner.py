"""
AI Deployment Planner.

Converts a repository profile and user requirements into a deterministic
Deployment Specification, and uses an LLM to generate DevOps artifacts.
"""
import json
from typing import Any
from app.services.llm.provider import LLMProvider, artifact_mapping_schema
from app.services.template_generator import generate_artifacts_deterministically

from app.core.logging import get_logger

logger = get_logger(__name__)


def generate_deployment_spec(profile: dict, req: dict) -> dict:
    """
    Deterministically build an intermediate deployment specification 
    based on the profile and user requirements.
    """
    # 1. Base App Spec
    app_spec = {
        "name": f"app-{str(profile.get('project_id', 'sample'))[:8]}",
        "language": profile.get("language"),
        "framework": profile.get("framework"),
        "package_manager": profile.get("package_manager"),
        "entrypoint": profile.get("entrypoint"),
        "build_command": profile.get("build_command"),
        "start_command": profile.get("start_command"),
        "port": req.get("container_port") or profile.get("port") or 8080,
        "files": profile.get("raw_files") or [],
    }

    # 2. Container Spec
    container_spec = {
        "base_image": _infer_base_image(profile),
        "port": app_spec["port"],
        "env_vars": profile.get("env_vars") or [],
    }

    # 3. Target Platform Spec
    platform_spec = {
        "platform": req.get("deployment_platform", "Kubernetes"),
        "provider": req.get("cloud_provider", "AWS"),
        "replicas": req.get("replicas", 1),
        "cpu_limit": req.get("cpu_limit"),
        "memory_limit": req.get("memory_limit"),
        "autoscaling": req.get("autoscaling", False),
        "is_public": req.get("is_public", True),
    }

    # 4. Services Spec
    services_spec = []
    if req.get("include_database"):
        services_spec.append({
            "type": "database",
            "engine": profile.get("database") or "MongoDB",
        })
    if req.get("include_redis"):
        services_spec.append({
            "type": "cache",
            "engine": "Redis",
        })

    return {
        "application": app_spec,
        "container": container_spec,
        "platform": platform_spec,
        "services": services_spec,
    }


def _infer_base_image(profile: dict) -> str:
    """Very simple heuristic to pick a base image."""
    lang = (profile.get("language") or "").lower()
    if lang == "node.js":
        return "node:20-alpine"
    elif lang == "python":
        return "python:3.12-slim"
    elif lang == "java":
        return "eclipse-temurin:21-jre-alpine"
    return "alpine:latest"


async def generate_artifacts_via_llm(provider: LLMProvider, spec: dict) -> dict:
    """
    Send the deterministic spec to the LLM to generate the final artifacts.
    """
    system_prompt = """You are an expert DevOps Architect.
Your job is to generate infrastructure configuration files based on the provided JSON specification.

Output ONLY a JSON object where the keys are filenames and the values are raw text content.
Do not include any explanation or markdown outside of the JSON object.

Rules:
1. Generate a secure, non-root Dockerfile and the requested platform files.
2. If Kubernetes is selected, generate kubernetes/deployment.yaml and kubernetes/service.yaml; add ingress and HPA only when requested.
3. If Kubernetes is selected, also include a valid Helm chart under helm/ with Chart.yaml, values.yaml, and templates.
4. If Docker Compose is selected, generate docker-compose.yml.
5. Include a GitHub Actions quality workflow at .github/workflows/devops-ci.yml. It may build and validate artifacts, but must not publish images or deploy without credentials and explicit setup.
6. Never copy secret values into generated files. Use only the environment variable names in the specification.
7. Always generate a Dockerfile when application details are provided.
"""

    user_prompt = f"""Generate DevOps artifacts for the following Deployment Specification:
{json.dumps(spec, indent=2)}
"""

    logger.info("Requesting artifacts from %s...", provider.name)
    expected_files = generate_artifacts_deterministically(spec).keys()
    artifacts = await provider.generate_structured_json(
        system_prompt,
        user_prompt,
        response_schema=artifact_mapping_schema(expected_files),
    )
    logger.info("Successfully generated %d artifacts from %s", len(artifacts), provider.name)
    
    return artifacts
