"""OAuth route handlers for Starlette."""
import logging
from typing import Callable
from urllib.parse import urlencode

from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse

from ..config import config
from .metadata import get_protected_resource_metadata, proxy_authorization_server_metadata
from .dcr import handle_client_registration, DCRError
from .token import TokenProxy

logger = logging.getLogger(__name__)


async def protected_resource_metadata_handler(request: Request) -> JSONResponse:
    """Handle GET /.well-known/oauth-protected-resource (RFC 9728)."""
    return JSONResponse(get_protected_resource_metadata())


async def authorize_handler(request: Request) -> RedirectResponse:
    """Handle GET /authorize - redirect to upstream authorization server.

    This proxy is needed because some MCP clients (e.g., Cursor) refuse to open
    HTTP authorization URLs directly. By proxying through our HTTPS endpoint,
    the browser is redirected to the upstream HTTP auth server.
    """
    query_params = dict(request.query_params)
    logger.info(f"Authorize request for client_id={query_params.get('client_id')}, redirecting to upstream")

    # Build upstream authorization URL
    upstream_authorize_url = f"{config.oauth_server_url}/oauth2.1/authorize"
    if query_params:
        upstream_authorize_url += "?" + urlencode(query_params)

    return RedirectResponse(url=upstream_authorize_url, status_code=302)


async def authorization_server_metadata_handler(request: Request) -> JSONResponse:
    """Handle GET /.well-known/oauth-authorization-server (RFC 8414 proxy)."""
    try:
        metadata = await proxy_authorization_server_metadata()
        return JSONResponse(metadata)
    except Exception as e:
        return JSONResponse(
            {"error": "upstream_error", "error_description": str(e)},
            status_code=502,
        )


async def register_handler(request: Request) -> JSONResponse:
    """Handle POST /register (RFC 7591 Dynamic Client Registration)."""
    try:
        body = await request.json()
    except Exception:
        body = {}

    try:
        response = handle_client_registration(body)
        return JSONResponse(response, status_code=201)
    except DCRError as e:
        return JSONResponse(
            {"error": "invalid_request", "error_description": str(e)},
            status_code=400,
        )


def create_token_handler(token_proxy: TokenProxy) -> Callable:
    """Create token endpoint handler with injected TokenProxy.

    Args:
        token_proxy: TokenProxy instance for proxying requests

    Returns:
        Async handler function for POST /oauth/token
    """

    async def token_handler(request: Request) -> JSONResponse:
        """Handle POST /oauth/token - proxy to upstream auth server.

        Stateless: proxies the request to upstream and returns the response
        directly to the client. No server-side token storage.
        """
        # Get form data
        try:
            form = await request.form()
            form_data = dict(form)
        except Exception:
            return JSONResponse(
                {"error": "invalid_request", "error_description": "Invalid form data"},
                status_code=400,
            )

        # Proxy to upstream
        response_data, status_code = await token_proxy.proxy_token_request(
            form_data=form_data,
        )

        return JSONResponse(response_data, status_code=status_code)

    return token_handler
