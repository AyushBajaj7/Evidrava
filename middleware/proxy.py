"""Strict local reverse proxy between the browser UI and Evidrava backend."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import re
import secrets
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import urlsplit


MAX_BODY_BYTES = 2_500_000
MAX_WORKBOOK_BODY_BYTES = 32_000_000
REQUEST_ID = re.compile(r"^[A-Za-z0-9-]{8,64}$")
GET_PATHS = {"/health", "/api/v1/project-status", "/api/v1/templates"}
POST_PATHS = {"/api/v1/frame/check", "/api/v1/workbook/check", "/api/v1/sample/draw"}


def require_loopback_host(host: str) -> str:
    """Keep the separately runnable middleware unavailable off the machine."""
    if host != "127.0.0.1":
        raise ValueError("Evidrava local services may bind only to 127.0.0.1")
    return host


def require_loopback_url(value: str, label: str) -> str:
    """Reject accidental forwarding or browser connections to non-local hosts."""
    parsed = urlsplit(value)
    if (
        parsed.scheme != "http"
        or parsed.hostname != "127.0.0.1"
        or parsed.port is None
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(f"{label} must be an http://127.0.0.1:<port> URL")
    return value.rstrip("/")


@dataclass(frozen=True)
class ProxyConfig:
    backend_url: str
    frontend_origin: str
    timeout_seconds: float = 15.0


def json_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def error_body(code: str, message: str) -> dict[str, Any]:
    return {"error": {"code": code, "message": message}, "research_decision": "NOT_EVALUATED"}


def allowed_path(method: str, target: str) -> bool:
    parsed = urlsplit(target)
    if parsed.query or parsed.fragment:
        return False
    return (method == "GET" and parsed.path in GET_PATHS) or (method == "POST" and parsed.path in POST_PATHS)


def max_body_bytes(path: str) -> int:
    """Allow encoded workbook bytes only on their explicit, allowlisted route."""
    return MAX_WORKBOOK_BODY_BYTES if path == "/api/v1/workbook/check" else MAX_BODY_BYTES


def request_id(header_value: str | None) -> str:
    return header_value if header_value and REQUEST_ID.fullmatch(header_value) else secrets.token_hex(16)


def backend_request(config: ProxyConfig, method: str, path: str, body: bytes | None, correlation_id: str) -> tuple[int, bytes, str]:
    """Forward only a pre-approved relative route to the configured backend."""
    url = config.backend_url.rstrip("/") + path
    headers = {"Accept": "application/json", "X-Request-ID": correlation_id}
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=config.timeout_seconds) as response:
            return response.status, response.read(), response.headers.get_content_type()
    except HTTPError as exc:
        return exc.code, exc.read(), exc.headers.get_content_type()
    except URLError as exc:
        return HTTPStatus.BAD_GATEWAY, json_bytes(error_body("BACKEND_UNAVAILABLE", f"Local backend is unavailable: {exc.reason}")), "application/json"


class MiddlewareHandler(BaseHTTPRequestHandler):
    server_version = "EvidravaMiddleware/0.1"

    @property
    def config(self) -> ProxyConfig:
        return self.server.proxy_config  # type: ignore[attr-defined]

    def log_message(self, format: str, *args: Any) -> None:
        print(f"middleware {self.address_string()} - {format % args}")

    def _origin_allowed(self) -> bool:
        origin = self.headers.get("Origin")
        return origin is None or origin == self.config.frontend_origin

    def _write(self, status: int, body: bytes, content_type: str = "application/json", correlation_id: str | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type if "charset=" in content_type else content_type + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        if correlation_id:
            self.send_header("X-Request-ID", correlation_id)
        origin = self.headers.get("Origin")
        if origin == self.config.frontend_origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.end_headers()
        self.wfile.write(body)

    def _reject(self, status: int, code: str, message: str, correlation_id: str | None = None) -> None:
        self._write(status, json_bytes(error_body(code, message)), correlation_id=correlation_id)

    def _read_body(self) -> tuple[bytes | None, tuple[int, str, str] | None]:
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            return None, (HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "JSON_REQUIRED", "Use Content-Type: application/json")
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            return None, (HTTPStatus.LENGTH_REQUIRED, "CONTENT_LENGTH_REQUIRED", "A valid Content-Length is required")
        if length < 1 or length > max_body_bytes(urlsplit(self.path).path):
            return None, (HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "REQUEST_TOO_LARGE", "Request exceeds the middleware size limit")
        return self.rfile.read(length), None

    def _proxy(self, method: str) -> None:
        correlation_id = request_id(self.headers.get("X-Request-ID"))
        if not self._origin_allowed():
            self._reject(HTTPStatus.FORBIDDEN, "ORIGIN_NOT_ALLOWED", "This origin is not allowed to use the local middleware", correlation_id)
            return
        if not allowed_path(method, self.path):
            self._reject(HTTPStatus.NOT_FOUND, "ROUTE_NOT_ALLOWED", "The requested route is not exposed by local middleware", correlation_id)
            return
        body = None
        if method == "POST":
            body, error = self._read_body()
            if error is not None:
                self._reject(*error, correlation_id=correlation_id)
                return
        status, response_body, content_type = backend_request(self.config, method, self.path, body, correlation_id)
        self._write(status, response_body, content_type, correlation_id)

    def do_GET(self) -> None:
        self._proxy("GET")

    def do_POST(self) -> None:
        self._proxy("POST")

    def do_OPTIONS(self) -> None:
        correlation_id = request_id(self.headers.get("X-Request-ID"))
        origin = self.headers.get("Origin")
        requested_method = self.headers.get("Access-Control-Request-Method", "")
        if origin != self.config.frontend_origin or requested_method not in {"GET", "POST"} or not allowed_path(requested_method, self.path):
            self._reject(HTTPStatus.FORBIDDEN, "PREFLIGHT_REJECTED", "This preflight request is not allowed", correlation_id)
            return
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Methods", requested_method)
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Request-ID")
        self.send_header("Access-Control-Max-Age", "600")
        self.send_header("Vary", "Origin, Access-Control-Request-Method, Access-Control-Request-Headers")
        self.send_header("X-Request-ID", correlation_id)
        self.end_headers()

    def do_PUT(self) -> None:
        self._reject(HTTPStatus.METHOD_NOT_ALLOWED, "METHOD_NOT_ALLOWED", "Only GET, POST and approved OPTIONS requests are supported")

    do_DELETE = do_PUT
    do_PATCH = do_PUT


def create_server(host: str = "127.0.0.1", port: int = 8001, *, backend_url: str = "http://127.0.0.1:8002", frontend_origin: str = "http://127.0.0.1:5173") -> ThreadingHTTPServer:
    require_loopback_host(host)
    safe_backend_url = require_loopback_url(backend_url, "backend_url")
    safe_frontend_origin = require_loopback_url(frontend_origin, "frontend_origin")
    server = ThreadingHTTPServer((host, port), MiddlewareHandler)
    server.proxy_config = ProxyConfig(  # type: ignore[attr-defined]
        backend_url=safe_backend_url,
        frontend_origin=safe_frontend_origin,
    )
    return server


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run strict local Evidrava browser middleware")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--backend-url", default="http://127.0.0.1:8002")
    parser.add_argument("--frontend-origin", default="http://127.0.0.1:5173")
    args = parser.parse_args(argv)
    try:
        server = create_server(args.host, args.port, backend_url=args.backend_url, frontend_origin=args.frontend_origin)
    except ValueError as exc:
        parser.error(str(exc))
    print(f"Evidrava middleware listening at http://{args.host}:{args.port}; forwarding to {args.backend_url}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0
