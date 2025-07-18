"""Authentication tool handlers."""
import logging
from typing import List
import json
import mcp.types as types
from realize.auth import auth

logger = logging.getLogger(__name__)


async def get_auth_token() -> List[types.TextContent]:
    """Get authentication token."""
    try:
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