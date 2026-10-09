"""
Tests for security features (URL validation, ZIP path traversal prevention).
"""
import pytest
import zipfile
from pathlib import Path
from app.services.security import validate_github_url, safe_extract_zip, SecurityError


def test_validate_github_url_valid():
    owner, repo, branch = validate_github_url("https://github.com/Shriharipise18/Academic-Engagement-Portal")
    assert owner == "Shriharipise18"
    assert repo == "Academic-Engagement-Portal"
    assert branch == "main"

    owner, repo, branch = validate_github_url("https://github.com/facebook/react/tree/18.2.0")
    assert owner == "facebook"
    assert repo == "react"
    assert branch == "18.2.0"


def test_validate_github_url_invalid():
    with pytest.raises(SecurityError):
        validate_github_url("http://gitlab.com/test/repo")
    
    with pytest.raises(SecurityError):
        validate_github_url("https://github.com/test") # missing repo
        
    with pytest.raises(SecurityError):
        validate_github_url("https://github.com/owner/repo-with-injection;rm-rf")


def test_safe_extract_zip_path_traversal(tmp_path):
    zip_path = tmp_path / "malicious.zip"
    extract_to = tmp_path / "extracted"
    extract_to.mkdir()

    # Create a malicious zip file
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("../outside.txt", "hacked")

    with pytest.raises(SecurityError, match="Path traversal attempt detected"):
        safe_extract_zip(zip_path, extract_to)
