"""Validation, repair, and generation history stored in MongoDB."""
from datetime import datetime, timezone
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pymongo import ReturnDocument

from app.core.logging import get_logger
from app.db.database import get_db
from app.models.validation import ValidationStatus
from app.schemas.deployment import ArtifactGenerationResponse
from app.schemas.validation import ValidationRunResponse
from app.services.llm.factory import get_llm_provider
from app.services.repair import attempt_repair, MAX_REPAIR_ATTEMPTS
from app.services.template_generator import generate_artifacts_deterministically
from app.services.validator import validate_artifacts

logger = get_logger(__name__)
router = APIRouter(tags=["Validation & Repair"])


def _now():
    return datetime.now(timezone.utc)


def _public(document: dict) -> dict:
    document.pop("_id", None)
    return document


async def _latest_generation(db, project_id: str):
    return await db.artifact_generations.find_one(
        {"project_id": project_id}, sort=[("artifact_version", -1)]
    )


async def _next_version(db, project_id: str) -> int:
    counter = await db.projects.find_one_and_update(
        {"_id": project_id},
        {"$inc": {"artifact_version_seq": 1}},
        return_document=ReturnDocument.AFTER,
    )
    if counter is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return counter["artifact_version_seq"]


@router.post("/projects/{project_id}/validate", response_model=ValidationRunResponse)
async def run_validation(project_id: uuid.UUID, db=Depends(get_db)):
    """Run built-in deterministic checks against the latest revision."""
    project_key = str(project_id)
    generation = await _latest_generation(db, project_key)
    if not generation:
        raise HTTPException(status_code=404, detail="No artifacts found to validate.")
    project = await db.projects.find_one({"_id": project_key})
    specification = (project or {}).get("deployment_spec", {}).get("specification", {})
    findings = validate_artifacts(generation["artifacts"], specification)
    status = ValidationStatus.PASSED.value if not findings else ValidationStatus.FAILED.value
    run_id = str(uuid.uuid4())
    run = {
        "_id": run_id,
        "id": run_id,
        "project_id": project_key,
        "generation_id": generation["id"],
        "status": status,
        "stage_failed": None,
        "created_at": _now(),
        "errors": [
            {
                "category": finding.get("category", "validation"),
                "artifact_name": finding.get("artifact_name"),
                "message": finding["message"],
                "severity": finding.get("severity", "error"),
            }
            for finding in findings
        ],
    }
    await db.validation_runs.insert_one(run)
    return _public(run)


@router.post("/projects/{project_id}/repair", response_model=ArtifactGenerationResponse)
async def execute_repair(project_id: uuid.UUID, db=Depends(get_db)):
    """Create a repair revision from the latest failed validation run."""
    project_key = str(project_id)
    last_run = await db.validation_runs.find_one(
        {"project_id": project_key}, sort=[("created_at", -1)]
    )
    if not last_run:
        raise HTTPException(status_code=400, detail="No validation run found.")
    if last_run["status"] == ValidationStatus.PASSED.value:
        raise HTTPException(status_code=400, detail="Latest artifacts already passed validation.")

    attempts = await db.repair_attempts.count_documents({"project_id": project_key})
    if attempts >= MAX_REPAIR_ATTEMPTS:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum repair attempts ({MAX_REPAIR_ATTEMPTS}) reached. Please adjust requirements manually.",
        )

    failed_generation = await db.artifact_generations.find_one(
        {"id": last_run["generation_id"], "project_id": project_key}
    )
    if not failed_generation:
        raise HTTPException(status_code=404, detail="The failed artifact revision no longer exists.")
    project = await db.projects.find_one({"_id": project_key})
    specification = (project or {}).get("deployment_spec", {}).get("specification", {})
    provider = get_llm_provider()
    model_used = "Deterministic templates"
    try:
        if provider:
            repaired_artifacts = await attempt_repair(
                provider=provider,
                spec=specification,
                failed_artifacts=failed_generation["artifacts"],
                errors=last_run.get("errors", []),
            )
            model_used = provider.name
        else:
            repaired_artifacts = generate_artifacts_deterministically(specification)
    except Exception as exc:
        logger.warning("Model repair unavailable; regenerating local templates: %s", exc)
        repaired_artifacts = generate_artifacts_deterministically(specification)

    generation_id = str(uuid.uuid4())
    generation = {
        "_id": generation_id,
        "id": generation_id,
        "project_id": project_key,
        "model_used": model_used,
        "prompt_version": "v2.0-repair",
        "artifact_version": await _next_version(db, project_key),
        "artifacts": repaired_artifacts,
        "created_at": _now(),
    }
    await db.artifact_generations.insert_one(generation)
    await db.projects.update_one(
        {"_id": project_key},
        {"$set": {"last_deployment": None, "updated_at": _now()}},
    )

    # A repair is only reported as successful after the same deterministic
    # quality gate has inspected its output and the result has been persisted.
    repaired_findings = validate_artifacts(repaired_artifacts, specification)
    repair_validation_id = str(uuid.uuid4())
    await db.validation_runs.insert_one({
        "_id": repair_validation_id,
        "id": repair_validation_id,
        "project_id": project_key,
        "generation_id": generation_id,
        "status": ValidationStatus.PASSED.value if not repaired_findings else ValidationStatus.FAILED.value,
        "stage_failed": "validation" if repaired_findings else None,
        "created_at": _now(),
        "errors": [
            {
                "category": finding.get("category", "validation"),
                "artifact_name": finding.get("artifact_name"),
                "message": finding["message"],
                "severity": finding.get("severity", "error"),
            }
            for finding in repaired_findings
        ],
    })

    repair_id = str(uuid.uuid4())
    await db.repair_attempts.insert_one({
        "_id": repair_id,
        "id": repair_id,
        "project_id": project_key,
        "source_generation_id": last_run["generation_id"],
        "validation_run_id": repair_validation_id,
        "new_generation_id": generation_id,
        "attempt_number": attempts + 1,
        "successful": not repaired_findings,
        "created_at": _now(),
    })
    return _public(generation)


@router.get("/projects/{project_id}/status")
async def get_project_status(project_id: uuid.UUID, db=Depends(get_db)):
    """Return generation history with the latest validation and repair metadata."""
    project_key = str(project_id)
    generations = [
        document async for document in db.artifact_generations.find(
            {"project_id": project_key}
        ).sort("artifact_version", 1)
    ]
    runs_by_generation = {}
    async for run in db.validation_runs.find(
        {"project_id": project_key}
    ).sort("created_at", -1):
        runs_by_generation.setdefault(run["generation_id"], run)

    repairs_by_generation = {}
    async for repair in db.repair_attempts.find({"project_id": project_key}):
        if repair.get("new_generation_id"):
            repairs_by_generation[repair["new_generation_id"]] = repair

    history = []
    for generation in generations:
        run = runs_by_generation.get(generation["id"])
        repair = repairs_by_generation.get(generation["id"])
        history.append({
            "generation_id": generation["id"],
            "version": generation["artifact_version"],
            "model": generation["model_used"],
            "is_repair": repair is not None,
            "repair_attempt_num": repair.get("attempt_number") if repair else None,
            "validation_status": run["status"] if run else "unvalidated",
            "errors": [
                {"message": error["message"], "artifact": error.get("artifact_name")}
                for error in run.get("errors", [])
            ] if run else [],
        })
    return {"history": history}
