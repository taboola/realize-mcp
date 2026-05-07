"""Type-agnostic item read handlers for Realize MCP server.

`list_items` and `get_item` return whatever items live on a campaign —
native, display, or any other supported type — without filtering. Write
handlers split by type live in `item_native_handlers` and
`item_display_handlers`.
"""
from typing import List
from urllib.parse import quote

import mcp.types as types

from realize.client import client
from realize.tools.errors import ToolInputError
from realize.tools.utils import format_response, validate_account_id


async def list_items(arguments: dict = None) -> List[types.TextContent]:
    """List all items for a campaign (read-only)."""
    account_id = arguments.get("account_id") if arguments else None
    campaign_id = arguments.get("campaign_id") if arguments else None

    is_valid, error_message = validate_account_id(account_id)
    if not is_valid:
        raise ToolInputError(error_message)

    if not campaign_id:
        raise ToolInputError("campaign_id is required")

    response = await client.get(
        f"/{quote(account_id, safe='')}/campaigns/{quote(campaign_id, safe='')}/items"
    )

    return [types.TextContent(
        type="text",
        text=f"Campaign items for campaign {campaign_id}:\n{format_response(response)}",
    )]


async def get_item(arguments: dict = None) -> List[types.TextContent]:
    """Get specific campaign item details (read-only)."""
    account_id = arguments.get("account_id") if arguments else None
    campaign_id = arguments.get("campaign_id") if arguments else None
    item_id = arguments.get("item_id") if arguments else None

    is_valid, error_message = validate_account_id(account_id)
    if not is_valid:
        raise ToolInputError(error_message)

    if not campaign_id or not item_id:
        raise ToolInputError("campaign_id and item_id are both required")

    response = await client.get(
        f"/{quote(account_id, safe='')}/campaigns/{quote(campaign_id, safe='')}"
        f"/items/{quote(item_id, safe='')}"
    )

    return [types.TextContent(
        type="text",
        text=f"Campaign item {item_id} details:\n{format_response(response)}",
    )]
