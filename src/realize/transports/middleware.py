"""Pure ASGI middleware for Prometheus HTTP metrics."""
import logging
import time

from starlette.types import ASGIApp, Receive, Scope, Send

from ..app_metrics import metrics

logger = logging.getLogger(__name__)


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
