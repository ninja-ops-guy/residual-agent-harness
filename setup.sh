#!/usr/bin/env bash
# RESIDUAL setup script
# - Installs residual-agent-harness into a dedicated venv
# - Exports the venv bin onto PATH
# - Optionally creates a `residual` macro that auto-serves on 0.0.0.0:8765
# - Prints a tooltip and clickable link fallback
set -euo pipefail

REPO_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${RESIDUAL_VENV:-/tmp/residual-venv}"
DATA_DIR="${RESIDUAL_DATA:-/tmp/residual-station-data}"
HOST="${RESIDUAL_HOST:-0.0.0.0}"
PORT="${RESIDUAL_PORT:-8765}"
SETTINGS_FILE="${RESIDUAL_SETTINGS:-$HOME/.residual-settings}"

# ── helpers ──────────────────────────────────────────────────────────────────

info()  { printf '\033[1;34m[residual]\033[0m %s\n' "$*"; }
warn()  { printf '\033[1;33m[residual]\033[0m %s\n' "$*"; }
error() { printf '\033[1;31m[residual]\033[0m %s\n' "$*" >&2; }

# Persist a key=value setting
set_setting() {
  local key="$1" val="$2"
  touch "$SETTINGS_FILE"
  # Remove existing key, then append
  grep -v "^${key}=" "$SETTINGS_FILE" > "$SETTINGS_FILE.tmp" 2>/dev/null || true
  mv "$SETTINGS_FILE.tmp" "$SETTINGS_FILE"
  echo "${key}=${val}" >> "$SETTINGS_FILE"
}

# Read a setting (returns empty if absent)
get_setting() {
  local key="$1"
  [ -f "$SETTINGS_FILE" ] && grep "^${key}=" "$SETTINGS_FILE" | tail -1 | cut -d= -f2- || true
}

# ── python check ─────────────────────────────────────────────────────────────

PY=""
for candidate in python3.13 python3.12 python3.11 python3; do
  if command -v "$candidate" >/dev/null 2>&1; then
    ver=$("$candidate" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    major=${ver%%.*}
    minor=${ver##*.}
    if [ "$major" -gt 3 ] || { [ "$major" -eq 3 ] && [ "$minor" -ge 11 ]; }; then
      PY="$candidate"
      break
    fi
  fi
done

if [ -z "$PY" ]; then
  error "Python 3.11+ is required. Install it and re-run."
  exit 1
fi

info "Using $PY ($("$PY" --version 2>&1))"

# ── venv + install ───────────────────────────────────────────────────────────

if [ ! -d "$VENV_DIR" ]; then
  info "Creating venv at $VENV_DIR"
  "$PY" -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

pip install --upgrade pip -q

if pip show residual-agent-harness >/dev/null 2>&1; then
  info "residual-agent-harness already installed — skipping"
else
  info "Installing residual-agent-harness (editable)…"
  pip install -e "$REPO_DIR"
fi

# ── PATH export ─────────────────────────────────────────────────────────────

SNIPPET="# residual-agent-harness
export PATH=\"$VENV_DIR/bin:\$PATH\""

# Detect current shell rc file
if [ -n "${ZSH_VERSION:-}" ]; then
  RC_FILE="$HOME/.zshrc"
elif [ -n "${BASH_VERSION:-}" ]; then
  RC_FILE="$HOME/.bashrc"
else
  RC_FILE="$HOME/.profile"
fi

if ! grep -qF "residual-agent-harness" "$RC_FILE" 2>/dev/null; then
  info "Adding PATH export to $RC_FILE"
  printf '\n%s\n' "$SNIPPET" >> "$RC_FILE"
else
  info "PATH export already present in $RC_FILE"
fi

# Also export for the current session
export PATH="$VENV_DIR/bin:$PATH"

# ── macro prompt ─────────────────────────────────────────────────────────────

SERVE_MACRO='residual() {
  if [ $# -eq 0 ]; then
    echo "Starting RESIDUAL Command Station…"
    echo "  serve: residual serve --host '"$HOST"' --port '"$PORT"' --data '"$DATA_DIR"'"
    echo "  link:  http://localhost:'"$PORT"'"
    command residual serve --host '"$HOST"' --port '"$PORT"' --data '"$DATA_DIR"'
  else
    command residual "$@"
  fi
}'

# Check existing setting
MACRO_ENABLED=$(get_setting "serve_macro")

if [ -z "$MACRO_ENABLED" ]; then
  # First run — ask the user
  echo ""
  info "Setup option: typing just \`residual\` (no arguments) can auto-start the Station."
  echo ""
  echo "  When enabled:"
  echo "    \$ residual          → starts server on $HOST:$PORT, data=$DATA_DIR"
  echo "    \$ residual <args>   → passes through to the real CLI"
  echo ""
  echo "  When disabled:"
  echo "    \$ residual          → shows CLI help (normal behaviour)"
  echo ""
  printf 'Enable the serve macro? [Y/n] '
  if [ -t 0 ]; then
    read -r reply
  else
    # Non-interactive (piped / no TTY) — default to yes
    reply="Y"
    echo "(no TTY detected — defaulting to yes)"
  fi
  case "$reply" in
    [Nn]*)
      set_setting "serve_macro" "false"
      info "Macro disabled. Change anytime: echo 'serve_macro=true' >> $SETTINGS_FILE"
      ;;
    *)
      set_setting "serve_macro" "true"
      MACRO_ENABLED="true"
      ;;
  esac
fi

# Apply or remove the macro based on setting
if [ "$MACRO_ENABLED" = "true" ]; then
  if ! grep -qF "residual() {" "$RC_FILE" 2>/dev/null; then
    info "Adding \`residual\` macro to $RC_FILE"
    printf '\n%s\n' "$SERVE_MACRO" >> "$RC_FILE"
  else
    info "Macro already present in $RC_FILE"
  fi
  # Also define for the current session
  eval "$SERVE_MACRO"
else
  # Remove macro if present
  if grep -qF "residual() {" "$RC_FILE" 2>/dev/null; then
    info "Removing macro from $RC_FILE (disabled in settings)"
    grep -vF "residual() {" "$RC_FILE" > "$RC_FILE.tmp"
    # Remove the closing brace of the function too (next line after the match)
    awk 'BEGIN{skip=0}
      /^residual\(\) \{$/ {skip=1; next}
      skip==1 && /^\}$/ {skip=0; next}
      {print}
    ' "$RC_FILE.tmp" > "$RC_FILE"
    rm -f "$RC_FILE.tmp"
  fi
fi

# ── tooltip + link ───────────────────────────────────────────────────────────

echo ""
info "Setup complete."
echo ""

# Tooltip
echo "  ┌─────────────────────────────────────────────────────────────────┐"
echo "  │  residual serve --host $HOST --port $PORT --data $DATA_DIR"
echo "  └─────────────────────────────────────────────────────────────────┘"
echo ""

# Try to open browser
LINK="http://localhost:$PORT"
OPENED=false

if command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$LINK" >/dev/null 2>&1 && OPENED=true || true
elif command -v open >/dev/null 2>&1; then
  open "$LINK" >/dev/null 2>&1 && OPENED=true || true
elif command -v start >/dev/null 2>&1; then
  start "$LINK" >/dev/null 2>&1 && OPENED=true || true
fi

if [ "$OPENED" = "false" ]; then
  echo "  Could not auto-open a browser."
  echo "  Click or paste this link:  $LINK"
else
  echo "  Opened: $LINK"
fi

echo ""
echo "  CLI:        residual --help"
echo "  Serve:      residual serve --host $HOST --port $PORT --data $DATA_DIR"
[ "$MACRO_ENABLED" = "true" ] && echo "  Macro:      type \`residual\` (no args) to auto-serve"
echo "  Settings:   $SETTINGS_FILE  (serve_macro=true/false)"
echo ""
