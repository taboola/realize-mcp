"""Server-Sent Events endpoint for MCP protocol with OAuth 2.1.

Uses the mcp SDK's SseServerTransport for proper MCP protocol handling.
Stateless: extracts Bearer token from Authorization header per-request,
sets it in async context for the duration of the connection, discards on disconnect.
"""
import logging
from typing import Callable

from starlette.requests import Request
from starlette.responses import Response
from mcp.server.sse import SseServerTransport
from mcp.server import NotificationOptions
from mcp.server.models import InitializationOptions

from ..oauth.context import set_session_token, clear_session_token
from ..oauth.routes import _get_base_url

logger = logging.getLogger(__name__)

# SSE transport - shared instance
sse_transport = SseServerTransport("/messages/")


def create_sse_endpoint() -> Callable:
    """Create SSE endpoint handler.

    Returns:
        Async handler function for GET /sse
    """

    async def sse_endpoint(request: Request) -> Response:
        """SSE endpoint for MCP over HTTP with OAuth 2.1.

        Stateless: extracts Bearer token from Authorization header,
        sets it in async context for downstream API calls, clears on disconnect.
        Token validation is delegated to the downstream Realize API.
        """
        # Check for Bearer token
        auth_header = request.headers.get("Authorization", "")
        base_url = _get_base_url(request)

        if not auth_header.startswith("Bearer "):
            # Return 401 to trigger OAuth flow
            logger.info("No Bearer token in SSE request - returning 401")
            return Response(
                status_code=401,
                headers={
                    "WWW-Authenticate": f'Bearer resource_metadata="{base_url}/.well-known/oauth-protected-resource"'
                }
            )

        token = auth_header[7:]
        if not token:
            logger.info("Empty Bearer token in SSE request - returning 401")
            return Response(
                status_code=401,
                headers={
                    "WWW-Authenticate": f'Bearer resource_metadata="{base_url}/.well-known/oauth-protected-resource"'
                }
            )

        logger.info("SSE connection established with Bearer token")
        # Set token in contextvar (isolated to this async context)
        set_session_token(token)

        # Import here to avoid circular dependency
        from ..realize_server import server

        # Build initialization options - must match what stdio uses
        init_options = InitializationOptions(
            server_name="realize-mcp",
            server_version="1.0.0",
            capabilities=server.get_capabilities(
                notification_options=NotificationOptions(),
                experimental_capabilities={},
            ),
        )

        try:
            # Handle SSE connection
            async with sse_transport.connect_sse(
                request.scope, request.receive, request._send
            ) as streams:
                await server.run(streams[0], streams[1], init_options)
        finally:
            # Cleanup token from context when connection ends
            clear_session_token()
            logger.debug("Client SSE connection disconnected")

        # Return empty response after SSE ends (required to avoid NoneType error)
        return Response()

    return sse_endpoint
