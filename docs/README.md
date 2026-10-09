# AI-Based DevOps Assistant

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
