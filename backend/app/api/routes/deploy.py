"""Readiness and real Kubernetes deployment endpoints."""
import asyncio
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.db.database import get_db
from app.models.validation import ValidationStatus
from app.services.analysis.performance import analyze_performance
from app.services.analysis.security import analyze_security
from app.services.deployment_engine import (
    calculate_readiness_score,
    deploy_to_kubernetes,
    get_deployment_status,
    get_kubernetes_target_status,
)
from app.services.validator import validate_artifacts

router = APIRouter(tags=["Deployment Engine"])


class DeploymentRequest(BaseModel):
    namespace: str = Field(default="default", pattern=r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
    expected_context: str = Field(min_length=1, max_length=256)


@router.get("/deployment-target")
async def get_deployment_target():
    """Report the active kubectl context and its reachability."""
    return await asyncio.to_thread(get_kubernetes_target_status)


async def _current_state(project_id: uuid.UUID, db):
    key = str(project_id)
    project = await db.projects.find_one({"_id": key})
    generation = await db.artifact_generations.find_one(
        {"project_id": key}, sort=[("artifact_version", -1)]
    )
    if not project or not generation:
        return project, generation, {}, None
    validation = await db.validation_runs.find_one(
        {"project_id": key, "generation_id": generation["id"]},
        sort=[("created_at", -1)],
    )
    specification = project.get("deployment_spec", {}).get("specification", {})
    return project, generation, specification, validation


@router.get("/projects/{project_id}/readiness")
async def get_project_readiness(project_id: uuid.UUID, db=Depends(get_db)):
    """Calculate a deterministic readiness score for the current artifacts."""
    project, generation, specification, validation = await _current_state(project_id, db)
    if not project or not generation:
        raise HTTPException(status_code=404, detail="No artifacts generated yet.")
    validation_status = validation["status"] if validation else "pending"
    security_report = analyze_security(generation["artifacts"])
    performance_report = analyze_performance(generation["artifacts"], specification)
    return calculate_readiness_score(validation_status, security_report, performance_report, specification)


@router.post("/projects/{project_id}/deploy")
async def trigger_deployment(project_id: uuid.UUID, request: DeploymentRequest, db=Depends(get_db)):
    """Apply validated Kubernetes manifests to the confirmed current context."""
    project, generation, specification, validation = await _current_state(project_id, db)
    if not project or not generation:
        raise HTTPException(status_code=404, detail="No artifacts found to deploy.")
    if str(specification.get("platform", {}).get("platform", "")).lower() != "kubernetes":
        raise HTTPException(status_code=409, detail="Select Kubernetes as the deployment platform before deploying to a cluster.")
    if not validation or validation["status"] != ValidationStatus.PASSED.value:
        raise HTTPException(status_code=409, detail="Run and pass validation before deployment.")
    if validate_artifacts(generation["artifacts"], specification):
        raise HTTPException(status_code=409, detail="The current artifacts no longer pass validation.")

    security_report = analyze_security(generation["artifacts"])
    performance_report = analyze_performance(generation["artifacts"], specification)
    readiness = calculate_readiness_score("passed", security_report, performance_report, specification)
    if not readiness["is_ready"]:
        raise HTTPException(status_code=409, detail="Improve the readiness score to at least 80 before deployment.")

    result = await asyncio.to_thread(
        deploy_to_kubernetes,
        str(project_id),
        generation["artifacts"],
        request.namespace,
        request.expected_context,
    )
    if result.get("status") != "success":
        raise HTTPException(status_code=409, detail=result.get("message", "Kubernetes target is unavailable."))
    deployed_at = datetime.now(timezone.utc)
    deployment_id = str(uuid.uuid4())
    deployment_record = {
        **result,
        "deployment_id": deployment_id,
        "project_id": str(project_id),
        "generation_id": generation["id"],
        "created_at": deployed_at,
    }
    await db.deployments.insert_one({"_id": deployment_id, **deployment_record})
    await db.projects.update_one(
        {"_id": str(project_id)},
        {"$set": {"last_deployment": deployment_record, "updated_at": deployed_at}},
    )
    result["deployment_id"] = deployment_id
    result["created_at"] = deployed_at
    return result


@router.get("/projects/{project_id}/deploy/status")
async def fetch_deployment_status(
    project_id: uuid.UUID,
    namespace: str | None = Query(default=None, pattern=r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$"),
    db=Depends(get_db),
):
    """Read live pod and service state from the target cluster."""
    project = await db.projects.find_one({"_id": str(project_id)})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    specification = project.get("deployment_spec", {}).get("specification", {})
    if str(specification.get("platform", {}).get("platform", "")).lower() != "kubernetes":
        return {"status": "not_applicable", "message": "This project is configured for Docker Compose.", "pods": [], "services": []}
    last_deployment = project.get("last_deployment")
    latest_generation = await db.artifact_generations.find_one(
        {"project_id": str(project_id)}, sort=[("artifact_version", -1)], projection={"id": 1}
    )
    if not last_deployment or not latest_generation or last_deployment.get("generation_id") != latest_generation.get("id"):
        return {"status": "not_deployed", "message": "This project has not been deployed yet.", "pods": [], "services": []}
    target_namespace = namespace or last_deployment.get("namespace") or "default"
    app_name = last_deployment.get("deployment_name") or specification.get("application", {}).get("name") or f"app-{str(project_id)[:8]}"
    return await asyncio.to_thread(get_deployment_status, app_name, target_namespace)
