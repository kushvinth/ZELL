#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${ZELL_REPO_URL:-https://github.com/kushvinth/ZELL.git}"
INSTALL_DIR="${ZELL_INSTALL_DIR:-$HOME/zell}"

if ! command -v git >/dev/null 2>&1; then
  echo "Git is required. Install Git first, then rerun this command."
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required. Install Docker Desktop/Engine first, then rerun this command."
  exit 1
fi

if docker compose version >/dev/null 2>&1; then
  COMPOSE=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE=(docker-compose)
else
  echo "Docker Compose is required. Install the Docker Compose plugin and retry."
  exit 1
fi

if [ -d "$INSTALL_DIR/.git" ]; then
  echo "Updating existing ZELL installation at $INSTALL_DIR"
  git -C "$INSTALL_DIR" pull --ff-only
else
  echo "Cloning ZELL into $INSTALL_DIR"
  git clone "$REPO_URL" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"

echo "Starting ZELL with Docker Compose..."
"${COMPOSE[@]}" up --build -d

echo

echo "ZELL is starting up."
echo "Frontend: http://localhost:3000"
echo "Backend API: http://localhost:8000"
echo

echo "To view logs: ${COMPOSE[*]} logs -f"
echo "To stop: ${COMPOSE[*]} down"
