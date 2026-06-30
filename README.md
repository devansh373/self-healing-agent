# Self-Healing Infrastructure Agent — Phase 1

An autonomous AI coding agent system designed to detect, analyze, and repair broken Terraform deployment pipelines in real-time without human intervention. This repository represents **Phase 1 ("Local Foundation / Walking Skeleton")**.

## Overview

When an infrastructure deployment fails due to syntax or configuration faults in Terraform code, the orchestrator intercepts the failure, delegates root-cause analysis to Google's **Gemini 2.5 Flash** LLM, validates the AI's proposed HCL fix inside an isolated local sandbox, commits the outcome to PostgreSQL, and broadcasts live state updates to a Next.js telemetry dashboard via WebSockets.

## Repository Structure

```
self-healing-agent-python/
├── backend/            # FastAPI orchestrator, Async SQLAlchemy 2.0, Alembic, pytest suite
├── frontend/           # Next.js 16 (App Router), TypeScript, real-time WebSocket dashboard
├── .github/workflows/  # GitHub Actions CI running containerized Postgres & full verification
└── phase-1-spec-self-healing-agent.md # Full technical specification & architecture roadmap
```

## Quickstart Guide

### 1. Start Database & Backend Orchestrator
Ensure Docker, Python 3.12+, and Terraform CLI (v1.7+) are installed locally.

```bash
cd backend
cp .env.example .env
# Edit .env to add your GEMINI_API_KEY and verify TERRAFORM_BINARY_PATH

# Start Postgres container
docker compose up -d

# Create virtual environment & install dependencies
python -m venv .venv
.venv\Scripts\activate  # On Windows PowerShell
pip install -e ".[dev]"

# Run database migrations
alembic upgrade head

# Start API server on http://localhost:8000
uvicorn app.main:app --reload
```

### 2. Start Frontend Dashboard
Open a new terminal window:

```bash
cd frontend
npm install
npm run dev
```
Open **[http://localhost:3000](http://localhost:3000)** in your browser. Click **"Run Demo Pipeline"** to watch the self-healing cycle execute live!

## Component Documentation

For detailed architecture, configuration, testing, and linting instructions, refer to:
- [Backend README](backend/README.md)
- [Frontend README](frontend/README.md)
- [Phase 1 Specification](phase-1-spec-self-healing-agent.md)

## Verification & CI

To run automated verification across the workspace:
```bash
# Backend unit tests & linting
cd backend
ruff check .
pytest -v

# Frontend TypeScript check & build
cd ../frontend
npm run build
```
