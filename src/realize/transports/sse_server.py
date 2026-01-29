"""Server-Sent Events endpoint for MCP protocol with OAuth 2.1.

Uses the mcp SDK's SseServerTransport for proper MCP protocol handling.
Based on working implementation from mcp-oauth21-test.
"""
import logging
from typing import Callable

from starlette.requests import Request
from starlette.responses import Response
from mcp.server.sse import SseServerTransport
from mcp.server import NotificationOptions
from mcp.server.models import InitializationOptions

from ..config import config
from ..oauth.context import set_session_token, clear_session_token
from ..oauth.session import SessionManager

logger = logging.getLogger(__name__)

# SSE transport - shared instance
sse_transport = SseServerTransport("/messages/")


def create_sse_endpoint(session_manager: SessionManager) -> Callable:
    """Create SSE endpoint handler with access to session manager for token validation.

    Args:
        session_manager: SessionManager to validate tokens against

    Returns:
        Async handler function for GET /sse
    """

    async def sse_endpoint(request: Request) -> Response:
        """SSE endpoint for MCP over HTTP with OAuth 2.1.

        This is a Starlette route handler that validates Bearer token
        and establishes SSE connection for MCP protocol.
        """
        # Check for Bearer token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            # Return 401 to trigger OAuth flow
            logger.info("No Bearer token in SSE request - returning 401")
            return Response(
                status_code=401,
                headers={
                    "WWW-Authenticate": f'Bearer resource_metadata="{config.mcp_server_url}/.well-known/oauth-protected-resource"'
                }
            )

        token = auth_header[7:]

        # Validate token was issued through our OAuth flow
        session_id = await session_manager.find_session_by_token(token)
        if session_id is None:
            # Token not found in session manager - not issued through our OAuth flow
            logger.info("Bearer token not found in session manager - returning 401 to trigger OAuth flow")
            return Response(
                status_code=401,
                headers={
                    "WWW-Authenticate": f'Bearer resource_metadata="{config.mcp_server_url}/.well-known/oauth-protected-resource", error="invalid_token", error_description="Token not recognized"'
                }
            )

        logger.info(f"SSE connection established with valid Bearer token (session: {session_id})")
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
            logger.debug(f"Client session disconnected {session_id}")

        # Return empty response after SSE ends (required to avoid NoneType error)
        return Response()

    return sse_endpoint
