"""Run the existing Command Station with Mission Control enabled.

python -m residual.station.mission_server --port 8765 --data /path/to/station
The ordinary Station UI and all existing worker/acceptance routes are retained.
"""
from __future__ import annotations


def main(argv=None):
    from . import server
    from .mission_routes import with_mission_sync
    # Handler is resolved by Server.__init__; no Station or Store methods change.
    original = server.Handler
    server.Handler = with_mission_sync(original)
    try:
        return server.main(argv)
    finally:
        server.Handler = original


if __name__ == "__main__":
    main()
