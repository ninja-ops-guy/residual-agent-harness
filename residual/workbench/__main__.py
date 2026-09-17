import sys

if len(sys.argv) > 1 and sys.argv[1] == "build":
    from .build import main
    raise SystemExit(main(sys.argv[2:]))

from .runner import main
raise SystemExit(main())
