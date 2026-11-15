"""Launch Evidrava's local frontend, middleware and backend together.

Use Ctrl+C to stop every child. This is deliberately a local development
launcher: it binds to loopback by default and does not publish any service.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]


def port(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Port must be an integer") from exc
    if not 1 <= number <= 65535:
        raise argparse.ArgumentTypeError("Port must be between 1 and 65535")
    return number


def stop(processes: list[subprocess.Popen]) -> None:
    for process in processes:
        if process.poll() is None:
            process.terminate()
    deadline = time.monotonic() + 5
    for process in processes:
        if process.poll() is None:
            try:
                process.wait(timeout=max(0.1, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                process.kill()
    for process in processes:
        if process.poll() is None:
            process.wait(timeout=2)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1", help="Loopback host used by all three local services")
    parser.add_argument("--frontend-port", type=port, default=5173)
    parser.add_argument("--middleware-port", type=port, default=8001)
    parser.add_argument("--backend-port", type=port, default=8002)
    args = parser.parse_args(argv)
    if args.host != "127.0.0.1":
        parser.error("Evidrava local services may bind only to 127.0.0.1")
    ports = [args.frontend_port, args.middleware_port, args.backend_port]
    if len(set(ports)) != len(ports):
        parser.error("Frontend, middleware and backend ports must be distinct")
    backend_url = f"http://{args.host}:{args.backend_port}"
    frontend_url = f"http://{args.host}:{args.frontend_port}"
    middleware_url = f"http://{args.host}:{args.middleware_port}"
    commands = [
        [sys.executable, "-u", "-m", "backend", "--host", args.host, "--port", str(args.backend_port)],
        [sys.executable, "-u", "-m", "middleware", "--host", args.host, "--port", str(args.middleware_port), "--backend-url", backend_url, "--frontend-origin", frontend_url],
        [sys.executable, "-u", "-m", "frontend", "--host", args.host, "--port", str(args.frontend_port), "--api-base", middleware_url]
    ]
    environment = os.environ.copy()
    processes: list[subprocess.Popen] = []
    popen_options = {"cwd": ROOT, "env": environment}
    if os.name == "nt":
        # Keep Ctrl+C with this launcher. The parent then stops all children
        # deliberately instead of treating one interrupted child as a crash.
        popen_options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        popen_options["start_new_session"] = True
    try:
        for command in commands:
            processes.append(subprocess.Popen(command, **popen_options))
        print("Evidrava local web stack is starting:", flush=True)
        print(f"  frontend:   {frontend_url}", flush=True)
        print(f"  middleware: {middleware_url}", flush=True)
        print(f"  backend:    {backend_url}", flush=True)
        print("Press Ctrl+C to stop all local services.", flush=True)
        while True:
            for process in processes:
                exit_code = process.poll()
                if exit_code is not None:
                    print(f"A local service exited with code {exit_code}; stopping the stack.", file=sys.stderr, flush=True)
                    return exit_code or 1
            time.sleep(0.2)
    except KeyboardInterrupt:
        print("Stopping Evidrava local web stack.", flush=True)
        return 0
    finally:
        stop(processes)


if __name__ == "__main__":
    raise SystemExit(main())
