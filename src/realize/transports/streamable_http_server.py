"""Streamable HTTP endpoint for MCP protocol with OAuth 2.1.

Uses the mcp SDK's StreamableHTTPSessionManager in stateless mode
for proper MCP protocol handling over Streamable HTTP transport.
Stateless: extracts Bearer token from Authorization header per-request,
sets it in async context for the duration of the request, discards after.
"""
import logging

from starlette.requests import Request
from starlette.responses import Response
from starlette.types import Receive, Scope, Send

from mcp.server.streamable_http_manager import StreamableHTTPSessionManager

from ..oauth.context import set_session_token, clear_session_token
from ..oauth.routes import _get_base_url

logger = logging.getLogger(__name__)


def create_streamable_http_session_manager() -> StreamableHTTPSessionManager:
    """Create a StreamableHTTPSessionManager in stateless mode.

    Uses the global MCP server instance and configures for stateless
    operation (no session tracking, fresh transport per request).

    Returns:
        Configured StreamableHTTPSessionManager
    """
    from ..realize_server import server

    return StreamableHTTPSessionManager(
        app=server,
        stateless=True,
    )


class StreamableHTTPEndpoint:
    """ASGI app for Streamable HTTP with OAuth 2.1 Bearer token extraction.

    Implemented as a class (not a function) so that Starlette's Route treats
    it as a raw ASGI app rather than wrapping it in request_response().
    This avoids the 307 trailing-slash redirect that Mount causes.
    """

    def __init__(self, session_manager: StreamableHTTPSessionManager):
        self.session_manager = session_manager

    async def __call__(
        self, scope: Scope, receive: Receive, send: Send
    ) -> None:
        """Handle ASGI request with Bearer token extraction."""
        request = Request(scope, receive)

        auth_header = request.headers.get("Authorization", "")
        base_url = _get_base_url(request)

        if not auth_header.startswith("Bearer "):
            logger.info("No Bearer token in Streamable HTTP request - returning 401")
            response = Response(
                status_code=401,
                headers={
                    "WWW-Authenticate": f'Bearer resource_metadata="{base_url}/.well-known/oauth-protected-resource"'
                },
            )
            await response(scope, receive, send)
            return

        token = auth_header[7:]
        if not token:
            logger.info("Empty Bearer token in Streamable HTTP request - returning 401")
            response = Response(
                status_code=401,
                headers={
                    "WWW-Authenticate": f'Bearer resource_metadata="{base_url}/.well-known/oauth-protected-resource"'
                },
            )
            await response(scope, receive, send)
            return

        logger.info("Streamable HTTP request with Bearer token")
        set_session_token(token)

        try:
            await self.session_manager.handle_request(scope, receive, send)
        finally:
            clear_session_token()
            logger.debug("Streamable HTTP request completed, token cleared")
