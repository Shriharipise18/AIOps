"""Repository ingestion routes with project profiles stored in MongoDB."""
from datetime import datetime, timezone
from pathlib import Path
import uuid

import aiofiles
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.core.logging import get_logger
from app.db.database import get_db
from app.models.project import ProjectStatus, SourceType
from app.schemas.project import AnalyzeGithubRequest, ProjectResponse
from app.services.analyzer import RepoAnalyzer
from app.services.github_service import download_github_repo
from app.services.security import safe_extract_zip, MAX_ZIP_SIZE_BYTES, SecurityError
from app.services.workspace import temporary_workspace, create_workspace, destroy_workspace

logger = get_logger(__name__)
router = APIRouter(tags=["Repositories"])


def _now():
    return datetime.now(timezone.utc)


async def _run_analysis(repo_root: Path, project_id: str, db):
    """Analyze source files and persist the resulting profile in the project document."""
    await db.projects.update_one(
        {"_id": project_id},
        {"$set": {"status": ProjectStatus.ANALYZING.value, "updated_at": _now()}},
    )
    try:
        profile_data = RepoAnalyzer(repo_root).analyze()
        await db.projects.update_one(
            {"_id": project_id},
            {"$set": {
                "profile": profile_data,
                "status": ProjectStatus.COMPLETED.value,
                "error_message": None,
                "updated_at": _now(),
            }},
        )
    except Exception as exc:
        logger.error("Analysis failed for project %s: %s", project_id, exc, exc_info=True)
        await db.projects.update_one(
            {"_id": project_id},
            {"$set": {
                "status": ProjectStatus.FAILED.value,
                "error_message": str(exc),
                "updated_at": _now(),
            }},
        )


def _new_project(name: str, source_type: SourceType, source_url: str | None = None):
    project_id = str(uuid.uuid4())
    now = _now()
    return {
        "_id": project_id,
        "id": project_id,
        "name": name,
        "source_type": source_type.value,
        "source_url": source_url,
        "status": ProjectStatus.PENDING.value,
        "error_message": None,
        "created_at": now,
        "updated_at": now,
        "profile": None,
        "requirements": None,
        "deployment_spec": None,
        "artifact_version_seq": 0,
    }


async def _public_project(db, project_id: str):
    project = await db.projects.find_one({"_id": project_id})
    if project:
        project.pop("_id", None)
    return project


@router.post("/repositories/analyze/github", response_model=ProjectResponse)
async def analyze_github(request: AnalyzeGithubRequest, db=Depends(get_db)):
    """Download and analyze a GitHub repository."""
    project = _new_project("GitHub Repo", SourceType.GITHUB_URL, request.url)
    await db.projects.insert_one(project)
    project_id = project["id"]

    try:
        async with temporary_workspace(uuid.UUID(project_id)) as workspace:
            repo_root, owner, repo_name = await download_github_repo(request.url, workspace)
            await db.projects.update_one(
                {"_id": project_id},
                {"$set": {"name": f"{owner}/{repo_name}", "updated_at": _now()}},
            )
            # Repository analysis is bounded static inspection; long-running work
            # can be moved to a queue independently of the Mongo persistence layer.
            await _run_analysis(repo_root, project_id, db)
    except (ValueError, SecurityError) as exc:
        await db.projects.update_one(
            {"_id": project_id},
            {"$set": {"status": ProjectStatus.FAILED.value, "error_message": str(exc), "updated_at": _now()}},
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        await db.projects.update_one(
            {"_id": project_id},
            {"$set": {"status": ProjectStatus.FAILED.value, "error_message": "Internal error during download/analysis", "updated_at": _now()}},
        )
        logger.error("Error analyzing GitHub repository: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal error during repository analysis") from exc

    return await _public_project(db, project_id)


@router.post("/repositories/analyze/zip", response_model=ProjectResponse)
async def analyze_zip(file: UploadFile = File(...), db=Depends(get_db)):
    """Safely unpack and analyze an uploaded ZIP archive."""
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Must be a .zip file")

    project = _new_project(file.filename, SourceType.ZIP_UPLOAD)
    await db.projects.insert_one(project)
    project_id = project["id"]
    workspace = create_workspace(uuid.UUID(project_id))
    zip_path = workspace / "upload.zip"

    try:
        downloaded = 0
        async with aiofiles.open(zip_path, "wb") as output_file:
            while chunk := await file.read(65_536):
                downloaded += len(chunk)
                if downloaded > MAX_ZIP_SIZE_BYTES:
                    raise SecurityError(f"File exceeds maximum size of {MAX_ZIP_SIZE_BYTES // 1024 // 1024}MB")
                await output_file.write(chunk)

        extract_dir = workspace / "extracted"
        extract_dir.mkdir(exist_ok=True)
        repo_root = safe_extract_zip(zip_path, extract_dir)
        zip_path.unlink()
        await _run_analysis(repo_root, project_id, db)
    except SecurityError as exc:
        await db.projects.update_one(
            {"_id": project_id},
            {"$set": {"status": ProjectStatus.FAILED.value, "error_message": str(exc), "updated_at": _now()}},
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        await db.projects.update_one(
            {"_id": project_id},
            {"$set": {"status": ProjectStatus.FAILED.value, "error_message": "Internal error during upload/analysis", "updated_at": _now()}},
        )
        logger.error("Error analyzing ZIP repository: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal error during archive analysis") from exc
    finally:
        await file.close()
        destroy_workspace(uuid.UUID(project_id))

    return await _public_project(db, project_id)
