"""Streamable HTTP endpoint for MCP protocol with OAuth 2.1.

Uses the mcp SDK's StreamableHTTPSessionManager in stateless mode
for proper MCP protocol handling over Streamable HTTP transport.
Stateless: extracts Bearer token from Authorization header per-request,
sets it in async context for the duration of the request, discards after.
"""
import json
import logging
from typing import Optional

from starlette.requests import Request
from starlette.responses import Response
from starlette.types import Receive, Scope, Send

from mcp.server.streamable_http_manager import StreamableHTTPSessionManager

from ..app_metrics import metrics
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

    @staticmethod
    def _extract_client_info_from_body(body: bytes) -> Optional[tuple[str, str]]:
        """Parse JSON-RPC body and extract client info from initialize requests.

        Returns (client_name, client_version) if this is an initialize request
        with clientInfo, otherwise None.
        """
        try:
            data = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None

        if not isinstance(data, dict):
            return None
        if data.get("method") != "initialize":
            return None

        params = data.get("params")
        if not isinstance(params, dict):
            return None

        client_info = params.get("clientInfo")
        if not isinstance(client_info, dict):
            return None

        name = client_info.get("name")
        if not name:
            return None

        version = client_info.get("version") or "?"
        return (name, version)

    async def __call__(
        self, scope: Scope, receive: Receive, send: Send
    ) -> None:
        """Handle ASGI request with Bearer token extraction."""
        request = Request(scope, receive)

        if request.method not in ("POST", "DELETE"):
            response = Response(
                status_code=405,
                headers={"Allow": "POST, DELETE"},
            )
            await response(scope, receive, send)
            return

        auth_header = request.headers.get("Authorization", "")
        base_url = _get_base_url(request)

        if not auth_header.startswith("Bearer "):
            logger.info("No Bearer token in Streamable HTTP request - returning 401")
            body = await request.body()
            client_info = self._extract_client_info_from_body(body)
            if client_info:
                metrics.record_client_connection(client_info[0], client_info[1])
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
            body = await request.body()
            client_info = self._extract_client_info_from_body(body)
            if client_info:
                metrics.record_client_connection(client_info[0], client_info[1])
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

        captured_body = bytearray()

        async def tee_receive():
            message = await receive()
            if message["type"] == "http.request":
                captured_body.extend(message.get("body", b""))
            return message

        try:
            await self.session_manager.handle_request(scope, tee_receive, send)
        finally:
            clear_session_token()
            client_info = self._extract_client_info_from_body(bytes(captured_body))
            if client_info:
                metrics.record_client_connection(client_info[0], client_info[1])
            logger.debug("Streamable HTTP request completed, token cleared")
