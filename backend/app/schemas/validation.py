"""
Pydantic schemas for Level 4 — Validation and Repair APIs.
"""
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
import uuid
from datetime import datetime

from app.models.validation import ValidationStatus


class ValidationErrorResponse(BaseModel):
    category: str
    artifact_name: Optional[str]
    message: str
    severity: str
    
    model_config = ConfigDict(from_attributes=True)


class ValidationRunResponse(BaseModel):
    id: uuid.UUID
    generation_id: uuid.UUID
    status: ValidationStatus
    stage_failed: Optional[str]
    created_at: datetime
    errors: List[ValidationErrorResponse] = []
    
    model_config = ConfigDict(from_attributes=True)


class RepairAttemptResponse(BaseModel):
    id: uuid.UUID
    source_generation_id: uuid.UUID
    validation_run_id: uuid.UUID
    new_generation_id: Optional[uuid.UUID]
    attempt_number: int
    successful: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
