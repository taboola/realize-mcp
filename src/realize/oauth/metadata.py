"""OAuth metadata endpoints for RFC 8414 and RFC 9728."""
import logging

import httpx

from ..config import config

logger = logging.getLogger(__name__)


def get_protected_resource_metadata() -> dict:
    """Generate RFC 9728 Protected Resource Metadata.

    This describes the MCP server as a protected resource,
    indicating which authorization servers it trusts.

    Returns:
        dict: Protected resource metadata per RFC 9728
    """
    return {
        "resource": config.mcp_server_url,
        # Point to MCP server so clients fetch our modified AS metadata
        # (which routes /register, /token, /authorize through our proxy)
        "authorization_servers": [config.mcp_server_url],
        "bearer_methods_supported": ["header"],
        "scopes_supported": config.oauth_scopes.split(),
        "resource_documentation": "https://github.com/taboola/realize-mcp",
    }


async def proxy_authorization_server_metadata() -> dict:
    """Proxy and modify upstream Authorization Server Metadata (RFC 8414).

    Fetches metadata from the upstream authorization server, then modifies it
    to route client registration and token requests through the MCP server.
    This is necessary because Claude Desktop/Claude.ai may not be able to reach
    internal authorization servers directly.

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

    # Route endpoints through MCP server's HTTPS URL (ngrok)
    # This is needed because:
    # - MCP clients can't reach internal auth server for /register and /token
    # - Some MCP clients (e.g., Cursor) refuse to open HTTP authorization URLs
    #   so we proxy /authorize through HTTPS, which redirects browser to upstream
    metadata["registration_endpoint"] = f"{config.mcp_server_url}/register"
    metadata["token_endpoint"] = f"{config.mcp_server_url}/oauth/token"
    metadata["authorization_endpoint"] = f"{config.mcp_server_url}/authorize"

    logger.debug("Returning modified OAuth AS metadata")
    return metadata
