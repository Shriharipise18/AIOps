"""Security, cost, and performance analysis over MongoDB artifacts."""
import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.db.database import get_db
from app.services.analysis.cost import analyze_cost
from app.services.analysis.performance import analyze_performance
from app.services.analysis.security import analyze_security

router = APIRouter(tags=["Analysis"])


@router.get("/projects/{project_id}/analysis")
async def get_project_analysis(project_id: uuid.UUID, db=Depends(get_db)):
    """Analyze the newest generated artifact bundle and saved deployment spec."""
    project_key = str(project_id)
    generation = await db.artifact_generations.find_one(
        {"project_id": project_key}, sort=[("artifact_version", -1)]
    )
    if not generation:
        raise HTTPException(status_code=404, detail="No artifacts generated yet. Cannot run analysis.")

    project = await db.projects.find_one({"_id": project_key})
    specification = (project or {}).get("deployment_spec", {}).get("specification", {})
    return {
        "security": analyze_security(generation["artifacts"]),
        "cost": analyze_cost(specification),
        "performance": analyze_performance(generation["artifacts"], specification),
    }
