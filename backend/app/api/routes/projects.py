"""MongoDB-backed project library and CRUD routes."""
import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from app.db.database import get_db
from app.schemas.project import ProjectResponse, ProjectUpdate
from app.services.workspace import destroy_workspace

router = APIRouter(tags=["Projects"])


def _public_project(document: dict | None) -> dict | None:
    if document is None:
        return None
    document.pop("_id", None)
    return document


@router.get("/projects", response_model=list[ProjectResponse])
async def list_projects(
    q: str | None = Query(default=None, max_length=120),
    status: str | None = Query(default=None, pattern="^(pending|analyzing|completed|failed)$"),
    source_type: str | None = Query(default=None, pattern="^(github_url|zip_upload)$"),
    limit: int = Query(default=100, ge=1, le=500),
    skip: int = Query(default=0, ge=0),
    db=Depends(get_db),
):
    """Search and filter recent saved projects."""
    filters = []
    if status:
        filters.append({"status": status})
    if source_type:
        filters.append({"source_type": source_type})
    if q and q.strip():
        expression = re.escape(q.strip())
        filters.append({"$or": [
            {"name": {"$regex": expression, "$options": "i"}},
            {"source_url": {"$regex": expression, "$options": "i"}},
        ]})
    query = {"$and": filters} if filters else {}
    cursor = db.projects.find(query).sort("created_at", -1).skip(skip).limit(limit)
    return [_public_project(document) async for document in cursor]


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: uuid.UUID, db=Depends(get_db)):
    """Return one project and its embedded repository profile."""
    project = await db.projects.find_one({"_id": str(project_id)})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return _public_project(project)


@router.patch("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: uuid.UUID, update: ProjectUpdate, db=Depends(get_db)):
    """Rename a saved project."""
    key = str(project_id)
    result = await db.projects.update_one(
        {"_id": key},
        {"$set": {"name": update.name, "updated_at": datetime.now(timezone.utc)}},
    )
    if not result.matched_count:
        raise HTTPException(status_code=404, detail="Project not found")
    return _public_project(await db.projects.find_one({"_id": key}))


@router.delete("/projects/{project_id}", status_code=204, response_class=Response)
async def delete_project(project_id: uuid.UUID, db=Depends(get_db)) -> Response:
    """Delete a project and all workflow records that belong to it."""
    key = str(project_id)
    result = await db.projects.delete_one({"_id": key})
    if not result.deleted_count:
        raise HTTPException(status_code=404, detail="Project not found")

    await db.artifact_generations.delete_many({"project_id": key})
    await db.validation_runs.delete_many({"project_id": key})
    await db.repair_attempts.delete_many({"project_id": key})
    await db.deployments.delete_many({"project_id": key})
    destroy_workspace(project_id)
    return Response(status_code=204)
