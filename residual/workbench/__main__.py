import sys

if len(sys.argv) > 1 and sys.argv[1] == "arena":
    from .arena_benchmark import main
    raise SystemExit(main(sys.argv[2:]))

if len(sys.argv) > 1 and sys.argv[1] == "build":
    from .build import main
    raise SystemExit(main(sys.argv[2:]))

from .runner import main
raise SystemExit(main())
