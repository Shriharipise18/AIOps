"""Deployment planning and artifact generation backed by MongoDB."""
from datetime import datetime, timezone
from io import BytesIO
from pathlib import PurePosixPath
import uuid
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pymongo import ReturnDocument

from app.core.logging import get_logger
from app.db.database import get_db
from app.schemas.deployment import ProjectRequirementsCreate, ArtifactGenerationResponse
from app.services.llm.factory import get_llm_provider
from app.services.planner import generate_deployment_spec, generate_artifacts_via_llm
from app.services.template_generator import generate_artifacts_deterministically

logger = get_logger(__name__)
router = APIRouter(tags=["Deployment"])


def _now():
    return datetime.now(timezone.utc)


def _public_generation(document: dict) -> dict:
    document.pop("_id", None)
    return document


@router.post("/projects/{project_id}/requirements", response_model=ArtifactGenerationResponse)
async def create_deployment_plan(project_id: uuid.UUID, req_in: ProjectRequirementsCreate, db=Depends(get_db)):
    """Save requirements, derive a deployment spec, and create artifacts."""
    project_key = str(project_id)
    project = await db.projects.find_one({"_id": project_key})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not project.get("profile"):
        raise HTTPException(status_code=400, detail="Project profile not found. Analysis incomplete.")

    requirements = req_in.model_dump()
    profile = {**project["profile"], "project_id": project_key}
    specification = generate_deployment_spec(profile, requirements)
    now = _now()
    await db.projects.update_one(
        {"_id": project_key},
        {"$set": {
            "requirements": {**requirements, "created_at": now},
            "deployment_spec": {"specification": specification, "created_at": now},
            "last_deployment": None,
            "updated_at": now,
        }},
    )

    artifacts = generate_artifacts_deterministically(specification)
    model_used = "Deterministic templates"
    provider = get_llm_provider()
    if provider:
        try:
            model_artifacts = await generate_artifacts_via_llm(provider, specification)
            artifacts.update(model_artifacts)
            model_used = provider.name
        except Exception as exc:
            logger.warning("LLM generation unavailable; using deterministic templates: %s", exc)

    counter = await db.projects.find_one_and_update(
        {"_id": project_key},
        {"$inc": {"artifact_version_seq": 1}},
        return_document=ReturnDocument.AFTER,
    )
    version = counter["artifact_version_seq"]
    generation_id = str(uuid.uuid4())
    generation = {
        "_id": generation_id,
        "id": generation_id,
        "project_id": project_key,
        "model_used": model_used,
        "prompt_version": "v1.0",
        "artifact_version": version,
        "artifacts": artifacts,
        "created_at": _now(),
    }
    await db.artifact_generations.insert_one(generation)
    return _public_generation(generation)


@router.get("/projects/{project_id}/artifacts", response_model=list[ArtifactGenerationResponse])
async def get_project_artifacts(project_id: uuid.UUID, db=Depends(get_db)):
    """List the project's artifact revisions, newest first."""
    cursor = db.artifact_generations.find({"project_id": str(project_id)}).sort("artifact_version", -1)
    return [_public_generation(document) async for document in cursor]


@router.get("/projects/{project_id}/artifacts/{generation_id}/download")
async def download_artifact_bundle(
    project_id: uuid.UUID,
    generation_id: uuid.UUID,
    db=Depends(get_db),
):
    """Download one immutable artifact revision as a ZIP archive."""
    generation = await db.artifact_generations.find_one({
        "_id": str(generation_id),
        "project_id": str(project_id),
    })
    if not generation:
        raise HTTPException(status_code=404, detail="Artifact revision not found")

    buffer = BytesIO()
    try:
        with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
            for name, content in generation.get("artifacts", {}).items():
                safe_name = PurePosixPath(str(name).replace("\\", "/"))
                if (
                    safe_name.is_absolute()
                    or not safe_name.parts
                    or any(part in {"", ".", ".."} or ":" in part or "\x00" in part for part in safe_name.parts)
                ):
                    raise HTTPException(status_code=400, detail="An artifact has an unsafe file path")
                archive.writestr(safe_name.as_posix(), str(content))
    except (OSError, TypeError) as exc:
        raise HTTPException(status_code=500, detail="Could not package this artifact revision") from exc

    filename = f"devops-artifacts-v{generation['artifact_version']}.zip"
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
