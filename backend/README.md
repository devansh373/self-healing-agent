# Self-Healing Infrastructure Agent — Backend

This is the backend for the Self-Healing Infrastructure Agent. It is built using FastAPI, SQLAlchemy 2.0 (async), and Postgres. It coordinates triggering deployments, simulating local Terraform validation, delegating to the Gemini API for code-fixes, and broadcasting results over WebSockets.

## Prerequisites

Before setting up the backend, ensure you have the following installed locally:
- Python 3.12+
- Docker & Docker Compose
- [Terraform CLI](https://developer.hashicorp.com/terraform/downloads) (v1.7+) installed directly on your host machine.
- A free Gemini API Key from [Google AI Studio](https://aistudio.google.com/).

## Local Setup

**1. Environment Setup**  
Copy the example environment variables file and fill it out:
```bash
cp .env.example .env
```
Inside `.env`, make sure to set your `GEMINI_API_KEY` and ensure `TERRAFORM_BINARY_PATH` points to your local Terraform installation.

**2. Start the Database**  
Start the PostgreSQL 16 database using Docker Compose:
```bash
docker compose up -d
```
*(Or use poe: `poe db-up`)*

**3. Set up the Python Virtual Environment**  
Create a virtual environment and install the required dependencies:
```bash
python -m venv .venv

# Activate the virtual environment
# On Linux/macOS:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate

# Install dependencies in editable mode
pip install -e ".[dev]"
```

**4. Run Database Migrations**  
Create the required tables (`deployments`, `healing_attempts`) via Alembic:
```bash
alembic upgrade head
```
*(Or use poe: `poe migrate`)*

## Running the Server

Start the development server with auto-reload enabled:
```bash
uvicorn app.main:app --reload
```
*(Or use poe: `poe dev`)*

The server will be available at `http://localhost:8000`. 
Check the health status by visiting: `http://localhost:8000/api/health`

## Linting and Testing

To ensure code quality and correctness, use `pytest` and `ruff`:

**Run tests:**
```bash
pytest -v
```
*(Or use poe: `poe test`)*

**Run linting and formatting:**
```bash
ruff check .
ruff format .
```
*(Or use poe: `poe lint` and `poe format`)*

## Security Note for Phase 1
Phase 1 intentionally omits authentication, authorization, and cloud deployments. The LLM runs in an isolated temporary sandbox (`tempfile.TemporaryDirectory`) exclusively to simulate Terraform validation locally.
