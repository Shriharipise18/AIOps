# ⚡ AI DevOps Assistant

> **Final-Year Project** · Repository-Aware Infrastructure Generation, Automated Validation & Intelligent Deployment

AI DevOps Assistant is a project scaffold for monitoring application services and building toward repository-aware infrastructure generation, validation, and deployment insights.

## 📋 Table of Contents

- [Architecture](#architecture)
- [Folder Structure](#folder-structure)
- [Prerequisites](#prerequisites)
- [Quick Start (Docker — recommended)](#quick-start-docker--recommended)
- [Run on GitHub Codespaces](#run-on-github-codespaces)
- [Local Development (without Docker)](#local-development-without-docker)
- [Environment Variables](#environment-variables)
- [API Reference](#api-reference)
- [Running Tests](#running-tests)
- [Continuous Integration](#continuous-integration)
- [Expected Output](#expected-output)
- [Troubleshooting](#troubleshooting)
- [Level 1 Definition of Done](#level-1-definition-of-done)

---

## Architecture

```text
Browser (React + Vite)
        |
        | Axios HTTP
        v
   FastAPI (Python 3.12)
        |
        +----> MongoDB 7+ (primary document store)
        |
        +----> Redis 7 (cache / queue)

All services are orchestrated by Docker Compose on a shared bridge network.
```

## Folder Structure

```text
ai-devops-assistant/
├── .devcontainer/
│   ├── devcontainer.json
│   └── setup.sh
├── .github/
│   └── workflows/
│       └── ci.yml
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   └── health.py
│   │   │   └── router.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   └── logging.py
│   │   ├── db/
│   │   │   └── database.py
│   │   ├── services/
│   │   │   └── redis_service.py
│   │   └── main.py
│   ├── .env.example
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/api.js
│   │   ├── components/
│   │   │   ├── Header.jsx
│   │   │   ├── ServiceCard.jsx
│   │   │   └── StatusDot.jsx
│   │   ├── hooks/useHealth.js
│   │   ├── pages/Dashboard.jsx
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css
│   ├── .env.example
│   ├── Dockerfile
│   ├── index.html
│   └── vite.config.js
├── infrastructure/
│   └── redis/
│       └── redis.conf
├── tests/
│   └── test_health.py
├── docs/
├── .env.example
├── .gitignore
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

## Prerequisites

| Tool | Version | Installation |
|---|---|---|
| Docker Desktop | 4.x or later | [Download Docker Desktop](https://www.docker.com/products/docker-desktop) |
| Docker Compose | 2.x or later | Included with Docker Desktop |
| Node.js | 20.x or later | [Download Node.js](https://nodejs.org) |
| Python | 3.12 or later | [Download Python](https://www.python.org) |
| Git | Recent version | [Download Git](https://git-scm.com) |

MongoDB and Redis are started by Docker Compose. For local development without Docker, install and run MongoDB and Redis separately.

> **Note:** GitHub only hosts the source code. The application itself runs wherever Docker runs: your own machine, or GitHub Codespaces (see below).

---

## Quick Start (Docker — recommended)

### 1. Clone the repository

```powershell
git clone https://github.com/Shriharipise18/DevAI.git
cd DevAI
```

If you already have the project locally, open a terminal in the project root instead.

### 2. Create environment files

In PowerShell:

```powershell
Copy-Item .env.example .env
Copy-Item backend/.env.example backend/.env
Copy-Item frontend/.env.example frontend/.env
```

If an environment file already exists, review it rather than overwriting your local settings.

### 3. Start the application

Ensure Docker Desktop is running, then run:

```powershell
docker compose up --build
```

### 4. Open the application

- **Frontend dashboard:** http://localhost:5173
- **Backend API:** http://localhost:8000
- **Interactive API docs:** http://localhost:8000/docs
- **Health endpoint:** http://localhost:8000/api/v1/health

To stop the services, press `Ctrl+C`, then run:

```powershell
docker compose down
```

To stop the services and remove the MongoDB data volume as well, run `docker compose down -v`. **This deletes the persisted database data.**

---

## Run on GitHub Codespaces

Use this if you want to run the app from GitHub without installing anything locally.

1. Open the repository on GitHub: https://github.com/Shriharipise18/DevAI
2. Click **Code → Codespaces → Create codespace on main**.
3. Wait for the environment to finish setting up. The `.devcontainer/setup.sh` script creates the `.env` files and sets `ALLOWED_ORIGINS` and `VITE_API_BASE_URL` to the Codespaces URLs automatically.
4. In the Codespaces terminal, run:

   ```bash
   docker compose up --build
   ```

5. Open the **Ports** tab and click the globe icon next to:
   - **5173** — frontend dashboard
   - **8000** — backend API (add `/docs` to the URL for interactive docs)

Ports 8000 and 5173 are set to **public** so the browser can call the backend across Codespaces URLs. Anyone with the link can reach them while the codespace is running, so stop or delete the codespace when you are done.

If the dashboard shows a connection error, check that `frontend/.env` contains the Codespaces URL of port 8000 followed by `/api/v1`, and restart with `docker compose up --build`.

---

## Local Development (without Docker)

For this mode, MongoDB and Redis must already be running locally.

### Backend

From the project root, open a PowerShell terminal:

```powershell
cd backend

python -m venv .venv
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `backend/.env` and make sure the local service addresses are configured:

```dotenv
MONGODB_URL=mongodb://localhost:27017
REDIS_HOST=localhost
REDIS_PORT=6379
```

Start the API:

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

Open a second terminal at the project root:

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

The Vite development server is available at http://localhost:5173.

---

## Environment Variables

### Root `.env`

| Variable | Default | Description |
|---|---|---|
| `MONGODB_DATABASE` | `devops_assistant` | MongoDB database name |

### `backend/.env`

| Variable | Default | Description |
|---|---|---|
| `ENVIRONMENT` | `development` | Runtime environment label |
| `DEBUG` | `true` | Enables debug-level logging |
| `MONGODB_URL` | `mongodb://localhost:27017` | MongoDB connection URI for local development |
| `MONGODB_DATABASE` | `devops_assistant` | MongoDB database name |
| `REDIS_HOST` | `localhost` locally; `redis` in Compose | Redis hostname |
| `REDIS_PORT` | `6379` | Redis port |
| `LLM_PROVIDER` | `groq` | Configured provider: `groq` or `openai` |
| `GROQ_API_KEY` | Empty | Groq API key for AI generation |
| `GROQ_MODEL` | `openai/gpt-oss-120b` | Model identifier used by the configured provider |
| `GROQ_BASE_URL` | `https://api.groq.com/openai/v1` | Groq API endpoint |
| `OPENAI_API_KEY` | Empty | Optional key when using the OpenAI provider |
| `ALLOWED_ORIGINS` | `http://localhost:5173` | Comma-separated allowed browser origins |

### `frontend/.env`

| Variable | Default | Description |
|---|---|---|
| `VITE_API_BASE_URL` | `http://localhost:8000/api/v1` | Backend API base URL |

To configure a Groq key, add it to `backend/.env`:

```dotenv
LLM_PROVIDER=groq
GROQ_API_KEY=your_groq_api_key
```

Keep API keys private. Do not commit `.env` files or place secret keys in frontend code. Restart the backend after changing environment variables.

> **Scope note:** The README describes the intended AI-provider configuration. Confirm that repository code implements the corresponding generation features before relying on them; the Level 1 scaffold focuses on the health dashboard and service connectivity.

---

## API Reference

### `GET /api/v1/health`

Returns the health status of the backend's database and Redis connections.

**Example response:**

```json
{
  "status": "ok",
  "version": "1.0.0",
  "environment": "development",
  "services": {
    "database": {
      "status": "ok",
      "latency_ms": 2.45
    },
    "redis": {
      "status": "ok",
      "latency_ms": 0.83
    }
  }
}
```

The `status` field can be `ok` or `degraded` based on service connectivity. Individual service statuses may be `ok` or `error`. Latency values above are illustrative and will vary by machine.

### `GET /`

Returns a simple API welcome message.

Interactive documentation: http://localhost:8000/docs

---

## Running Tests

From the project root, install the backend dependencies and test tools:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install pytest httpx
cd ..
pytest tests/ -v
```

The tests cover the root endpoint and the health endpoint's response structure. The exact result depends on the current implementation and test environment.

---

## Continuous Integration

Every push to `main` and every pull request triggers the workflow in `.github/workflows/ci.yml`, which runs two jobs on GitHub:

| Job | What it does |
|---|---|
| `backend-tests` | Starts MongoDB 7 and Redis 7 as service containers, installs `backend/requirements.txt`, and runs `pytest tests/ -v` |
| `frontend-build` | Installs frontend dependencies with Node 20 and runs `npm run build` |

View results in the repository's **Actions** tab. A green check on a commit means both jobs passed.

---

## Expected Output

### Docker Compose startup

When the services start correctly, Docker Compose should show logs indicating that MongoDB and Redis are ready and that the FastAPI and Vite development servers have started.

### Health check

Run:

```powershell
Invoke-RestMethod http://localhost:8000/api/v1/health
```

A healthy response reports `"status": "ok"` and shows `"status": "ok"` for both the database and Redis services. If either service cannot be reached, the overall response should report a degraded state.

---

## Troubleshooting

| Problem | Possible cause | Suggested fix |
|---|---|---|
| `port 27017 already in use` | Local MongoDB is already using the port | Stop the local service or change the published port in `docker-compose.yml` |
| `port 6379 already in use` | Local Redis is already using the port | Stop the local service or change the published port |
| Frontend shows a connection error | Backend is not running or not ready | Check `docker compose ps` and backend logs |
| Connection or CORS error in Codespaces | `.env` still points to `localhost`, or port 8000 is private | Re-run `bash .devcontainer/setup.sh`, set port 8000 to public in the Ports tab, restart the stack |
| `ModuleNotFoundError: No module named 'app'` | Backend command started from the wrong directory | Run the local Uvicorn command from `backend/` |
| CORS error in browser | Frontend origin is not in the backend allowlist | Check `ALLOWED_ORIGINS` and restart the backend |
| MongoDB is not connected | MongoDB is stopped or the URI is incorrect | Verify `MONGODB_URL` and container logs |
| Redis is not connected | Redis is stopped or hostname/port is incorrect | Verify `REDIS_HOST`, `REDIS_PORT`, and container logs |
| `Cannot connect to the Docker daemon` | Docker Desktop is not running | Start Docker Desktop and retry |
| Port `8000` or `5173` already in use | Another process occupies the port | Stop that process or update the port mappings and frontend configuration |
| GitHub Actions `backend-tests` fails with `ModuleNotFoundError` | Tests cannot find the `app` package | Confirm `PYTHONPATH: backend` is set in `ci.yml` |

Useful Docker commands:

```powershell
docker compose ps
docker compose logs backend
docker compose logs frontend
docker compose logs mongodb
docker compose logs redis
```

---

## Level 1 Definition of Done

Use this checklist to track completion against the current scaffold:

- [x] Project folder structure created
- [x] FastAPI application and health endpoint configured
- [x] React + Vite dashboard scaffolded
- [x] Dashboard displays backend, database, Redis, and overall application status
- [x] MongoDB connection configured
- [x] Redis connection configured
- [x] Dockerfiles created for backend and frontend
- [x] Docker Compose configured for the services
- [x] `.env.example`, `.gitignore`, and `README.md` included
- [x] Frontend-to-backend communication configured with Axios
- [x] Basic automated tests included
- [x] GitHub Actions workflow for tests and frontend build
- [x] GitHub Codespaces configuration

### Planned future capabilities

These are project goals, not claims that they are already implemented:

- [ ] Analyze a source-code repository
- [ ] Generate Dockerfiles and deployment configuration
- [ ] Validate generated infrastructure files
- [ ] Review deployment risks and provide actionable insights
- [ ] Add AI-assisted generation and repair workflows

---

**Project:** AI DevOps Assistant  
**GitHub:** [Shriharipise18/DevAI](https://github.com/Shriharipise18/DevAI)
