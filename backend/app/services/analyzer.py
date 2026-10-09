"""
Deterministic repository analysis engine.

Uses presence of files (package.json, requirements.txt, etc.) and their
contents to infer the language, framework, dependencies, and expected commands.
Does NOT use LLMs or execute untrusted code.
"""
import json
import os
import re
import toml
from pathlib import Path

from app.core.logging import get_logger
from app.services.security import is_safe_to_read

logger = get_logger(__name__)


class RepoAnalyzer:
    """Analyzes a repository directory deterministically."""

    def __init__(self, repo_root: Path):
        self.root = repo_root.resolve()
        self.profile = {
            "language": None,
            "framework": None,
            "package_manager": None,
            "entrypoint": None,
            "port": None,
            "database": None,
            "redis": False,
            "queue": None,
            "build_command": None,
            "start_command": None,
            "dependencies": {},
            "env_vars": [],
            "raw_files": [],
        }

    def analyze(self) -> dict:
        """Run all analysis steps and return the profile dict."""
        self._scan_files()
        self._detect_nodejs()
        if not self.profile["language"]:
            self._detect_python()
        if not self.profile["language"]:
            self._detect_java()

        self._detect_services_from_env()
        self._detect_port_from_source()
        return self.profile

    def _scan_files(self):
        """Collect a bounded source inventory without walking vendor/build output."""
        skipped_directories = {
            ".git", "node_modules", "vendor", ".venv", "venv", "__pycache__",
            "dist", "build", ".next", "coverage", ".idea", ".vscode",
        }
        for current, directories, filenames in os.walk(self.root):
            directories[:] = [
                name for name in directories
                if name not in skipped_directories and not name.startswith(".git")
            ]
            for filename in filenames:
                if filename == ".env":
                    continue
                path = Path(current) / filename
                self.profile["raw_files"].append(path.relative_to(self.root).as_posix())
                if len(self.profile["raw_files"]) >= 500:
                    break
            if len(self.profile["raw_files"]) >= 500:
                break
        self.profile["raw_files"].sort()

    def _detect_port_from_source(self):
        """Find a configured listening port from safe text files as a fallback."""
        if self.profile["port"]:
            return

        port_pattern = re.compile(
            r"(?:PORT|port)\s*(?:=|:|\|\|)\s*[\"']?(\d{2,5})\b"
        )
        source_extensions = {".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".env", ".yaml", ".yml"}
        for relative in self.profile["raw_files"]:
            path = self.root / relative
            if path.suffix.lower() not in source_extensions and path.name != ".env.example":
                continue
            content = self._read_file_safe(relative)
            if not content:
                continue
            match = port_pattern.search(content)
            if match:
                port = int(match.group(1))
                if 1 <= port <= 65535:
                    self.profile["port"] = port
                    return

    def _read_file_safe(self, filename: str) -> str | None:
        """Read a file if it exists and is safe."""
        path = self.root / filename
        if path.is_file() and is_safe_to_read(path):
            try:
                return path.read_text(encoding="utf-8")
            except Exception as e:
                logger.warning("Failed to read %s: %s", filename, e)
        return None

    def _detect_nodejs(self):
        """Check for package.json."""
        pkg_content = self._read_file_safe("package.json")
        if not pkg_content:
            return

        try:
            pkg = json.loads(pkg_content)
        except json.JSONDecodeError:
            logger.warning("package.json is invalid JSON")
            return

        self.profile["language"] = "Node.js"
        self.profile["package_manager"] = "npm"

        if (self.root / "yarn.lock").exists():
            self.profile["package_manager"] = "yarn"
        elif (self.root / "pnpm-lock.yaml").exists():
            self.profile["package_manager"] = "pnpm"

        deps = pkg.get("dependencies", {})
        dev_deps = pkg.get("devDependencies", {})
        all_deps = {**deps, **dev_deps}
        self.profile["dependencies"] = all_deps

        # Framework detection
        if "express" in deps:
            self.profile["framework"] = "Express"
            self.profile["port"] = 3000
        elif "react" in deps or "next" in deps:
            self.profile["framework"] = "React"
            self.profile["port"] = 3000
            if "next" in deps:
                self.profile["framework"] = "Next.js"
        
        # Commands
        scripts = pkg.get("scripts", {})
        if "build" in scripts:
            self.profile["build_command"] = f"{self.profile['package_manager']} run build"
        if "start" in scripts:
            self.profile["start_command"] = f"{self.profile['package_manager']} start"
        elif "dev" in scripts:
            self.profile["start_command"] = f"{self.profile['package_manager']} run dev"

        # Entrypoint
        self.profile["entrypoint"] = pkg.get("main")

    def _detect_python(self):
        """Check for requirements.txt or pyproject.toml."""
        req_content = self._read_file_safe("requirements.txt")
        pyproject_content = self._read_file_safe("pyproject.toml")

        if not req_content and not pyproject_content:
            return

        self.profile["language"] = "Python"
        self.profile["package_manager"] = "pip"
        
        deps = []
        if req_content:
            deps = [line.split("==")[0].strip() for line in req_content.splitlines() if line.strip() and not line.startswith("#")]
        
        if pyproject_content:
            try:
                pyproject = toml.loads(pyproject_content)
                if "tool" in pyproject and "poetry" in pyproject["tool"]:
                    self.profile["package_manager"] = "poetry"
                    deps.extend(pyproject["tool"]["poetry"].get("dependencies", {}).keys())
            except Exception as e:
                logger.warning("Failed to parse pyproject.toml: %s", e)

        self.profile["dependencies"] = {d: "*" for d in deps}

        deps_lower = [d.lower() for d in deps]
        if "flask" in deps_lower:
            self.profile["framework"] = "Flask"
            self.profile["port"] = 5000
            self.profile["start_command"] = "flask run"
        elif "fastapi" in deps_lower:
            self.profile["framework"] = "FastAPI"
            self.profile["port"] = 8000
            self.profile["start_command"] = "uvicorn main:app"
        elif "django" in deps_lower:
            self.profile["framework"] = "Django"
            self.profile["port"] = 8000
            self.profile["start_command"] = "python manage.py runserver"

    def _detect_java(self):
        """Check for pom.xml."""
        pom_content = self._read_file_safe("pom.xml")
        if not pom_content:
            return

        self.profile["language"] = "Java"
        self.profile["package_manager"] = "maven"
        self.profile["build_command"] = "mvn clean install"

        if "spring-boot" in pom_content:
            self.profile["framework"] = "Spring Boot"
            self.profile["port"] = 8080
            self.profile["start_command"] = "mvn spring-boot:run"

    def _detect_services_from_env(self):
        """Look at .env.example or .env for clues about databases/redis."""
        env_content = self._read_file_safe(".env.example") or self._read_file_safe(".env")
        if not env_content:
            return

        for line in env_content.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            
            key = line.split("=")[0].strip()
            self.profile["env_vars"].append(key)

            key_lower = key.lower()
            if "postgres" in key_lower:
                self.profile["database"] = "PostgreSQL"
            elif "mysql" in key_lower:
                self.profile["database"] = "MySQL"
            elif "mongo" in key_lower:
                self.profile["database"] = "MongoDB"
            elif "redis" in key_lower:
                self.profile["redis"] = True
            elif "rabbitmq" in key_lower or "amqp" in key_lower:
                self.profile["queue"] = "RabbitMQ"
