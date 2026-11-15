"""Serve the dependency-free Evidrava local console."""
from __future__ import annotations

import argparse
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
from urllib.parse import urlsplit


PUBLIC = Path(__file__).resolve().parent / "public"


def require_loopback_host(host: str) -> str:
    """Keep the browser console private to this computer."""
    if host != "127.0.0.1":
        raise ValueError("Evidrava local services may bind only to 127.0.0.1")
    return host


def require_loopback_url(value: str) -> str:
    """Prevent the static console from sending workbook bytes off-device."""
    parsed = urlsplit(value)
    if (
        parsed.scheme != "http"
        or parsed.hostname != "127.0.0.1"
        or parsed.port is None
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("api_base must be an http://127.0.0.1:<port> URL")
    return value.rstrip("/")


class FrontendHandler(SimpleHTTPRequestHandler):
    server_version = "EvidravaFrontend/0.1"

    def __init__(self, *args, directory: str | None = None, **kwargs):
        super().__init__(*args, directory=directory or str(PUBLIC), **kwargs)

    @property
    def api_base(self) -> str:
        return self.server.api_base  # type: ignore[attr-defined]

    def end_headers(self) -> None:
        api_origin = urlsplit(self.api_base)
        connect_source = f"{api_origin.scheme}://{api_origin.netloc}" if api_origin.scheme and api_origin.netloc else "'self'"
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", f"default-src 'self'; connect-src 'self' {connect_source}; style-src 'self'; script-src 'self'; base-uri 'none'; frame-ancestors 'none'")
        super().end_headers()

    def do_GET(self) -> None:
        parsed = urlsplit(self.path)
        if parsed.path == "/config.js" and not parsed.query:
            body = ("window.EVIDRAVA_CONFIG = Object.freeze(" + json.dumps({"apiBase": self.api_base}) + ");\n").encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/javascript; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.query:
            self.send_error(HTTPStatus.BAD_REQUEST, "Query parameters are not supported by the local console")
            return
        super().do_GET()

    def do_POST(self) -> None:
        self.send_error(HTTPStatus.METHOD_NOT_ALLOWED, "Static frontend accepts GET only")


def create_server(host: str = "127.0.0.1", port: int = 5173, *, api_base: str = "http://127.0.0.1:8001") -> ThreadingHTTPServer:
    require_loopback_host(host)
    safe_api_base = require_loopback_url(api_base)
    server = ThreadingHTTPServer((host, port), FrontendHandler)
    server.api_base = safe_api_base  # type: ignore[attr-defined]
    return server


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the local Evidrava frontend")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5173)
    parser.add_argument("--api-base", default=os.environ.get("EVIDRAVA_MIDDLEWARE_URL", "http://127.0.0.1:8001"))
    args = parser.parse_args(argv)
    try:
        server = create_server(args.host, args.port, api_base=args.api_base)
    except ValueError as exc:
        parser.error(str(exc))
    print(f"Evidrava frontend listening at http://{args.host}:{args.port}; using {args.api_base}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0
