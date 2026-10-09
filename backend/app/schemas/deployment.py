"""
Pydantic schemas for Level 3 — AI Deployment Planner APIs.
"""
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Dict, Any, List, Literal
import uuid
from datetime import datetime

class ProjectRequirementsCreate(BaseModel):
    deployment_platform: Literal["Kubernetes", "Docker Compose"]
    cloud_provider: Literal["AWS", "GCP", "Azure", "None (Local)"]
    replicas: int = Field(default=1, ge=1, le=100)
    cpu_limit: Optional[str] = Field(default=None, pattern=r"^[0-9]+(?:\.[0-9]+)?m?$", max_length=24)
    memory_limit: Optional[str] = Field(default=None, pattern=r"^[0-9]+(?:\.[0-9]+)?(?:Ki|Mi|Gi|Ti|K|M|G|T)?$", max_length=24)
    autoscaling: bool = False
    is_public: bool = True
    container_port: Optional[int] = Field(default=None, ge=1, le=65535)
    include_database: bool = False
    include_redis: bool = False

class ProjectRequirementsResponse(ProjectRequirementsCreate):
    id: uuid.UUID
    project_id: uuid.UUID
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class ProjectDeploymentSpecResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    specification: dict
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class ArtifactGenerationResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    model_used: str
    prompt_version: str
    artifact_version: int
    artifacts: dict
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())
