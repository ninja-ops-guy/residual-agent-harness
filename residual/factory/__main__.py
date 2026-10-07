"""Run the Factory CLI after package imports have completed."""
from .runtime import main

if __name__ == '__main__':
    raise SystemExit(main())
