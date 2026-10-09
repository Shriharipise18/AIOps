"""
Security Analysis Engine.
Runs deterministic rules against generated artifacts to produce a Security Report.
"""
from typing import Dict, Any, List
import yaml


def analyze_security(artifacts: Dict[str, str]) -> Dict[str, Any]:
    """
    Produce a deterministic security report.
    Returns a dict with 'overall_status' and a list of 'findings'.
    """
    findings = []
    
    # Check Dockerfile
    dockerfile = artifacts.get("Dockerfile", "").lower()
    if dockerfile:
        if "user root" in dockerfile or "user " not in dockerfile:
            findings.append({
                "severity": "High",
                "finding": "Container runs as root user",
                "resource": "Dockerfile",
                "evidence": "Missing 'USER nonroot' or similar instruction.",
                "remediation": "Create a dedicated non-root user and switch to it using the USER instruction."
            })
        if "latest" in dockerfile:
            findings.append({
                "severity": "Medium",
                "finding": "Using 'latest' tag for base image",
                "resource": "Dockerfile",
                "evidence": "Found 'latest' in FROM instruction.",
                "remediation": "Pin the base image to a specific version or SHA to ensure reproducible builds."
            })

    # Check Kubernetes YAMLs
    for name, content in artifacts.items():
        if name.endswith(".yaml") or name.endswith(".yml"):
            try:
                docs = list(yaml.safe_load_all(content))
            except yaml.YAMLError:
                continue
            
            for doc in docs:
                if not doc or not isinstance(doc, dict):
                    continue
                
                kind = doc.get("kind")
                if kind == "Deployment":
                    spec = doc.get("spec", {}).get("template", {}).get("spec", {})
                    containers = spec.get("containers", [])
                    
                    for container in containers:
                        sec_ctx = container.get("securityContext", {})
                        
                        if sec_ctx.get("privileged") is True:
                            findings.append({
                                "severity": "Critical",
                                "finding": "Privileged container execution",
                                "resource": name,
                                "evidence": "securityContext.privileged is set to true.",
                                "remediation": "Remove the privileged flag or use fine-grained capabilities."
                            })
                            
                        if sec_ctx.get("readOnlyRootFilesystem") is not True:
                            findings.append({
                                "severity": "Low",
                                "finding": "Root filesystem is not read-only",
                                "resource": name,
                                "evidence": "Missing readOnlyRootFilesystem: true in securityContext.",
                                "remediation": "Set securityContext.readOnlyRootFilesystem to true."
                            })
                            
                        if sec_ctx.get("runAsNonRoot") is not True:
                            findings.append({
                                "severity": "Medium",
                                "finding": "Container might run as root",
                                "resource": name,
                                "evidence": "Missing runAsNonRoot: true in securityContext.",
                                "remediation": "Enforce non-root execution via securityContext.runAsNonRoot."
                            })

    overall = "Secure"
    if any(f["severity"] == "Critical" for f in findings):
        overall = "Critical Vulnerabilities"
    elif any(f["severity"] == "High" for f in findings):
        overall = "High Vulnerabilities"
    elif len(findings) > 0:
        overall = "Warnings Present"

    return {
        "overall_status": overall,
        "findings": findings
    }
