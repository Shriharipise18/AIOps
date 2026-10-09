"""Validation status values persisted in MongoDB workflow documents."""
import enum


class ValidationStatus(str, enum.Enum):
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
