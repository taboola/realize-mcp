"""OAuth route handlers for Starlette."""
import logging

from starlette.requests import Request
from starlette.responses import JSONResponse

from ..config import config
from .metadata import get_protected_resource_metadata, proxy_authorization_server_metadata
from .dcr import handle_client_registration, DCRError

logger = logging.getLogger(__name__)


def _get_base_url(request: Request) -> str:
    """Derive public-facing base URL from the request.

    Uses MCP_SERVER_SCHEME to override the scheme when behind a
    TLS-terminating proxy that doesn't forward X-Forwarded-Proto.
    """
    url = str(request.base_url).rstrip("/")
    if config.mcp_server_scheme:
        url = config.mcp_server_scheme + url[url.index(":"):]
    return url


async def protected_resource_metadata_handler(request: Request) -> JSONResponse:
    """Handle GET /.well-known/oauth-protected-resource (RFC 9728)."""
    base_url = _get_base_url(request)
    return JSONResponse(get_protected_resource_metadata(base_url))


async def authorization_server_metadata_handler(request: Request) -> JSONResponse:
    """Handle GET /.well-known/oauth-authorization-server (RFC 8414 metadata)."""
    base_url = _get_base_url(request)
    try:
        metadata = await proxy_authorization_server_metadata(base_url)
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

    log_extra = {
        "client_name": body.get("client_name"),
        "software_id": body.get("software_id"),
        "software_version": body.get("software_version"),
        "redirect_uris": body.get("redirect_uris"),
        "user_agent": request.headers.get("user-agent"),
    }

    try:
        response = handle_client_registration(body)
        logger.info("dcr_register", extra={**log_extra, "status": 201})
        return JSONResponse(response, status_code=201)
    except DCRError as e:
        logger.info("dcr_register", extra={**log_extra, "status": 400, "error_code": e.error_code})
        return JSONResponse(
            {"error": e.error_code, "error_description": str(e)},
            status_code=400,
        )
