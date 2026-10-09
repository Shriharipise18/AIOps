"""
GitHub repository downloader.

Downloads a repository archive via the GitHub public ZIP endpoint.
No GitHub API token is required for public repositories.

Security:
  - URL is validated before any HTTP request is made.
  - Archive is saved to an isolated workspace before extraction.
  - Extraction is delegated to the security module (path traversal checks).
"""
from pathlib import Path

import httpx

from app.core.logging import get_logger
from app.services.security import validate_github_url, safe_extract_zip, MAX_ZIP_SIZE_BYTES

logger = get_logger(__name__)

# Try these branches in order when the user doesn't specify one
_DEFAULT_BRANCHES = ("main", "master", "develop")
_DOWNLOAD_TIMEOUT_S = 60  # seconds


async def download_github_repo(url: str, workspace: Path) -> tuple[Path, str, str]:
    """
    Download a GitHub repository archive and extract it to *workspace*.

    Steps:
      1. Validate the GitHub URL.
      2. Try downloading the ZIP archive (main → master → develop).
      3. Save to workspace/repo.zip.
      4. Extract securely.

    Returns: (repo_root_path, owner, repo_name)
    Raises:  ValueError / httpx errors on failure.
    """
    owner, repo, preferred_branch = validate_github_url(url)

    branches_to_try = (
        [preferred_branch]
        if preferred_branch not in _DEFAULT_BRANCHES
        else list(_DEFAULT_BRANCHES)
    )

    zip_path = workspace / "repo.zip"
    last_error: Exception | None = None

    async with httpx.AsyncClient(follow_redirects=True, timeout=_DOWNLOAD_TIMEOUT_S) as client:
        for branch in branches_to_try:
            archive_url = (
                f"https://github.com/{owner}/{repo}"
                f"/archive/refs/heads/{branch}.zip"
            )
            logger.info("Trying archive URL: %s", archive_url)

            try:
                async with client.stream("GET", archive_url) as response:
                    if response.status_code == 404:
                        logger.debug("Branch %r not found, trying next…", branch)
                        continue
                    response.raise_for_status()

                    # Enforce size limit during streaming
                    downloaded = 0
                    with open(zip_path, "wb") as f:
                        async for chunk in response.aiter_bytes(chunk_size=65_536):
                            downloaded += len(chunk)
                            if downloaded > MAX_ZIP_SIZE_BYTES:
                                raise ValueError(
                                    f"Repository archive exceeds size limit of "
                                    f"{MAX_ZIP_SIZE_BYTES // 1024 // 1024} MB."
                                )
                            f.write(chunk)

                logger.info(
                    "Downloaded %s/%s@%s (%.1f MB)",
                    owner, repo, branch, downloaded / 1024 / 1024,
                )
                break  # success

            except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                last_error = exc
                logger.warning("Download failed for branch %r: %s", branch, exc)
        else:
            # Exhausted all branches
            raise ValueError(
                f"Could not download {owner}/{repo}. "
                f"Tried branches: {branches_to_try}. "
                f"Last error: {last_error}"
            )

    # Extract the downloaded archive
    extract_dir = workspace / "extracted"
    extract_dir.mkdir(exist_ok=True)
    repo_root = safe_extract_zip(zip_path, extract_dir)

    # Clean up the raw ZIP to save space
    zip_path.unlink(missing_ok=True)

    return repo_root, owner, repo
