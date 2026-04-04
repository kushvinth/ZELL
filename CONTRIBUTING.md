# Contributing to ZELL

Thank you for contributing to ZELL.

ZELL is a self-hosted intelligence and simulation platform. We welcome fixes, features, docs improvements, and operational hardening.

## Ways to contribute

- Report bugs
- Suggest features
- Improve docs and onboarding
- Submit code improvements
- Improve tests and CI reliability

## Before you start

- Search open issues and pull requests to avoid duplicate work.
- For larger features, open an issue first to discuss scope.
- Keep pull requests focused and small when possible.

## Development setup

## Backend

```bash
cd backend
uv sync --all-groups
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Frontend

```bash
cd frontend
npm ci
npm run dev
```

## Quality checks

Run these before opening a pull request.

## Backend checks

```bash
cd backend
uv run ruff check .
uv run ruff format --check .
```

## Frontend checks

```bash
cd frontend
npx --yes oxlint@latest "src/**/*.{ts,tsx}"
npx --yes prettier --check .
npx tsc --noEmit
npm run build
```

## Branch and commit guidance

- Use descriptive branch names: feature/atlas-filters, fix/bootstrap-cache
- Keep commit messages clear and scoped
- Group related changes in a single pull request

## Pull request checklist

- Add a clear title and context
- Link related issues
- Explain what changed and why
- Include screenshots for UI updates
- Confirm local checks pass
- Update docs when behavior changes

## Coding expectations

- Prefer readable, maintainable code over clever one-liners
- Keep API behavior explicit and predictable
- Avoid hidden side effects
- Preserve existing style and project conventions

## Reporting bugs

Please include:

- Environment details
- Steps to reproduce
- Expected result
- Actual result
- Relevant logs or screenshots

## Questions and support

See SUPPORT.md for help and communication paths.
