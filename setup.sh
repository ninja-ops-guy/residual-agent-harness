#!/usr/bin/env bash
# RESIDUAL setup script
# - Installs residual-agent-harness into a persistent dedicated venv
# - Adds a bounded PATH block to the active shell rc file
# - Optionally adds a bounded residual serve macro
# - Defaults the Command Station to loopback-only access
set -euo pipefail

REPO_DIR="$(cd -- "$(dirname -- "\${BASH_SOURCE[0]}")" && pwd)"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
STATE_HOME="${XDG_STATE_HOME:-$HOME/.local/state}"
VENV_DIR="${RESIDUAL_VENV:-$DATA_HOME/residual/venv}"
DATA_DIR="${RESIDUAL_DATA:-$STATE_HOME/residual/station}"
HOST="${RESIDUAL_HOST:-127.0.0.1}"
PORT="${RESIDUAL_PORT:-8765}"
SETTINGS_FILE="${RESIDUAL_SETTINGS:-$HOME/.residual-settings}"

PATH_BEGIN="# BEGIN residual-agent-harness PATH"
PATH_END="# END residual-agent-harness PATH"
MACRO_BEGIN="# BEGIN residual-agent-harness serve macro"
MACRO_END="# END residual-agent-harness serve macro"

info()  { printf '\033[1;34m[residual]\033[0m %s\n' "$*"; }
warn()  { printf '\033[1;33m[residual]\033[0m %s\n' "$*"; }
error() { printf '\033[1;31m[residual]\033[0m %s\n' "$*" >&2; }

set_setting() {
  local key="$1" val="$2" dir tmp
  dir="$(dirname -- "$SETTINGS_FILE")"
  mkdir -p "$dir"
  tmp="$(mktemp "$dir/.residual-settings.XXXXXX")"
  if [ -f "$SETTINGS_FILE" ]; then
    grep -v "^$key=" "$SETTINGS_FILE" > "$tmp" || true
  fi
  printf '%s=%s\n' "$key" "$val" >> "$tmp"
  chmod 600 "$tmp"
  mv -f -- "$tmp" "$SETTINGS_FILE"
}

get_setting() {
  local key="$1"
  [ -f "$SETTINGS_FILE" ] && grep "^$key=" "$SETTINGS_FILE" | tail -1 | cut -d= -f2- || true
}

PY=""
for candidate in python3.13 python3.12 python3.11 python3; do
  if command -v "$candidate" >/dev/null 2>&1; then
    if "$candidate" -c 'import sys; raise SystemExit(sys.version_info < (3, 11))' >/dev/null 2>&1; then
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
mkdir -p "$(dirname -- "$VENV_DIR")" "$DATA_DIR"

if [ -d "$VENV_DIR" ]; then
  if [ ! -x "$VENV_DIR/bin/python" ] || ! "$VENV_DIR/bin/python" -c 'import sys' >/dev/null 2>&1; then
    warn "Existing virtual environment is incomplete; repairing $VENV_DIR"
    "$PY" -m venv --clear "$VENV_DIR"
  fi
else
  info "Creating venv at $VENV_DIR"
  "$PY" -m venv "$VENV_DIR"
fi

VENV_PY="$VENV_DIR/bin/python"
"$VENV_PY" -m pip install --upgrade pip -q
info "Installing residual-agent-harness (editable)"
"$VENV_PY" -m pip install -e "$REPO_DIR"

if [ -n "${ZSH_VERSION:-}" ]; then
  RC_FILE="$HOME/.zshrc"
elif [ -n "${BASH_VERSION:-}" ]; then
  RC_FILE="$HOME/.bashrc"
else
  RC_FILE="$HOME/.profile"
fi

MACRO_ENABLED="$(get_setting serve_macro)"
case "$MACRO_ENABLED" in
  true|false) ;;
  "")
    echo ""
    info "Optional: typing residual with no arguments can start Command Station."
    echo "  Default bind: $HOST:$PORT"
    printf 'Enable the serve macro? [y/N] '
    if [ -t 0 ]; then
      read -r reply
    else
      reply="N"
      echo "(no TTY detected - leaving the macro disabled)"
    fi
    case "$reply" in
      [Yy]*) MACRO_ENABLED=true ;;
      *) MACRO_ENABLED=false ;;
    esac
    set_setting serve_macro "$MACRO_ENABLED"
    ;;
  *)
    warn "Invalid serve_macro setting; disabling the macro"
    MACRO_ENABLED=false
    set_setting serve_macro false
    ;;
esac

PATH_BLOCK="$PATH_BEGIN
export PATH=\"$VENV_DIR/bin:\$PATH\"
$PATH_END"

MACRO_BLOCK="$MACRO_BEGIN
residual() {
  if [ \$# -eq 0 ]; then
    echo \"Starting RESIDUAL Command Station on $HOST:$PORT\"
    command residual serve --host \"$HOST\" --port \"$PORT\" --data \"$DATA_DIR\"
  else
    command residual \"\$@\"
  fi
}
$MACRO_END"

export RESIDUAL_SETUP_PATH_BLOCK="$PATH_BLOCK"
export RESIDUAL_SETUP_MACRO_BLOCK="$MACRO_BLOCK"
export RESIDUAL_SETUP_ENABLE_MACRO="$MACRO_ENABLED"
export RESIDUAL_SETUP_PATH_BEGIN="$PATH_BEGIN"
export RESIDUAL_SETUP_PATH_END="$PATH_END"
export RESIDUAL_SETUP_MACRO_BEGIN="$MACRO_BEGIN"
export RESIDUAL_SETUP_MACRO_END="$MACRO_END"

"$PY" - "$RC_FILE" <<'PY'
import os
import stat
import sys
import tempfile
from pathlib import Path

path = Path(sys.argv[1])
path.parent.mkdir(parents=True, exist_ok=True)
original = path.read_text(encoding="utf-8") if path.exists() else ""
lines = original.splitlines()

def remove_managed_block(items, begin, end):
    output = []
    inside = False
    for line in items:
        if line == begin:
            if inside:
                raise RuntimeError(f"nested managed block: {begin}")
            inside = True
            continue
        if line == end:
            if not inside:
                raise RuntimeError(f"unmatched managed block terminator: {end}")
            inside = False
            continue
        if not inside:
            output.append(line)
    if inside:
        raise RuntimeError(f"unterminated managed block: {begin}")
    return output

for begin, end in (
    (os.environ["RESIDUAL_SETUP_PATH_BEGIN"], os.environ["RESIDUAL_SETUP_PATH_END"]),
    (os.environ["RESIDUAL_SETUP_MACRO_BEGIN"], os.environ["RESIDUAL_SETUP_MACRO_END"]),
):
    lines = remove_managed_block(lines, begin, end)

# Migrate only the exact legacy snippets written by the original setup script.
migrated = []
i = 0
while i < len(lines):
    if (
        lines[i] == "# residual-agent-harness"
        and i + 1 < len(lines)
        and lines[i + 1].startswith('export PATH="')
        and "/residual-venv/bin:" in lines[i + 1]
    ):
        i += 2
        continue
    if lines[i] == "residual() {":
        end = next((j for j in range(i + 1, len(lines)) if lines[j] == "}"), None)
        if end is None:
            raise RuntimeError("refusing to rewrite an unterminated residual function")
        block = "\n".join(lines[i : end + 1])
        if "Starting RESIDUAL Command Station" not in block or "command residual serve" not in block:
            raise RuntimeError("refusing to replace an unrecognized user-defined residual function")
        i = end + 1
        continue
    migrated.append(lines[i])
    i += 1

text = "\n".join(migrated).rstrip()
blocks = [os.environ["RESIDUAL_SETUP_PATH_BLOCK"]]
if os.environ["RESIDUAL_SETUP_ENABLE_MACRO"] == "true":
    blocks.append(os.environ["RESIDUAL_SETUP_MACRO_BLOCK"])
new_text = (text + "\n\n" if text else "") + "\n\n".join(blocks) + "\n"

mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o600
with tempfile.NamedTemporaryFile(
    mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
) as handle:
    handle.write(new_text)
    temp_name = handle.name
os.chmod(temp_name, mode)
os.replace(temp_name, path)
PY

export PATH="$VENV_DIR/bin:$PATH"

echo ""
info "Setup complete."
echo "  CLI:      residual --help"
echo "  Serve:    residual serve --host $HOST --port $PORT --data $DATA_DIR"
echo "  Link:     http://$HOST:$PORT"
echo "  Venv:     $VENV_DIR"
echo "  Settings: $SETTINGS_FILE"
if [ "$MACRO_ENABLED" = true ]; then
  echo "  Macro:    residual (no arguments)"
else
  echo "  Macro:    disabled (opt in with serve_macro=true)"
fi
echo ""
