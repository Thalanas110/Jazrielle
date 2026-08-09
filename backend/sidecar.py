from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any


def _open_log_stream() -> Any:
    log_path = os.environ.get("JAZRIELLE_LOG_PATH")
    if log_path:
        try:
            path = Path(log_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            return path.open("a", encoding="utf-8")
        except OSError:
            pass
    return open(os.devnull, "w", encoding="utf-8")


def configure_stdio() -> None:
    """Give windowed PyInstaller builds safe standard streams for Uvicorn."""
    if sys.stdin is None:
        sys.stdin = open(os.devnull, "r", encoding="utf-8")
    if sys.stdout is None:
        sys.stdout = _open_log_stream()
    if sys.stderr is None:
        sys.stderr = _open_log_stream()


configure_stdio()

import uvicorn


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Jazrielle local API sidecar")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8000, type=int)
    return parser.parse_args(argv)


def run_server(
    argv: Sequence[str] | None = None,
    server_runner: Callable[..., Any] = uvicorn.run,
) -> None:
    args = parse_args(argv)
    from app.main import app

    server_runner(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    run_server()
