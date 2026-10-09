# ⚡ AI DevOps Assistant

> **Final-Year Project** · Repository-Aware Infrastructure Generation, Automated Validation & Intelligent Deployment

---

## 📋 Table of Contents

- [Architecture](#architecture)
- [Folder Structure](#folder-structure)
- [Prerequisites](#prerequisites)
- [Quick Start (Docker — recommended)](#quick-start-docker--recommended)
- [Local Development (without Docker)](#local-development-without-docker)
- [Environment Variables](#environment-variables)
- [API Reference](#api-reference)
- [Running Tests](#running-tests)
- [Expected Output](#expected-output)
- [Troubleshooting](#troubleshooting)
- [Level 1 Definition of Done](#level-1-definition-of-done)

---

## Architecture

```
Browser (React + Vite)
       │  Axios HTTP
       ▼
  FastAPI (Python 3.12)
       │
       ├──▶ MongoDB 8       (primary document store)
       └──▶ Redis 7         (cache / queue)

All services orchestrated by Docker Compose on a shared bridge network.
```

---

## Folder Structure

```
ai-devops-assistant/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   └── health.py        ← GET /api/v1/health
│   │   │   └── router.py
│   │   ├── core/
│   │   │   ├── config.py            ← Pydantic Settings
│   │   │   └── logging.py
│   │   ├── db/
│   │   │   └── database.py          ← Async PyMongo client
│   │   ├── services/
│   │   │   └── redis_service.py     ← Async Redis client
│   │   └── main.py                  ← FastAPI entry point
│   ├── .env.example
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── api/api.js               ← Axios client
│   │   ├── components/
│   │   │   ├── Header.jsx
│   │   │   ├── ServiceCard.jsx
│   │   │   └── StatusDot.jsx
│   │   ├── hooks/useHealth.js       ← Polling hook
│   │   ├── pages/Dashboard.jsx      ← Main dashboard
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css
│   ├── .env.example
│   ├── Dockerfile
│   ├── index.html
│   ├── postcss.config.js
│   ├── tailwind.config.js
│   └── vite.config.js
│
├── infrastructure/
│   └── redis/redis.conf
│
├── tests/
│   └── test_health.py
│
├── docs/
├── .env.example
├── .gitignore
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

---

## Prerequisites

| Tool           | Version  | Install                          |
|----------------|----------|----------------------------------|
| MongoDB        | ≥ 7.x    | Local service or Docker Compose              |
| Docker Desktop | ≥ 4.x    | https://www.docker.com/products/docker-desktop |
| Docker Compose | ≥ 2.x    | bundled with Docker Desktop      |
| Node.js        | ≥ 20.x   | https://nodejs.org               |
| Python         | ≥ 3.12   | https://www.python.org           |
| Git            | any      | https://git-scm.com              |

---

## Quick Start (Docker — recommended)

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd ai-devops-assistant

# 2. Copy environment files
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

# 3. Install frontend dependencies (needed for Docker volume mount)
cd frontend && npm install && cd ..

# 4. Build and start all services
docker compose up --build

# 5. Open in browser
#   Frontend:  http://localhost:5173
#   Backend:   http://localhost:8000
#   API Docs:  http://localhost:8000/docs
```

---

## Local Development (without Docker)

### Backend

```bash
cd backend

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Set environment (point to your local MongoDB/Redis)
cp .env.example .env
# Edit backend/.env: set MONGODB_URL=mongodb://localhost:27017

# Run development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Set environment
cp .env.example .env

# Run dev server
npm run dev
```

---

## Environment Variables

### Root `.env` (docker-compose)

| Variable            | Default             | Description               |
|---------------------|---------------------|---------------------------|
| `MONGODB_DATABASE`  | `devops_assistant`  | MongoDB database name     |

### `backend/.env`

| Variable            | Default                       | Description                       |
|---------------------|-------------------------------|-----------------------------------|
| `ENVIRONMENT`       | `development`                 | Runtime environment label         |
| `DEBUG`             | `true`                        | Enable verbose logging            |
| `MONGODB_URL`        | `mongodb://localhost:27017`   | MongoDB URI (Docker uses service) |
| `MONGODB_DATABASE`  | `devops_assistant`            | MongoDB database name             |
| `REDIS_HOST`        | `redis`                       | Redis host (Docker service name)  |
| `REDIS_PORT`        | `6379`                        | Redis port                        |
| `LLM_PROVIDER`      | `groq`                        | Selects `groq` or `openai` for artifact generation and repair |
| `GROQ_API_KEY`      | —                             | Groq API key; required for AI generation |
| `GROQ_MODEL`        | `openai/gpt-oss-120b`         | Groq model used for artifact generation and repair |
| `GROQ_BASE_URL`     | `https://api.groq.com/openai/v1` | Groq's OpenAI-compatible endpoint |
| `OPENAI_API_KEY`    | —                             | Optional key when `LLM_PROVIDER=openai` |

To enable Groq, add `GROQ_API_KEY=...` to `backend/.env` and restart the backend. The key stays on the server and is never sent to the browser. Without a key, generation and repair use local deterministic templates. The health endpoint reports key configuration without making a remote API call.

### `frontend/.env`

| Variable              | Default                        | Description              |
|-----------------------|--------------------------------|--------------------------|
| `VITE_API_BASE_URL`   | `http://localhost:8000/api/v1` | Backend API base URL     |

---

## API Reference

### `GET /api/v1/health`

Returns the health status of all services.

**Response 200:**
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

**Status values:** `ok` | `degraded` | `error`

Interactive docs: http://localhost:8000/docs

---

## Running Tests

```bash
# From the project root

# 1. Create and activate a virtual environment (if not done)
cd backend
python -m venv .venv
.venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt
pip install pytest pytest-asyncio httpx

# 3. Run tests
cd ..
pytest tests/ -v
```

**Expected output:**
```
tests/test_health.py::TestHealthEndpoint::test_health_returns_200          PASSED
tests/test_health.py::TestHealthEndpoint::test_health_ok_when_all_services_up PASSED
tests/test_health.py::TestHealthEndpoint::test_health_degraded_when_db_down PASSED
tests/test_health.py::TestHealthEndpoint::test_health_degraded_when_redis_down PASSED
tests/test_health.py::TestHealthEndpoint::test_health_response_has_version  PASSED
tests/test_health.py::TestHealthEndpoint::test_health_latency_present       PASSED
tests/test_health.py::TestRootEndpoint::test_root_returns_200               PASSED
tests/test_health.py::TestRootEndpoint::test_root_contains_message          PASSED
============================== 8 passed in X.XXs ==============================
```

---

## Expected Output

### Docker Compose startup

```
devops_db       | database system is ready to accept connections
devops_redis    | Ready to accept connections
devops_backend  | INFO | app.main | === AI DevOps Assistant v1.0.0 starting up ===
devops_backend  | INFO | app.db.database | Database tables initialised
devops_backend  | INFO | app.main | Redis connection ready
devops_backend  | INFO | app.main | === Startup complete — environment: development ===
devops_backend  | INFO | uvicorn | Application startup complete.
devops_frontend | VITE v6.x  ready in Xms
devops_frontend | ➜  Local:   http://localhost:5173/
```

### Health check response

```bash
curl http://localhost:8000/api/v1/health
```
```json
{
  "status": "ok",
  "version": "1.0.0",
  "environment": "development",
  "services": {
    "database": { "status": "ok", "latency_ms": 2.1 },
    "redis":    { "status": "ok", "latency_ms": 0.9 }
  }
}
```

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `port 5432 already in use` | Local Postgres running | Stop it or change port in `docker-compose.yml` |
| `port 6379 already in use` | Local Redis running | Stop it or change port |
| Frontend shows "Connection Error" | Backend not started yet | Wait for `service_healthy` or run `docker compose up` again |
| `ModuleNotFoundError: No module named 'app'` | Wrong working directory for pytest | Run `pytest` from project root (pyproject.toml sets pythonpath) |
| `CORS error` in browser | `ALLOWED_ORIGINS` missing the frontend URL | Add your URL to `backend/.env` `ALLOWED_ORIGINS` |
| MongoDB not connected | MongoDB service is stopped or URI is wrong | Check `MONGODB_URL` and backend logs |
| `Cannot connect to the Docker daemon` | Docker Desktop not running | Start Docker Desktop |

---

## Level 1 Definition of Done

- [x] Project folder structure created
- [x] FastAPI configured with lifespan, CORS, request-logging middleware
- [x] `GET /api/v1/health` returns `{ status, version, environment, services }`
- [x] React + Vite + Tailwind CSS dashboard scaffolded
- [x] Dashboard displays: AI DevOps Assistant, Backend, Database, Redis status
- [x] MongoDB configured with async PyMongo and application-created indexes
- [x] Redis configured with custom `redis.conf`
- [x] Dockerfiles created for backend and frontend (multi-stage)
- [x] `docker-compose.yml` with health checks and proper `depends_on`
- [x] `.env.example`, `.gitignore`, `README.md` present
- [x] Health checks on all four Docker services
- [x] Structured logging with request timing middleware
- [x] Axios-based frontend ↔ backend communication
- [x] Automated tests with mocked dependencies
- [x] All services start cleanly with `docker compose up --build`

---

> **Next:** Say `LEVEL 1 COMPLETE` to proceed to Level 2.
#   A I O p s  
 