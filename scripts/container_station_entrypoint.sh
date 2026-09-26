#!/usr/bin/env sh
# Container-only transport shim for the Command Station.
#
# Security invariant:
#   the Station itself remains bound to 127.0.0.1 and therefore keeps the same
#   loopback-only exposure contract as native mode.
#
# Docker port publishing cannot reach a service bound to the container's own
# loopback interface, so a tiny TCP forwarder listens on the container-facing
# port and forwards bytes to the loopback-bound Station. The browser still
# connects to host-loopback because compose.yaml publishes 127.0.0.1:8765 only.
#
# The forwarded HTTP Host header is not rewritten. Station host validation
# therefore still applies and is explicitly constrained to localhost:8765 and
# 127.0.0.1:8765.
set -eu

PROXY_PORT="${RESIDUAL_CONTAINER_PROXY_PORT:-8765}"
STATION_PORT="${RESIDUAL_CONTAINER_STATION_PORT:-8766}"

case "$PROXY_PORT" in
  *[!0-9]*|'') echo "invalid RESIDUAL_CONTAINER_PROXY_PORT" >&2; exit 2 ;;
esac
case "$STATION_PORT" in
  *[!0-9]*|'') echo "invalid RESIDUAL_CONTAINER_STATION_PORT" >&2; exit 2 ;;
esac
if [ "$PROXY_PORT" = "$STATION_PORT" ]; then
  echo "container proxy and Station ports must differ" >&2
  exit 2
fi

: "${RESIDUAL_ALLOWED_HOSTS:=localhost:$PROXY_PORT,127.0.0.1:$PROXY_PORT}"
export RESIDUAL_ALLOWED_HOSTS

# Start only the forwarding process on the container network. The authoritative
# Station never binds 0.0.0.0 and does not opt into RESIDUAL_REMOTE_EXPOSURE.
socat   "TCP-LISTEN:$PROXY_PORT,fork,reuseaddr,bind=0.0.0.0"   "TCP:127.0.0.1:$STATION_PORT" &
PROXY_PID=$!

cleanup() {
  kill "$PROXY_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# Keep the Station as the foreground service so Docker health/restart semantics
# are still driven by the real server process. Any additional CLI arguments are
# forwarded after the fixed loopback bind and private in-container port.
python3 -m residual.station.server   --host 127.0.0.1   --port "$STATION_PORT"   "$@"
