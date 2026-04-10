"""Dedicated metrics server for port separation.

Runs on a separate port (default 8092) so infrastructure can restrict
access without application-level IP filtering.
"""
import logging

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route

logger = logging.getLogger(__name__)


async def metrics_handler(request: Request) -> Response:
    """Metrics endpoint."""
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


def create_metrics_app() -> Starlette:
    """Create minimal Starlette app for metrics.

    Serves on both ``/`` and ``/metrics`` (backward compatibility).
    """
    return Starlette(
        routes=[
            Route("/", metrics_handler, methods=["GET"]),
            Route("/metrics", metrics_handler, methods=["GET"]),
        ],
    )
