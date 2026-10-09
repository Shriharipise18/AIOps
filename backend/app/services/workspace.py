"""
Isolated workspace manager.

Each repository analysis gets its own UUID-namespaced temp directory.
Workspaces are automatically cleaned up after analysis (success or failure).
"""
import shutil
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

def _workspace_base() -> Path:
    base = Path(getattr(settings, "WORKSPACE_DIR", "/tmp/devops_workspaces"))
    base.mkdir(parents=True, exist_ok=True)
    return base


def create_workspace(project_id: uuid.UUID) -> Path:
    """
    Create an isolated directory for a single project analysis.
    Returns the workspace path.
    """
    ws = _workspace_base() / str(project_id)
    ws.mkdir(parents=True, exist_ok=True)
    logger.debug("Workspace created: %s", ws)
    return ws


def destroy_workspace(project_id: uuid.UUID) -> None:
    """Remove the workspace directory and all its contents."""
    ws = _workspace_base() / str(project_id)
    if ws.exists():
        shutil.rmtree(ws, ignore_errors=True)
        logger.debug("Workspace destroyed: %s", ws)


@asynccontextmanager
async def temporary_workspace(project_id: uuid.UUID):
    """
    Async context manager: creates a workspace before the block and
    unconditionally destroys it after (even on exception).

    Usage:
        async with temporary_workspace(project_id) as ws_path:
            # do work in ws_path
    """
    ws = create_workspace(project_id)
    try:
        yield ws
    finally:
        destroy_workspace(project_id)
