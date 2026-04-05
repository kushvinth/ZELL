# Self-Hosting ZELL

This guide covers a production-oriented deployment pattern for ZELL.

## What ZELL Is

ZELL is a self-hosted knowledge intelligence and multi-agent simulation platform.
You run the stack on your infrastructure, control your model endpoints, and keep your data in your own environment.

## Deployment Modes

## Docker Compose (recommended)

From repository root:

```bash
docker compose up --build -d
```

Services:

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`

Both services are attached to an explicit Docker bridge network (`zell-network`) for inter-service communication.

Stop stack:

```bash
docker compose down
```

The stack uses persistent Docker volumes for:

- persona markdown cache (`agents_data`)
- SQLite database (`agents.db` via `ZELL_DB_PATH`)

## One-line installer

If Docker and Git are already installed:

```bash
curl -fsSL https://zell.kushvinth.com/install.sh | bash
```

Installer script in repo: `scripts/install.sh`

Install page HTML: `docs/one-line-install.html`

## Local split services (developer mode)

Backend:

```bash
cd backend
uv sync --all-groups
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```bash
cd frontend
npm ci
npm run dev
```

## Required Runtime Inputs

Set these in your deployment environment:

- `LLM_PROVIDER`
- `LLM_BASE_URL`
- `LLM_MODEL`
- `LLM_TIMEOUT`
- `LLM_MAX_TOKENS`
- `LLM_TEMPERATURE`
- `LLM_TOP_P`
- `CORS_ORIGINS`

Optional tuning:

- `BOOTSTRAP_PROFILE_COUNT`
- `POST_BOOTSTRAP_PROFILE_COUNT`
- `BOOTSTRAP_AGENT_LIMIT`
- `SEMANTIC_SCAN_MAX_RESPONSES`

## Security Checklist

- Put backend behind TLS via a reverse proxy or load balancer
- Restrict `CORS_ORIGINS` to trusted domains
- Avoid exposing internal LLM endpoints publicly
- Run with least-privilege container/user permissions
- Scan dependencies regularly

## Persistence and Data

Current backend data paths include:

- `backend/agents.db` (or `ZELL_DB_PATH`)
- `backend/agents_data/` (or `ZELL_AGENTS_DATA_DIR`)

For production, mount persistent volumes for both.

## Health and Smoke Tests

Check service status:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/llm/health
```

Bootstrap world data:

```bash
curl -X POST http://localhost:8000/api/bootstrap \
  -H "Content-Type: application/json" \
  -d '{"count": 1200, "with_agents": true}'
```

Start a simulation:

```bash
curl -X POST http://localhost:8000/api/simulation/start \
  -H "Content-Type: application/json" \
  -d '{"event": "Regional climate shock", "cycles": 2, "year": 2026}'
```

List runs:

```bash
curl http://localhost:8000/api/dashboard/runs
```

## Scaling Notes

- Horizontal API scale should be paired with shared/persistent storage
- For larger workloads, move SQLite to a network database
- Keep LLM latency under control with model sizing and queueing
- Rate-limit expensive generation endpoints in public environments

## Observability

Recommended additions:

- Reverse-proxy access logs
- Structured backend logs
- Metrics collection (CPU, memory, request latency)
- Uptime checks for `/health` and key API routes

## CI/CD

Repository workflows run checks on push and pull request for both backend and frontend quality gates.

See:

- `.github/workflows/backend.yml`
- `.github/workflows/frontend.yml`
