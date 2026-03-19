"""Authentication tool handlers."""
from typing import List
import json
import mcp.types as types
from realize.http import create_http_client
from realize.auth import auth
from realize.config import config
from realize.tools.errors import ToolInputError


async def get_auth_token() -> List[types.TextContent]:
    """Get authentication token."""
    if config.mcp_transport == "sse":
        from realize.oauth.context import get_session_token
        token = get_session_token()
        if token:
            return [
                types.TextContent(
                    type="text",
                    text="Already authenticated via OAuth 2.1. Your Bearer token is active and being used for API requests."
                )
            ]
        raise ToolInputError("No active session token. Please reconnect via the SSE OAuth flow.")

    token = await auth.get_auth_token()
    return [
        types.TextContent(
            type="text",
            text=f"Successfully authenticated. Token expires in {token.expires_in} seconds."
        )
    ]


async def get_token_details() -> List[types.TextContent]:
    """Get token details."""
    if config.mcp_transport == "sse":
        from realize.oauth.context import get_session_token
        token = get_session_token()
        if not token:
            raise ToolInputError("No active session token. Please reconnect via the SSE OAuth flow.")
        url = f"{config.realize_base_url}/api/1.0/token-details"
        headers = {"Authorization": f"Bearer {token}"}
        async with create_http_client() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            details = response.json()
        return [
            types.TextContent(
                type="text",
                text=json.dumps(details, indent=2, ensure_ascii=False)
            )
        ]

    details = await auth.get_token_details()

    return [
        types.TextContent(
            type="text",
            text=json.dumps(details, indent=2, ensure_ascii=False)
        )
    ]
