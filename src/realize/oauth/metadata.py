"""OAuth metadata endpoints for RFC 8414 and RFC 9728."""
import logging

import httpx

from ..config import config
from ..http import create_http_client

logger = logging.getLogger(__name__)


def get_protected_resource_metadata(base_url: str) -> dict:
    """Generate RFC 9728 Protected Resource Metadata.

    This describes the MCP server as a protected resource,
    indicating which authorization servers it trusts.

    Args:
        base_url: Public-facing base URL of this MCP server

    Returns:
        dict: Protected resource metadata per RFC 9728
    """
    return {
        "resource": f"{base_url}/mcp",
        "authorization_servers": [base_url],
        "bearer_methods_supported": ["header"],
        "scopes_supported": config.oauth_scopes.split(),
        "resource_documentation": "https://github.com/taboola/realize-mcp",
    }


async def proxy_authorization_server_metadata(base_url: str) -> dict:
    """Proxy and modify upstream Authorization Server Metadata (RFC 8414).

    Proxies upstream AS metadata. Rewrites `issuer` (RFC 8414 §3.3) and
    `registration_endpoint` (upstream lacks RFC 7591 DCR — routes to our
    fake). Other fields pass through.

    Args:
        base_url: Public-facing base URL of this MCP server

    Returns:
        dict: Authorization server metadata per RFC 8414

    Raises:
        httpx.HTTPError: If upstream request fails
    """
    async with create_http_client() as client:
        url = f"{config.oauth_server_url}/.well-known/oauth-authorization-server"
        response = await client.get(url, timeout=10.0)
        response.raise_for_status()
        metadata = response.json()

    # Override issuer to match this server's URL (RFC 8414 Section 3.3 requires
    # issuer to match the URL the client used to fetch this metadata)
    metadata["issuer"] = base_url

    # Override registration_endpoint (upstream doesn't support RFC 7591)
    metadata["registration_endpoint"] = f"{base_url}/register"

    logger.debug("Returning modified OAuth AS metadata")
    return metadata
