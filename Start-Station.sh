#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
printf '%s\n' 'RESIDUAL / COMMAND STATION' 'Starting your local workspace…'
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  mkdir -p projects
  docker compose up --build -d
  if command -v open >/dev/null 2>&1; then open 'http://localhost:8765';
  elif command -v xdg-open >/dev/null 2>&1; then xdg-open 'http://localhost:8765' >/dev/null 2>&1 || true; fi
  printf '%s\n' 'Open http://localhost:8765' 'Stop with: docker compose stop' 'Model weights download inside Model Workshop.'
else
  if ! command -v python3 >/dev/null 2>&1; then
    printf '%s\n' 'Install Docker Desktop for the complete runtime, or Python 3.11+ and Git for native mode.' 'See START-HERE.md.'
    exit 1
  fi
  python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else "Python 3.11+ is required")'
  if ! command -v git >/dev/null 2>&1; then printf '%s\n' 'Git is required. Install Git or use Docker Desktop.'; exit 1; fi
  exec python3 -m residual.station.server --open
fi
