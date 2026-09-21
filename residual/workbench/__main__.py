import os
import sys


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "build":
        from .build import main as workbench_main
        status = workbench_main(args[1:])
    else:
        from .runner import main as workbench_main
        status = workbench_main(args)

    # The WebVM writable overlay is browser-backed persistent storage. A
    # successful standalone CLI command must cross the same filesystem-wide
    # durability boundary as Mission Control before its caller can safely
    # reload/recycle the browser guest. Platforms without os.sync retain their
    # normal CLI behavior; WebVM/Linux has it and must complete it before
    # success is published to the shell.
    if status == 0:
        sync = getattr(os, "sync", None)
        if sync is not None:
            sync()
    return status


if __name__ == "__main__":
    raise SystemExit(main())
