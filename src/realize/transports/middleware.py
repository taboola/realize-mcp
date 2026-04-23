"""Pure ASGI middleware for Prometheus HTTP metrics and request size limiting."""
import json
import logging
import time

from starlette.types import ASGIApp, Receive, Scope, Send

from ..app_metrics import metrics

logger = logging.getLogger(__name__)

MAX_REQUEST_BYTES = 131072  # 128KB

_EXACT_ROUTES = frozenset({"/health", "/register", "/mcp"})
_ALLOWED_METHODS = frozenset(
    {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}
)


_WELLKNOWN_PREFIXES = (
    "/.well-known/oauth-protected-resource",
    "/.well-known/oauth-authorization-server",
)


def _normalize_http_path(path: str) -> str:
    """Map raw ASGI path to a bounded set of endpoint labels.

    Prevents unbounded label cardinality from `{path:path}` routes and
    scanner traffic that would otherwise blow past the Prometheus sample cap.
    """
    if path in _EXACT_ROUTES:
        return path
    for prefix in _WELLKNOWN_PREFIXES:
        if path == prefix or path.startswith(prefix + "/"):
            return prefix
    return "other"


def _normalize_http_method(method: str) -> str:
    return method if method in _ALLOWED_METHODS else "other"


class RequestSizeLimitMiddleware:
    """Reject HTTP requests with bodies exceeding MAX_REQUEST_BYTES.

    Two-layer defence:
    1. Fast path – if Content-Length header exceeds the limit, return 413
       immediately without reading the body.
    2. Streaming guard – wrap the ASGI receive callable to count bytes as
       they arrive.  Covers spoofed Content-Length and chunked transfers.
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # --- Fast path: check Content-Length header ---
        headers = dict(scope.get("headers", []))
        content_length = headers.get(b"content-length")
        if content_length is not None and int(content_length) > MAX_REQUEST_BYTES:
            await self._send_413(scope, receive, send)
            return

        # --- Streaming guard: count bytes from receive ---
        bytes_received = 0

        async def guarded_receive() -> dict:
            nonlocal bytes_received
            message = await receive()
            if message.get("type") == "http.request":
                body = message.get("body", b"")
                bytes_received += len(body)
                if bytes_received > MAX_REQUEST_BYTES:
                    raise _RequestTooLarge()
            return message

        try:
            await self.app(scope, guarded_receive, send)
        except _RequestTooLarge:
            await self._send_413(scope, receive, send)

    @staticmethod
    async def _send_413(scope: Scope, receive: Receive, send: Send) -> None:
        body = json.dumps({
            "error": "request_too_large",
            "error_description": "Request body exceeds 128KB limit",
        }).encode()
        await send({
            "type": "http.response.start",
            "status": 413,
            "headers": [
                [b"content-type", b"application/json"],
                [b"content-length", str(len(body)).encode()],
            ],
        })
        await send({
            "type": "http.response.body",
            "body": body,
        })


class _RequestTooLarge(Exception):
    """Internal signal for streaming guard."""
    pass


class MetricsMiddleware:
    """Records HTTP request count and latency for all routes except /metrics."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path == "/metrics":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "UNKNOWN")
        status_code = 500  # default in case send is never called with response

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        start = time.monotonic()
        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration = time.monotonic() - start
            metrics.record_http_request(
                method=_normalize_http_method(method),
                endpoint=_normalize_http_path(path),
                http_status=status_code,
                duration=duration,
            )
            log = logger.debug if path == "/health" else logger.info
            log(
                "http_request",
                extra={
                    "method": method,
                    "path": path,
                    "status_code": status_code,
                    "duration_ms": round(duration * 1000, 1),
                },
            )
