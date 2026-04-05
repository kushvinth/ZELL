<p align="center">
    <picture>
        <source media="(prefers-color-scheme: light)" srcset="./assets/banner.png">
        <img src="./assets/banner.png" alt="ZELL" width="600">
    </picture>
</p>

<p align="center">
  <strong>SIMULATE. OBSERVE. UNDERSTAND.</strong>
</p>

<p align="center">
  <a href="https://github.com/kushvinth/ZELL/actions/workflows/frontend.yml?branch=main"><img src="https://img.shields.io/github/actions/workflow/status/kushvinth/ZELL/frontend.yml?branch=main&style=for-the-badge" alt="Build status"></a>
  <a href="https://github.com/kushvinth/ZELL/releases"><img src="https://img.shields.io/github/v/release/kushvinth/ZELL?include_prereleases&style=for-the-badge" alt="GitHub release"></a>
  <a href="https://github.com/kushvinth/ZELL/blob/main/LICENSE"><img src="https://img.shields.io/github/license/kushvinth/ZELL?style=for-the-badge" alt="MIT License"></a>
  <a href="https://github.com/kushvinth/ZELL/issues"><img src="https://img.shields.io/github/issues/kushvinth/ZELL?style=for-the-badge" alt="Open Issues"></a>
</p>

**ZELL** is a _self-hosted knowledge intelligence and multi-agent simulation platform_.
It gives teams a command-center experience for running synthetic societies, tracking agent behavior over time, and exploring relationship graphs and search-driven insights, all inside your own infrastructure.

If you want open-control-room energy with full data ownership, this is it.

[Docs](docs/) · [Self-Hosting Guide](docs/SELF_HOSTING.md) · [Quick Start](#quick-start) · [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md)

---

## Why ZELL

- **Self-hosted by design**: keep your data, prompts, and outputs inside your own stack.
- **FastAPI + React**: clean API-first backend, easy to extend and integrate.
- **Stateful agents**: generated personas, evolving memory, and cycle-based decisions.
- **Rich knowledge surfaces**: semantic search, run history, graph relationships, and dashboard endpoints.
- **Local-first LLM support**: Ollama/LocalAI compatible, fully environment-driven configuration.

---

## Core Capabilities

- **[Agent Bootstrap](#how-to-use-zell)**: generate rich personas and seed a synthetic world with a single API call.
- **[Simulation Orchestration](#how-to-use-zell)**: run multi-cycle scenarios with configurable events and time horizons.
- **[Decision Persistence](#how-to-use-zell)**: every agent decision is stored and queryable across simulation runs.
- **[Semantic + Fuzzy Search](#how-to-use-zell)**: hybrid search across all agent responses and run histories.
- **[Graph Relationship Extraction](#how-to-use-zell)**: visualize agent connections in the workbench and atlas views.
- **[API-first Architecture](#api-reference)**: build custom frontends or integrate with your existing tooling.

---

## Quick Start

Runtime: **Docker** (recommended) or **Python 3.11+ / Node 18+**.

Full setup guide: [docs/SELF_HOSTING.md](docs/SELF_HOSTING.md)

### Option 1: Docker Compose (recommended)

```bash
git clone https://github.com/kushvinth/ZELL
cd zell
docker compose up --build
```

Services start at:

- **Frontend**: <http://localhost:3000>
- **Backend API**: <http://localhost:8000>

### Option 2: Local Development

**Backend:**

```bash
cd backend
uv sync --all-groups
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend:**

```bash
cd frontend
npm ci
npm run dev
```

Dev URLs:

- **Frontend**: <http://localhost:5173>
- **Backend API**: <http://localhost:8000>

[Full configuration reference (all keys + examples).](docs/SELF_HOSTING.md)

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=kushvinth/ZELL&type=date&legend=top-left)](https://www.star-history.com/#kushvinth/ZELL&type=date&legend=top-left)

---

## Everything we built so far

### Core platform

- **[FastAPI backend](docs/)** with simulation orchestration, agent runtime, storage engine, and search index.
- **[React + Vite frontend](docs/)**: dashboard, atlas workbench, search UI, and relationship graph explorer.
- **[Agent bootstrap engine](docs/)**: persona generation pipeline seeding synthetic societies at scale.
- **[Session model](docs/)**: stateful agents with evolving memory and per-cycle decision persistence.
- **[Media pipeline](docs/)**: response storage, run history, and temp lifecycle management.

### Knowledge surfaces

- **[Hybrid search](docs/)**: semantic + fuzzy search across all agent responses and run histories.
- **[Graph extraction](docs/)**: relationship inference for atlas and workbench visualization.
- **[Dashboard API](docs/)**: run history, response retrieval, and aggregated analytics endpoints.
- **[Search index](docs/)**: configurable scan depth via `SEMANTIC_SCAN_MAX_RESPONSES`.

### Agents + simulation

- **[Agent personas](docs/)**: bootstrap-generated profiles with role, memory, and decision style.
- **[Simulation cycles](docs/)**: multi-step event injection with configurable year and cycle count.
- **[Run isolation](docs/)**: each simulation run is independently queryable and graph-extractable.
- **[Decision log](docs/)**: full audit trail of every agent response across all cycles.

### Runtime + ops

- **[Docker Compose](docker-compose.yml)**: one-command full-stack startup.
- **[Persistent storage](docs/SELF_HOSTING.md)**: `agents.db` + `agents_data/` volume mounts for prod.
- **[CORS config](docs/)**: environment-driven origin allowlisting.
- **[LLM failover](docs/)**: swap providers and models via env vars with no code changes.
- **[Health endpoints](docs/)**: `/health` and `/api/llm/health` for monitoring integration.

### CI + quality gates

- **[Backend checks](docs/)**: Ruff lint, Ruff format, Python compile validation on every push and PR.
- **[Frontend checks](docs/)**: ESLint, format check, TypeScript type-check, production build.
- **[GitHub Actions](docs/)**: runs on both push and pull requests; keeps the repo merge-ready.

---

## Security model (important)

- **Default:** all data stays local; no telemetry, no external calls except your configured LLM endpoint.
- **CORS:** restrict `CORS_ORIGINS` to your real frontend domain in production.
- **Storage:** `agents.db` and `agents_data/` should be mounted as persistent volumes and excluded from public access.
- **Reverse proxy:** always put the backend behind Nginx / Caddy / Traefik before exposing publicly.
- **LLM traffic:** If using a remote LLM backend, ensure the connection is over a trusted network or VPN.

Details: [Security policy](SECURITY.md) · [Self-hosting guide](docs/SELF_HOSTING.md)

---

## Production notes

- Put the backend behind a reverse proxy (Nginx / Caddy / Traefik).
- Restrict `CORS_ORIGINS` to your real frontend domain only.
- Use persistent Docker volumes for `backend/agents_data` and `backend/agents.db`.
- Pin your LLM model name and set resource limits before running scale tests.
- Configure log shipping and monitoring from day one.

Details: [Self-hosting guide](docs/SELF_HOSTING.md)

---

## Docs

Use these when you're past the quick start and want the deeper reference.

- [Start with the docs index for navigation and "what's where."](docs/)
- [Follow the self-hosting guide for production deployment.](docs/SELF_HOSTING.md)
- [Review the security policy before exposing anything publicly.](SECURITY.md)
- [Read the contribution guide before submitting a PR.](CONTRIBUTING.md)
- [Check the support guide if you're stuck.](SUPPORT.md)

---

## Community and governance

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines and how to submit PRs.
AI/vibe-coded PRs welcome!

- Contribution guide: [CONTRIBUTING.md](CONTRIBUTING.md)
- Code of conduct: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
- Security policy: [SECURITY.md](SECURITY.md)
- Support guide: [SUPPORT.md](SUPPORT.md)
- Funding: [.github/FUNDING.yml](.github/FUNDING.yml)

---

## Project status

Active development. PRs are welcome.

If you are building a private, self-hosted intelligence cockpit for knowledge exploration and agent behavior analysis, ZELL is built for that mission.
