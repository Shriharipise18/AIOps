"""
Security module for repository analysis.

All repository inputs are UNTRUSTED. This module enforces:
  - Path traversal prevention (ZIP extraction)
  - File count and size limits
  - GitHub URL validation (allowlist)
  - No code execution at any point
"""
import os
import re
import zipfile
from pathlib import Path
from urllib.parse import urlparse

from app.core.logging import get_logger

logger = get_logger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────
MAX_ZIP_SIZE_BYTES   = 100 * 1024 * 1024   # 100 MB upload limit
MAX_UNZIPPED_BYTES   = 500 * 1024 * 1024   # 500 MB extracted limit
MAX_FILE_COUNT       = 10_000              # max files inside ZIP
MAX_PATH_DEPTH       = 20                  # max nested directories
ALLOWED_GITHUB_HOST  = "github.com"

# Extensions we NEVER read content from (binary, compiled, etc.)
BINARY_EXTENSIONS = frozenset({
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp", ".bmp",
    ".pdf", ".zip", ".tar", ".gz", ".rar", ".7z",
    ".exe", ".dll", ".so", ".dylib", ".bin",
    ".class", ".jar", ".war", ".ear",
    ".pyc", ".pyo", ".pyd",
    ".node", ".wasm",
    ".mp3", ".mp4", ".mov", ".avi", ".mkv",
    ".ttf", ".woff", ".woff2", ".eot",
    ".DS_Store", ".lock",  # content not useful
})

# Dangerous path components
DANGEROUS_PATTERNS = re.compile(
    r"(\.\./|\.\.\\|^/|^\\|[<>:\"|?*\x00-\x1f])",
    re.IGNORECASE,
)


# ── GitHub URL Validation ─────────────────────────────────────────────────

class SecurityError(ValueError):
    """Raised when a security constraint is violated."""


def validate_github_url(url: str) -> tuple[str, str, str]:
    """
    Validate a GitHub repository URL and extract owner, repo, and branch.

    Accepted formats:
      https://github.com/{owner}/{repo}
      https://github.com/{owner}/{repo}.git
      https://github.com/{owner}/{repo}/tree/{branch}

    Returns: (owner, repo, branch)
    Raises:  SecurityError on invalid input.
    """
    url = url.strip()
    parsed = urlparse(url)

    if parsed.scheme not in ("https", "http"):
        raise SecurityError(f"URL scheme must be https, got: {parsed.scheme!r}")

    if parsed.hostname != ALLOWED_GITHUB_HOST:
        raise SecurityError(
            f"Only {ALLOWED_GITHUB_HOST} URLs are accepted, got: {parsed.hostname!r}"
        )

    # Strip .git suffix and leading slash
    path = parsed.path.rstrip("/").removesuffix(".git")
    parts = [p for p in path.split("/") if p]

    if len(parts) < 2:
        raise SecurityError(
            "URL must be in the form https://github.com/{owner}/{repo}"
        )

    owner = parts[0]
    repo  = parts[1]
    branch = "main"  # default; downloader will try master as fallback

    # Validate owner/repo names: only alphanumeric, hyphens, underscores, dots
    name_re = re.compile(r"^[a-zA-Z0-9._-]+$")
    if not name_re.match(owner):
        raise SecurityError(f"Invalid owner name: {owner!r}")
    if not name_re.match(repo):
        raise SecurityError(f"Invalid repo name: {repo!r}")

    # Extract explicit branch from /tree/{branch}
    if len(parts) >= 4 and parts[2] == "tree":
        branch = parts[3]

    logger.info("Validated GitHub URL: owner=%s repo=%s branch=%s", owner, repo, branch)
    return owner, repo, branch


# ── ZIP Extraction ────────────────────────────────────────────────────────

def safe_extract_zip(zip_path: Path, extract_to: Path) -> Path:
    """
    Securely extract a ZIP archive, preventing path traversal and resource
    exhaustion attacks.

    Returns the root directory of the extracted content.
    Raises: SecurityError on any violation.
    """
    if not zipfile.is_zipfile(zip_path):
        raise SecurityError("Uploaded file is not a valid ZIP archive.")

    with zipfile.ZipFile(zip_path, "r") as zf:
        members = zf.infolist()

        # 1. File count limit
        if len(members) > MAX_FILE_COUNT:
            raise SecurityError(
                f"ZIP contains {len(members)} files; maximum allowed is {MAX_FILE_COUNT}."
            )

        # 2. Total uncompressed size limit (zip bomb check)
        total_size = sum(m.file_size for m in members)
        if total_size > MAX_UNZIPPED_BYTES:
            raise SecurityError(
                f"ZIP uncompressed content is {total_size / 1024 / 1024:.1f} MB; "
                f"maximum allowed is {MAX_UNZIPPED_BYTES / 1024 / 1024:.0f} MB."
            )

        # 3. Path traversal + dangerous name check
        extract_to_resolved = extract_to.resolve()
        for member in members:
            member_path = extract_to_resolved / member.filename
            try:
                member_path.resolve().relative_to(extract_to_resolved)
            except ValueError:
                raise SecurityError(
                    f"Path traversal attempt detected: {member.filename!r}"
                )

            if DANGEROUS_PATTERNS.search(member.filename):
                raise SecurityError(
                    f"Dangerous filename detected: {member.filename!r}"
                )

            # Depth check
            depth = len(Path(member.filename).parts)
            if depth > MAX_PATH_DEPTH:
                raise SecurityError(
                    f"Path depth {depth} exceeds limit {MAX_PATH_DEPTH}: {member.filename!r}"
                )

        # All checks passed — extract
        zf.extractall(extract_to_resolved)
        logger.info(
            "ZIP extracted securely: %d files, %.1f MB uncompressed",
            len(members), total_size / 1024 / 1024,
        )

    # Find the actual root: GitHub ZIPs wrap everything in a {repo}-{sha}/ subfolder
    children = list(extract_to.iterdir())
    if len(children) == 1 and children[0].is_dir():
        return children[0]
    return extract_to


def is_safe_to_read(file_path: Path) -> bool:
    """Return True if the file content is safe and useful to read as text."""
    suffix = file_path.suffix.lower()
    if suffix in BINARY_EXTENSIONS:
        return False
    # Skip hidden dot-directories (e.g. .git)
    for part in file_path.parts:
        if part.startswith(".git"):
            return False
    # Skip very large files (> 1 MB of source)
    try:
        return file_path.stat().st_size <= 1_048_576
    except OSError:
        return False
