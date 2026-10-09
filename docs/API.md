# API Documentation

## Core Endpoints
- `GET /api/v1/health`: System health and latency.
- `GET /api/v1/projects?q=...&status=...&source_type=...`: Search and filter saved projects.
- `GET /api/v1/projects/{id}`: Reopen a saved project, including its requirements and latest deployment record.
- `PATCH /api/v1/projects/{id}`: Rename a project.
- `DELETE /api/v1/projects/{id}`: Delete a project and its artifacts, validations, repairs, deployments, and workspace.
- `POST /api/v1/repositories/analyze/github`: Analyzes a GitHub repository.
- `POST /api/v1/repositories/analyze/zip`: Analyzes an uploaded ZIP archive.
- `POST /api/v1/projects/{id}/requirements`: Submits deployment constraints and triggers AI generation.
- `GET /api/v1/projects/{id}/artifacts`: Retrieves generated artifacts.
- `GET /api/v1/projects/{id}/artifacts/{generation_id}/download`: Downloads an artifact revision as a ZIP archive.
- `POST /api/v1/projects/{id}/validate`: Runs the deterministic validation loop.
- `POST /api/v1/projects/{id}/repair`: Creates and validates a repaired artifact revision.
- `GET /api/v1/projects/{id}/analysis`: Retrieves Security, Cost, and Performance insights.
- `GET /api/v1/projects/{id}/readiness`: Computes the readiness score for deployment.
- `POST /api/v1/projects/{id}/deploy`: Triggers Kubernetes deployment.

## Local workflow

1. Analyze a public GitHub repository or upload a ZIP containing the source tree. Source code is inspected as text and is not executed by analysis.
2. Reopen saved work from the Projects library. Requirements, generated revisions, validation runs, and repairs are stored in MongoDB.
3. Generate infrastructure. The deterministic local generator works without an LLM key; an OpenAI key enables optional model generation.
4. Inspect individual files or download one revision as a ZIP. Run validation and, when needed, repair; repaired revisions are checked automatically.
5. Review built-in security heuristics, performance findings, the AWS cost approximation, and readiness score.
6. Kubernetes apply/status require `kubectl` on the backend host and a reachable current context. The API checks the context again at apply time and reports the live pod/service state. A cloud cluster also needs an application image it can pull. Docker Compose selection produces a bundle for local use; the UI does not claim it was deployed.

The app is intended for a single local operator; it has no account or tenant boundary. Do not expose this development server to an untrusted network. Redis is optional and not needed for the synchronous local workflow. GCP/Azure cost pricing and external CVE scanners are reported as unavailable unless integrations are configured.
