"""
Tests for the deterministic repository analyzer.
"""
import pytest
from pathlib import Path
import json

from app.services.analyzer import RepoAnalyzer

@pytest.fixture
def temp_workspace(tmp_path):
    return tmp_path


def test_analyze_nodejs_express(temp_workspace):
    (temp_workspace / "package.json").write_text(json.dumps({
        "name": "test-app",
        "main": "server.js",
        "scripts": {
            "start": "node server.js",
            "build": "tsc"
        },
        "dependencies": {
            "express": "^4.17.1"
        }
    }))

    analyzer = RepoAnalyzer(temp_workspace)
    profile = analyzer.analyze()

    assert profile["language"] == "Node.js"
    assert profile["framework"] == "Express"
    assert profile["package_manager"] == "npm"
    assert profile["entrypoint"] == "server.js"
    assert profile["port"] == 3000
    assert profile["start_command"] == "npm start"
    assert profile["build_command"] == "npm run build"
    assert "express" in profile["dependencies"]


def test_analyze_python_fastapi(temp_workspace):
    (temp_workspace / "requirements.txt").write_text("fastapi==0.115.0\nuvicorn\n")
    (temp_workspace / "main.py").write_text("print('hello')")

    analyzer = RepoAnalyzer(temp_workspace)
    profile = analyzer.analyze()

    assert profile["language"] == "Python"
    assert profile["framework"] == "FastAPI"
    assert profile["package_manager"] == "pip"
    assert profile["port"] == 8000
    assert profile["start_command"] == "uvicorn main:app"


def test_detect_services_from_env(temp_workspace):
    (temp_workspace / "requirements.txt").write_text("django\n")
    (temp_workspace / ".env.example").write_text(
        "POSTGRES_USER=dev\n"
        "REDIS_URL=redis://localhost\n"
        "RABBITMQ_HOST=localhost\n"
    )

    analyzer = RepoAnalyzer(temp_workspace)
    profile = analyzer.analyze()

    assert profile["language"] == "Python"
    assert profile["framework"] == "Django"
    assert profile["database"] == "PostgreSQL"
    assert profile["redis"] is True
    assert profile["queue"] == "RabbitMQ"
