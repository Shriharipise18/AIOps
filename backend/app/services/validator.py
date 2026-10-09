"""
Validation Engine for DevOps Artifacts.
Performs deterministic static analysis on generated infrastructure code.
"""
import yaml
from typing import List, Dict, Any

from app.core.logging import get_logger

logger = get_logger(__name__)


def validate_artifacts(artifacts: Dict[str, str], spec: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Validates a set of generated artifacts against the deterministic specification.
    Returns a list of errors. Empty list means validation passed.
    """
    errors = []

    # 1. Dockerfile checks
    if "Dockerfile" not in artifacts:
        errors.append({
            "category": "docker",
            "artifact_name": "Dockerfile",
            "message": "Missing Dockerfile."
        })
    else:
        errors.extend(_validate_dockerfile(artifacts["Dockerfile"], spec))

    # 2. Kubernetes / Compose Checks
    platform = spec.get("platform", {}).get("platform", "").lower()
    if platform == "kubernetes":
        errors.extend(_validate_kubernetes(artifacts, spec))
    elif platform == "docker compose":
        errors.extend(_validate_docker_compose(artifacts, spec))

    # 3. Built-in deterministic security heuristics (no external scanner claimed)
    errors.extend(_validate_security(artifacts))

    return errors


def _validate_dockerfile(content: str, spec: Dict[str, Any]) -> List[Dict[str, str]]:
    errors = []
    expected_port = spec.get("container", {}).get("port")
    
    if expected_port and f"EXPOSE {expected_port}" not in content:
        errors.append({
            "category": "docker",
            "artifact_name": "Dockerfile",
            "message": f"Dockerfile must expose the configured port: EXPOSE {expected_port}"
        })
        
    return errors


def _validate_kubernetes(artifacts: Dict[str, str], spec: Dict[str, Any]) -> List[Dict[str, str]]:
    errors = []
    
    expected_replicas = spec.get("platform", {}).get("replicas", 1)
    expected_port = spec.get("container", {}).get("port")

    deployment_found = False
    service_found = False

    for name, content in artifacts.items():
        if not name.endswith(".yaml") and not name.endswith(".yml"):
            continue
        # Helm templates contain Go-template directives; they are rendered and
        # checked by the generated Helm CI step instead of parsing as plain YAML.
        if name.startswith("helm/templates/") or "{{" in content:
            continue

        try:
            # Parse all YAML documents in the file (often separated by ---)
            docs = list(yaml.safe_load_all(content))
        except yaml.YAMLError as e:
            errors.append({
                "category": "kubernetes",
                "artifact_name": name,
                "message": f"Invalid YAML syntax: {str(e)}"
            })
            continue

        for doc in docs:
            if not doc or not isinstance(doc, dict):
                continue
            
            kind = doc.get("kind")
            
            if kind == "Deployment":
                deployment_found = True
                spec_block = doc.get("spec", {})
                replicas = spec_block.get("replicas")
                
                # Check replicas
                if replicas != expected_replicas:
                    errors.append({
                        "category": "kubernetes",
                        "artifact_name": name,
                        "message": f"Deployment replicas ({replicas}) do not match spec ({expected_replicas})."
                    })
                
                # Check ports in containers
                containers = spec_block.get("template", {}).get("spec", {}).get("containers", [])
                for container in containers:
                    ports = container.get("ports", [])
                    has_expected_port = any(p.get("containerPort") == expected_port for p in ports)
                    if expected_port and not has_expected_port:
                        errors.append({
                            "category": "kubernetes",
                            "artifact_name": name,
                            "message": f"Container in Deployment must expose port {expected_port}."
                        })
            
            elif kind == "Service":
                service_found = True
                ports = doc.get("spec", {}).get("ports", [])
                has_expected_port = any(p.get("targetPort") == expected_port for p in ports)
                if expected_port and not has_expected_port:
                    errors.append({
                        "category": "kubernetes",
                        "artifact_name": name,
                        "message": f"Service targetPort must match application port {expected_port}."
                    })

    if not deployment_found:
        errors.append({
            "category": "kubernetes",
            "artifact_name": None,
            "message": "Missing Kubernetes Deployment resource."
        })
    if not service_found:
        errors.append({
            "category": "kubernetes",
            "artifact_name": None,
            "message": "Missing Kubernetes Service resource."
        })

    return errors


def _validate_docker_compose(artifacts: Dict[str, str], spec: Dict[str, Any]) -> List[Dict[str, str]]:
    errors = []
    
    compose_file = artifacts.get("docker-compose.yml") or artifacts.get("docker-compose.yaml")
    if not compose_file:
        errors.append({
            "category": "docker",
            "artifact_name": "docker-compose.yml",
            "message": "Missing docker-compose.yml file."
        })
        return errors

    try:
        doc = yaml.safe_load(compose_file)
        if not doc or "services" not in doc:
            errors.append({
                "category": "docker",
                "artifact_name": "docker-compose.yml",
                "message": "docker-compose.yml is missing 'services' block."
            })
    except yaml.YAMLError as e:
        errors.append({
            "category": "docker",
            "artifact_name": "docker-compose.yml",
            "message": f"Invalid YAML syntax: {str(e)}"
        })

    return errors


def _validate_security(artifacts: Dict[str, str]) -> List[Dict[str, str]]:
    """Statically check for a few high-risk configuration mistakes."""
    errors = []
    
    if "Dockerfile" in artifacts:
        content = artifacts["Dockerfile"].lower()
        if "user root" in content:
            errors.append({
                "category": "security",
                "artifact_name": "Dockerfile",
                "message": "Running containers as root is a security risk. Switch to a non-root user."
            })
            
    for name, content in artifacts.items():
        if name.endswith(".yaml") or name.endswith(".yml"):
            if "privileged: true" in content:
                errors.append({
                    "category": "security",
                    "artifact_name": name,
                    "message": "Privileged containers detected. This is a severe security risk."
                })
                
    return errors
