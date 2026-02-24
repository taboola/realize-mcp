"""Authentication tool handlers."""
import logging
from typing import List
import json
import httpx
import mcp.types as types
from realize.auth import auth
from realize.config import config

logger = logging.getLogger(__name__)


async def get_auth_token() -> List[types.TextContent]:
    """Get authentication token."""
    try:
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
            return [
                types.TextContent(
                    type="text",
                    text="No active session token. Please reconnect via the SSE OAuth flow."
                )
            ]

        token = await auth.get_auth_token()
        return [
            types.TextContent(
                type="text",
                text=f"Successfully authenticated. Token expires in {token.expires_in} seconds."
            )
        ]
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        return [
            types.TextContent(
                type="text",
                text=f"Authentication failed: {str(e)}"
            )
        ]


async def get_token_details() -> List[types.TextContent]:
    """Get token details."""
    try:
        if config.mcp_transport == "sse":
            from realize.oauth.context import get_session_token
            token = get_session_token()
            if not token:
                return [
                    types.TextContent(
                        type="text",
                        text="No active session token. Please reconnect via the SSE OAuth flow."
                    )
                ]
            url = f"{config.realize_base_url}/api/1.0/token-details"
            headers = {"Authorization": f"Bearer {token}"}
            async with httpx.AsyncClient() as client:
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

        # Return raw JSON response - no special formatting or field mappings
        return [
            types.TextContent(
                type="text",
                text=json.dumps(details, indent=2, ensure_ascii=False)
            )
        ]
    except Exception as e:
        logger.error(f"Failed to get token details: {e}")
        return [
            types.TextContent(
                type="text",
                text=f"Failed to get token details: {str(e)}"
            )
        ] 