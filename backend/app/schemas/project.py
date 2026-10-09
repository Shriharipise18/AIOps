"""
Pydantic schemas for Level 2 APIs.
"""
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional, Dict, Any, List
import uuid
from datetime import datetime

from app.models.project import SourceType, ProjectStatus


class ProjectProfileBase(BaseModel):
    language: Optional[str] = None
    framework: Optional[str] = None
    package_manager: Optional[str] = None
    entrypoint: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    redis: bool = False
    queue: Optional[str] = None
    build_command: Optional[str] = None
    start_command: Optional[str] = None
    dependencies: Dict[str, Any] = Field(default_factory=dict)
    env_vars: List[str] = Field(default_factory=list)
    raw_files: List[str] = Field(default_factory=list)


class ProjectResponse(BaseModel):
    id: uuid.UUID
    name: str
    source_type: SourceType
    source_url: Optional[str] = None
    status: ProjectStatus
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    profile: Optional[ProjectProfileBase] = None
    requirements: Optional[Dict[str, Any]] = None
    last_deployment: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class AnalyzeGithubRequest(BaseModel):
    url: str


class ProjectUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Project name cannot be empty")
        return value
