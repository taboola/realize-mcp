"""Account management tool handlers."""
import logging
from typing import List
import json
import mcp.types as types
from realize.client import client

logger = logging.getLogger(__name__)


async def get_user_allowed_accounts() -> List[types.TextContent]:
    """Get accounts accessible to current user."""
    try:
        data = await client.get("/users/current/allowed-accounts")
        
        # Return raw JSON response with all fields
        return [
            types.TextContent(
                type="text",
                text=json.dumps(data, indent=2, ensure_ascii=False)
            )
        ]
    except Exception as e:
        logger.error(f"Failed to get allowed accounts: {e}")
        return [
            types.TextContent(
                type="text",
                text=f"Failed to get allowed accounts: {str(e)}"
            )
        ]


async def get_user_account() -> List[types.TextContent]:
    """Get current user's account information."""
    try:
        account = await client.get("/users/current/account")
        
        # Return raw JSON response with all fields
        return [
            types.TextContent(
                type="text",
                text=json.dumps(account, indent=2, ensure_ascii=False)
            )
        ]
    except Exception as e:
        logger.error(f"Failed to get user account: {e}")
        return [
            types.TextContent(
                type="text",
                text=f"Failed to get user account: {str(e)}"
            )
        ] 