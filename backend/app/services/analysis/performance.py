"""
Performance Engine.
Analyzes artifacts for resource limits, probes, and autoscaling configurations.
"""
from typing import Dict, Any, List
import yaml

def analyze_performance(artifacts: Dict[str, str], spec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Checks K8s manifests for CPU/Memory limits and readiness/liveness probes.
    """
    insights = []
    
    has_hpa = spec.get("platform", {}).get("autoscaling", False)
    if has_hpa:
        insights.append({
            "topic": "Autoscaling",
            "status": "Optimal",
            "message": "Horizontal Pod Autoscaling (HPA) is enabled. The application can scale under load."
        })
    else:
        insights.append({
            "topic": "Autoscaling",
            "status": "Warning",
            "message": "Autoscaling is disabled. The system cannot dynamically react to traffic spikes."
        })

    # Kubernetes specific checks
    for name, content in artifacts.items():
        if not (name.endswith(".yaml") or name.endswith(".yml")):
            continue
            
        try:
            docs = list(yaml.safe_load_all(content))
        except yaml.YAMLError:
            continue
            
        for doc in docs:
            if not doc or not isinstance(doc, dict):
                continue
                
            if doc.get("kind") == "Deployment":
                containers = doc.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])
                for container in containers:
                    # Resource Limits
                    resources = container.get("resources", {})
                    limits = resources.get("limits", {})
                    requests = resources.get("requests", {})
                    
                    if not limits.get("cpu") or not limits.get("memory"):
                        insights.append({
                            "topic": "Resource Limits",
                            "status": "Warning",
                            "message": f"Container '{container.get('name', 'app')}' is missing strict CPU/Memory limits. This can cause node resource exhaustion."
                        })
                    else:
                        insights.append({
                            "topic": "Resource Limits",
                            "status": "Optimal",
                            "message": f"CPU/Memory limits are explicitly defined."
                        })

                    # Health Probes
                    if not container.get("livenessProbe"):
                        insights.append({
                            "topic": "Health Probes",
                            "status": "Warning",
                            "message": "Missing liveness probe. Kubernetes cannot automatically restart deadlocked containers."
                        })
                    if not container.get("readinessProbe"):
                        insights.append({
                            "topic": "Health Probes",
                            "status": "Warning",
                            "message": "Missing readiness probe. Traffic may be sent to containers before they are fully initialized."
                        })

    if not insights:
        insights.append({
            "topic": "General",
            "status": "Info",
            "message": "No performance-related insights could be statically determined from the generated artifacts."
        })

    return {
        "insights": insights
    }
