"""Starlette application factory for Streamable HTTP transport with OAuth 2.1."""
import contextlib
import logging
from collections.abc import AsyncIterator

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

from ..oauth.routes import (
    protected_resource_metadata_handler,
    authorization_server_metadata_handler,
    register_handler,
)
from .streamable_http_server import (
    create_streamable_http_session_manager,
    StreamableHTTPEndpoint,
)

logger = logging.getLogger(__name__)


async def health_handler(request):
    """Health check endpoint for Kubernetes probes."""
    return JSONResponse({"status": "healthy", "service": "realize-mcp"})


def create_app() -> Starlette:
    """Create Starlette application with OAuth 2.1 and Streamable HTTP support.

    Returns:
        Configured Starlette application
    """
    logger.info("Creating Streamable HTTP application with OAuth 2.1 support")

    session_manager = create_streamable_http_session_manager()

    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncIterator[None]:
        async with session_manager.run():
            logger.info("StreamableHTTP session manager started")
            yield
            logger.info("StreamableHTTP session manager stopping")

    streamable_endpoint = StreamableHTTPEndpoint(session_manager)

    routes = [
        Route("/health", health_handler, methods=["GET"]),
        Route(
            "/.well-known/oauth-protected-resource/{path:path}",
            protected_resource_metadata_handler,
            methods=["GET"],
        ),
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
        Route("/register", register_handler, methods=["POST"]),
        Route("/mcp", streamable_endpoint),
    ]

    app = Starlette(routes=routes, lifespan=lifespan)

    return app
