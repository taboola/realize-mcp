"""Starlette application factory for SSE transport with OAuth 2.1.

Based on working implementation from mcp-oauth21-test.
"""
import logging

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route, Mount

from ..oauth.routes import (
    protected_resource_metadata_handler,
    authorization_server_metadata_handler,
    register_handler,
)
from .sse_server import create_sse_endpoint, sse_transport

logger = logging.getLogger(__name__)


async def health_handler(request):
    """Health check endpoint for Kubernetes probes."""
    return JSONResponse({"status": "healthy", "service": "realize-mcp"})


def create_app() -> Starlette:
    """Create Starlette application with OAuth 2.1 and SSE support.

    Returns:
        Configured Starlette application
    """
    logger.info("Creating SSE application with OAuth 2.1 support")

    # Create SSE endpoint (stateless - no session manager needed)
    sse_endpoint = create_sse_endpoint()

    # Define routes
    routes = [
        # Health check endpoint for Kubernetes probes
        Route("/health", health_handler, methods=["GET"]),
        # OAuth 2.1 metadata endpoints
        Route(
            "/.well-known/oauth-protected-resource",
            protected_resource_metadata_handler,
            methods=["GET"],
        ),
        Route(
            "/.well-known/oauth-authorization-server",
            authorization_server_metadata_handler,
            methods=["GET"],
        ),
        # Dynamic Client Registration
        Route("/register", register_handler, methods=["POST"]),
        # SSE endpoint - uses Route with methods=["GET"] like working impl
        Route("/sse", sse_endpoint, methods=["GET"]),
        # MCP messages endpoint - uses Mount like working impl
        Mount("/messages/", app=sse_transport.handle_post_message),
    ]

    # Plain Starlette app without middleware (matching working impl)
    app = Starlette(routes=routes)

    return app