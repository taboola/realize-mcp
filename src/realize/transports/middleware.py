"""Pure ASGI middleware for Prometheus HTTP metrics and request size limiting."""
import ipaddress
import json
import logging
import time

from starlette.types import ASGIApp, Receive, Scope, Send

from ..app_metrics import metrics

logger = logging.getLogger(__name__)

MAX_REQUEST_BYTES = 131072  # 128KB


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


class InternalOnlyMiddleware:
    """Restrict sensitive endpoints to requests from allowed CIDR ranges.

    Prometheus scrapes pods directly in-cluster, so scope["client"]
    is the real scraper IP (e.g. 10.x.x.x). External requests via
    the load balancer are blocked since their source IP falls outside
    the allowed CIDRs.
    """

    RESTRICTED_PATHS = {"/metrics"}

    def __init__(self, app: ASGIApp, allowed_cidrs: list[str]):
        self.app = app
        self.allowed_networks = [
            ipaddress.ip_network(cidr, strict=False)
            for cidr in allowed_cidrs
        ]

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("path") not in self.RESTRICTED_PATHS:
            await self.app(scope, receive, send)
            return

        client = scope.get("client")
        if client:
            try:
                client_ip = ipaddress.ip_address(client[0])
                if any(client_ip in network for network in self.allowed_networks):
                    await self.app(scope, receive, send)
                    return
            except ValueError:
                pass

        logger.warning(
            "blocked_restricted_path",
            extra={
                "path": scope.get("path"),
                "client_ip": client[0] if client else "unknown",
            },
        )
        await self._send_403(send)

    @staticmethod
    async def _send_403(send: Send) -> None:
        body = json.dumps({
            "error": "forbidden",
            "error_description": "Access denied",
        }).encode()
        await send({
            "type": "http.response.start",
            "status": 403,
            "headers": [
                [b"content-type", b"application/json"],
                [b"content-length", str(len(body)).encode()],
            ],
        })
        await send({
            "type": "http.response.body",
            "body": body,
        })


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
                method=method,
                endpoint=path,
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
