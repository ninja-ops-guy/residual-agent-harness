from __future__ import annotations
import multiprocessing as mp
from typing import Any, Callable

def _child(conn, fn: Callable, args: tuple[Any, ...]):
    try: conn.send((True, fn(*args)))
    except BaseException as exc: conn.send((False, {"type": type(exc).__name__, "message": str(exc)[:1000]}))
    finally: conn.close()

def run_isolated(fn: Callable, *args: Any, timeout_s: float = 300.0) -> Any:
    parent, child = mp.Pipe(duplex=False)
    process = mp.get_context("spawn").Process(target=_child, args=(child, fn, args), daemon=True)
    process.start(); child.close()
    if not parent.poll(timeout_s):
        process.terminate(); process.join(5); raise TimeoutError("execution engine timed out")
    ok, payload = parent.recv(); process.join(5)
    if not ok: raise RuntimeError(f"engine process failed: {payload['type']}: {payload['message']}")
    return payload
