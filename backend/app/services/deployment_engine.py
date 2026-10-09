"""
Deployment Engine Service.
Handles calculating Readiness Score and performing deployments (Kubernetes).
"""
from typing import Dict, Any, List
import subprocess
import json
import os
import re
import shutil
import yaml
from pathlib import Path
from app.core.logging import get_logger

logger = get_logger(__name__)

def calculate_readiness_score(
    validation_status: str,
    security_report: dict,
    performance_report: dict,
    spec: dict
) -> dict:
    """
    Calculate deterministic explainable Readiness Score.
    """
    score = 100
    factors = []

    # 1. Validation Status
    if validation_status == "passed":
        factors.append({"factor": "Validation", "impact": 0, "reason": "All validations passed."})
    elif validation_status == "pending":
        score -= 50
        factors.append({"factor": "Validation", "impact": -50, "reason": "Validation is still pending."})
    else:
        score -= 100
        factors.append({"factor": "Validation", "impact": -100, "reason": f"Validation failed ({validation_status})."})

    # 2. Security Findings
    critical = sum(1 for f in security_report.get("findings", []) if f["severity"].lower() == "critical")
    high = sum(1 for f in security_report.get("findings", []) if f["severity"].lower() == "high")
    
    if critical > 0:
        score -= 40
        factors.append({"factor": "Security", "impact": -40, "reason": f"{critical} Critical vulnerabilities found."})
    if high > 0:
        score -= 20
        factors.append({"factor": "Security", "impact": -20, "reason": f"{high} High vulnerabilities found."})
    
    if critical == 0 and high == 0:
        factors.append({"factor": "Security", "impact": 0, "reason": "No high/critical vulnerabilities found."})

    # 3. Performance
    suboptimal = sum(1 for i in performance_report.get("insights", []) if i["status"].lower() != "optimal")
    if suboptimal > 0:
        penalty = 10 * suboptimal
        score -= penalty
        factors.append({"factor": "Performance", "impact": -penalty, "reason": f"{suboptimal} suboptimal performance configs."})
    else:
        factors.append({"factor": "Performance", "impact": 0, "reason": "Performance configs are optimal."})

    # Bound the score
    score = max(0, min(100, score))

    return {
        "score": score,
        "factors": factors,
        "is_ready": score >= 80,
    }

def get_kubernetes_target_status() -> dict:
    """Report whether kubectl has an active, reachable cluster context."""
    kubectl = shutil.which("kubectl")
    if not kubectl:
        return {
            "available": False,
            "context": None,
            "message": "kubectl is not installed on the backend machine.",
        }

    try:
        context_result = subprocess.run(
            [kubectl, "config", "current-context"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        context = context_result.stdout.strip()
        if context_result.returncode != 0 or not context:
            return {"available": False, "context": None, "message": "No active Kubernetes context is configured."}

        ready_result = subprocess.run(
            [kubectl, "--context", context, "get", "--raw=/readyz", "--request-timeout=5s"],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
        if ready_result.returncode != 0:
            return {"available": False, "context": context, "message": "The active Kubernetes context is not reachable."}
        return {"available": True, "context": context, "message": "Kubernetes cluster is reachable."}
    except (OSError, subprocess.TimeoutExpired):
        return {"available": False, "context": None, "message": "Kubernetes target check timed out."}


def _collect_deployable_manifests(artifacts: dict) -> tuple[str, list[dict]]:
    allowed_kinds = {"Deployment", "Service", "ConfigMap", "Ingress", "HorizontalPodAutoscaler"}
    manifests = []
    deployment_names = []
    service_names = []
    for artifact_name, content in artifacts.items():
        name = Path(artifact_name)
        if not name.as_posix().startswith("kubernetes/") or name.suffix.lower() not in {".yaml", ".yml"}:
            continue
        if "{{" in content:
            raise ValueError(f"Unrendered template syntax found in {artifact_name}.")
        try:
            documents = list(yaml.safe_load_all(content))
        except yaml.YAMLError as exc:
            raise ValueError(f"Invalid YAML in {artifact_name}.") from exc

        for document in documents:
            if not document:
                continue
            if not isinstance(document, dict) or document.get("kind") not in allowed_kinds:
                raise ValueError(f"Unsupported Kubernetes resource in {artifact_name}.")
            kind = document["kind"]
            metadata = document.get("metadata") or {}
            resource_name = metadata.get("name")
            if not resource_name:
                raise ValueError(f"A Kubernetes resource in {artifact_name} has no name.")
            if kind == "Deployment":
                deployment_names.append(resource_name)
                pod_spec = document.get("spec", {}).get("template", {}).get("spec", {})
                if any(pod_spec.get(flag) is True for flag in ("hostNetwork", "hostPID", "hostIPC")):
                    raise ValueError("Host namespace access is not allowed in generated workloads.")
                for volume in pod_spec.get("volumes", []):
                    if "hostPath" in volume:
                        raise ValueError("Host path mounts are not allowed in generated workloads.")
                for container in pod_spec.get("containers", []):
                    security_context = container.get("securityContext", {})
                    if security_context.get("privileged") is True or security_context.get("allowPrivilegeEscalation") is True:
                        raise ValueError("Privileged or privilege-escalating containers are not allowed.")
                    if security_context.get("capabilities", {}).get("add"):
                        raise ValueError("Adding Linux capabilities is not allowed in generated workloads.")
            elif kind == "Service":
                service_names.append(resource_name)
            manifests.append(document)

    if not deployment_names or not service_names:
        raise ValueError("Generated Kubernetes Deployment and Service manifests are required.")
    return deployment_names[0], manifests


def deploy_to_kubernetes(
    project_id: str,
    artifacts: dict,
    namespace: str = "default",
    expected_context: str | None = None,
) -> dict:
    """Apply validated project manifests to the explicitly confirmed context."""
    import tempfile

    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", namespace):
        return {"status": "unavailable", "message": "Namespace must be a valid lowercase Kubernetes name."}
    try:
        deployment_name, manifests = _collect_deployable_manifests(artifacts)
    except ValueError as exc:
        return {"status": "unavailable", "message": str(exc)}

    target = get_kubernetes_target_status()
    if not target["available"]:
        return {"status": "unavailable", "message": target["message"], "context": target.get("context")}
    if expected_context != target["context"]:
        return {"status": "unavailable", "message": "The active Kubernetes context changed. Review the target and retry.", "context": target.get("context")}

    manifest_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".yaml", delete=False) as manifest_file:
            yaml.safe_dump_all(manifests, manifest_file, sort_keys=False)
            manifest_path = manifest_file.name
        result = subprocess.run(
            [shutil.which("kubectl"), "--context", target["context"], "apply", "--namespace", namespace, "--filename", manifest_path, "--request-timeout=30s"],
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
        if result.returncode != 0:
            logger.warning("kubectl apply did not complete for project %s: %s", project_id, result.stderr[-1000:])
            return {"status": "unavailable", "message": "Kubernetes did not accept the deployment. Review the manifest and cluster permissions.", "context": target["context"], "namespace": namespace}

        return {
            "status": "success",
            "message": "Kubernetes accepted the generated resources.",
            "details": result.stdout.strip()[-4000:],
            "context": target["context"],
            "namespace": namespace,
            "deployment_name": deployment_name,
            "pods": [],
            "services": [],
        }
    except subprocess.TimeoutExpired:
        return {"status": "unavailable", "message": "Kubernetes deployment timed out. Check the cluster before retrying.", "context": target["context"], "namespace": namespace}
    except OSError:
        return {"status": "unavailable", "message": "kubectl could not be started by the backend.", "context": target["context"], "namespace": namespace}
    finally:
        if manifest_path:
            try:
                os.unlink(manifest_path)
            except OSError:
                logger.warning("Unable to remove temporary deployment manifest for project %s", project_id)


def get_deployment_status(deployment_name: str, namespace: str = "default") -> dict:
    """Read only this deployment's pods and service from the selected namespace."""
    target = get_kubernetes_target_status()
    if not target["available"]:
        return {"status": "unavailable", "message": target["message"], "context": target.get("context"), "pods": [], "services": []}
    kubectl = shutil.which("kubectl")
    selector = f"app.kubernetes.io/name={deployment_name}"
    try:
        pods_result = subprocess.run([kubectl, "--context", target["context"], "get", "pods", "--namespace", namespace, "--selector", selector, "--output", "json", "--request-timeout=10s"], capture_output=True, text=True, timeout=15, check=False)
        service_result = subprocess.run([kubectl, "--context", target["context"], "get", "service", deployment_name, "--namespace", namespace, "--output", "json", "--request-timeout=10s"], capture_output=True, text=True, timeout=15, check=False)
        pods_data = json.loads(pods_result.stdout) if pods_result.returncode == 0 else {"items": []}
        service_data = json.loads(service_result.stdout) if service_result.returncode == 0 else None
        pods = [{"name": item.get("metadata", {}).get("name"), "status": item.get("status", {}).get("phase", "Pending")} for item in pods_data.get("items", [])]
        services = []
        if service_data:
            ports = service_data.get("spec", {}).get("ports", [])
            services.append({"name": service_data.get("metadata", {}).get("name"), "cluster_ip": service_data.get("spec", {}).get("clusterIP"), "ports": ", ".join(f"{item.get('port')}:{item.get('targetPort')}" for item in ports)})
        return {"status": "Running" if pods and all(pod["status"] == "Running" for pod in pods) else "Progressing", "context": target["context"], "namespace": namespace, "pods": pods, "services": services}
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return {"status": "unavailable", "message": "Could not read deployment status from Kubernetes.", "context": target["context"], "namespace": namespace, "pods": [], "services": []}
