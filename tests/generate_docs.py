import os

docs_dir = "c:/Users/piseg/Desktop/DeVoPs/ai-devops-assistant/docs"
os.makedirs(docs_dir, exist_ok=True)

files = {
    "README.md": """# AI-Based DevOps Assistant

Repository-Aware Infrastructure Generation, Automated Validation and Intelligent Deployment.

## Overview
This final-year project is a comprehensive end-to-end system that automates the DevOps lifecycle. It analyzes a given source repository, determines requirements, generates Docker and Kubernetes artifacts using LLMs, deterministically validates and repairs them, and evaluates them for security, cost, and performance before deploying to a cluster.

## Features
- **Level 1**: Full-stack setup (FastAPI, React, MongoDB, Redis).
- **Level 2**: Intelligent Repository Analysis (detects frameworks, ports, dependencies).
- **Level 3**: AI Deployment Planner (converts profile to Kubernetes/Docker specs).
- **Level 4**: Validation & AI Self-Correction (closed-loop testing of generated artifacts).
- **Level 5**: Deployment Analysis (Security, Cost, Performance).
- **Level 6**: Deployment Engine (Kubernetes rollout with Readiness Score).
- **Level 7**: Professional React Dashboard.
- **Level 8**: Experimental Evaluation Framework.

## How to Run
1. Start backend: `cd backend && uvicorn app.main:app --reload`
2. Start frontend: `cd frontend && npm run dev`
""",

    "ARCHITECTURE.md": """# System Architecture

```mermaid
graph TD
    User([User / GitHub URL]) --> UI[React Dashboard]
    UI --> Backend[FastAPI Backend]
    
    subgraph AI DevOps Assistant
        Backend --> Analyzer[Repository Analyzer]
        Analyzer --> Spec[Deterministic Spec Generator]
        Spec --> LLM[LLM Generator]
        LLM --> Validator[Validation Engine]
        Validator -- Fails --> Repair[AI Repair Loop]
        Validator -- Passes --> Analysis[Security/Cost/Performance Engine]
        Analysis --> Readiness[Readiness Scorer]
    end
    
    Readiness --> Deploy[Kubernetes Deployment Engine]
    Deploy --> Cluster[(K8s Cluster)]
```
""",

    "API.md": """# API Documentation

## Core Endpoints
- `GET /api/v1/health`: System health and latency.
- `POST /api/v1/repositories/analyze/github`: Analyzes a GitHub repository.
- `POST /api/v1/projects/{id}/requirements`: Submits deployment constraints and triggers AI generation.
- `GET /api/v1/projects/{id}/artifacts`: Retrieves generated artifacts.
- `POST /api/v1/projects/{id}/validate`: Runs the deterministic validation loop.
- `GET /api/v1/projects/{id}/analysis`: Retrieves Security, Cost, and Performance insights.
- `GET /api/v1/projects/{id}/readiness`: Computes the readiness score for deployment.
- `POST /api/v1/projects/{id}/deploy`: Triggers Kubernetes deployment.
""",

    "DB_SCHEMA.md": """# MongoDB Document Model

The `projects` collection embeds profile, requirements, and deployment spec.
Versioned artifacts, validation runs (with embedded errors), and repair history
are stored in `artifact_generations`, `validation_runs`, and `repair_attempts`.

```mermaid
flowchart LR
    P[projects] -->|project_id| A[artifact_generations]
    P -->|project_id| V[validation_runs]
    A -->|generation_id| V
    P -->|project_id| R[repair_attempts]
    V -->|validation_run_id| R
```
""",

    "VIVA_PREP.md": """# Viva Questions & Answers

1. **Why use deterministic validation instead of just asking the LLM if it's correct?**
   *Answer:* LLMs are prone to hallucinations. They might confidently generate invalid YAML or expose sensitive ports. Deterministic validation (like running `docker build` or `trivy`) ensures actual correctness, which is critical for infrastructure.

2. **How does the AI Self-Correction loop work?**
   *Answer:* If validation fails, the exact error logs (e.g., mismatched ports) are fed back to the LLM as a repair prompt. The LLM generates a fix, and the validation runs again. This repeats up to 3 times to prevent infinite loops.

3. **How is the Readiness Score calculated?**
   *Answer:* It's a formula-based score starting at 100. It deducts points for validation failures, critical security findings, and suboptimal performance configs. It is entirely deterministic, avoiding LLM bias.
""",

    "PAPER_OUTLINE.md": """# Research Paper Outline

**Title:** Repository-Aware Infrastructure Generation, Automated Validation and Intelligent Deployment Using Large Language Models

1. **Abstract**: Summary of the automated DevOps pipeline and its ability to self-correct infrastructure code.
2. **Introduction**: The complexity of modern DevOps and the rise of LLMs.
3. **Related Work**: Current IaC generators and their lack of validation.
4. **Methodology**:
   - Repository Analysis Heuristics
   - Closed-Loop LLM Generation
   - Deterministic Validation and Security/Cost Engines
5. **Experimental Evaluation**: Comparison of Manual, Single-Shot LLM, and the Proposed System across Node, Python, Java, and MERN stacks.
6. **Results**: Data showing reduced time and higher reliability compared to single-shot LLMs.
7. **Conclusion & Future Work**.
""",

    "FINAL_REPORT.md": """# Final Project Report Material

This folder contains all necessary materials for the final project report.

- **Objective**: Automate the DevOps lifecycle safely.
- **System Flow**: Repo -> AI Generation -> Deterministic Validation -> Analysis -> K8s Deployment.
- **Tech Stack**: React, FastAPI, MongoDB, Redis, Docker, Kubernetes.
- **Evaluation**: Please refer to `EVALUATION.md` for the quantitative analysis.
"""
}

for filename, content in files.items():
    with open(os.path.join(docs_dir, filename), "w", encoding="utf-8") as f:
        f.write(content)

print("Deliverables generated successfully.")
