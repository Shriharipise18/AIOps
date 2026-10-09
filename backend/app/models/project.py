"""String enums shared by repository API schemas and MongoDB documents."""
import enum


class SourceType(str, enum.Enum):
    GITHUB_URL = "github_url"
    ZIP_UPLOAD = "zip_upload"


class ProjectStatus(str, enum.Enum):
    PENDING = "pending"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"
