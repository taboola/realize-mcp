"""OAuth metadata endpoints for RFC 8414 and RFC 9728."""
import logging

import httpx

from ..config import config

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
        "resource": base_url,
        "authorization_servers": [base_url],
        "bearer_methods_supported": ["header"],
        "scopes_supported": config.oauth_scopes.split(),
        "resource_documentation": "https://github.com/taboola/realize-mcp",
    }


async def proxy_authorization_server_metadata(base_url: str) -> dict:
    """Proxy and modify upstream Authorization Server Metadata (RFC 8414).

    Fetches metadata from the upstream authorization server, then modifies it
    to route client registration through the MCP server. The upstream auth
    server doesn't support RFC 7591 Dynamic Client Registration, so we
    override registration_endpoint to point to our fake DCR endpoint.

    Args:
        base_url: Public-facing base URL of this MCP server

    Returns:
        dict: Authorization server metadata per RFC 8414

    Raises:
        httpx.HTTPError: If upstream request fails
    """
    async with httpx.AsyncClient() as client:
        url = f"{config.oauth_server_url}/.well-known/oauth-authorization-server"
        response = await client.get(url, timeout=10.0)
        response.raise_for_status()
        metadata = response.json()

    # Remove "none" from token_endpoint_auth_methods_supported
    # to force Claude Desktop to use client_secret_post and send client_id
    if "token_endpoint_auth_methods_supported" in metadata:
        methods = metadata["token_endpoint_auth_methods_supported"]
        metadata["token_endpoint_auth_methods_supported"] = [
            m for m in methods if m != "none"
        ]

    # Only override registration_endpoint (upstream doesn't support RFC 7591)
    metadata["registration_endpoint"] = f"{base_url}/register"

    logger.debug("Returning modified OAuth AS metadata")
    return metadata