"""Campaign handlers for Realize MCP server."""
from typing import List
from urllib.parse import quote
import mcp.types as types
from realize.tools.utils import format_response, validate_account_id
from realize.tools.errors import ToolInputError
from realize.client import client


async def get_all_campaigns(arguments: dict = None) -> List[types.TextContent]:
    """Get all campaigns for an account (read-only)."""
    account_id = arguments.get("account_id") if arguments else None

    is_valid, error_message = validate_account_id(account_id)
    if not is_valid:
        raise ToolInputError(error_message)

    response = await client.get(f"/{quote(account_id, safe='')}/campaigns")

    return [types.TextContent(
        type="text",
        text=f"Campaigns for account {account_id}:\n{format_response(response)}"
    )]


async def get_campaign(arguments: dict = None) -> List[types.TextContent]:
    """Get specific campaign details (read-only)."""
    account_id = arguments.get("account_id") if arguments else None
    campaign_id = arguments.get("campaign_id") if arguments else None

    is_valid, error_message = validate_account_id(account_id)
    if not is_valid:
        raise ToolInputError(error_message)

    if not campaign_id:
        raise ToolInputError("campaign_id is required")

    response = await client.get(f"/{quote(account_id, safe='')}/campaigns/{quote(campaign_id, safe='')}")

    return [types.TextContent(
        type="text",
        text=f"Campaign {campaign_id} details:\n{format_response(response)}"
    )]


async def get_campaign_items(arguments: dict = None) -> List[types.TextContent]:
    """Get all items for a campaign (read-only)."""
    account_id = arguments.get("account_id") if arguments else None
    campaign_id = arguments.get("campaign_id") if arguments else None

    is_valid, error_message = validate_account_id(account_id)
    if not is_valid:
        raise ToolInputError(error_message)

    if not campaign_id:
        raise ToolInputError("campaign_id is required")

    response = await client.get(f"/{quote(account_id, safe='')}/campaigns/{quote(campaign_id, safe='')}/items/")

    return [types.TextContent(
        type="text",
        text=f"Campaign items for campaign {campaign_id}:\n{format_response(response)}"
    )]


async def get_campaign_item(arguments: dict = None) -> List[types.TextContent]:
    """Get specific campaign item details (read-only)."""
    account_id = arguments.get("account_id") if arguments else None
    campaign_id = arguments.get("campaign_id") if arguments else None
    item_id = arguments.get("item_id") if arguments else None

    is_valid, error_message = validate_account_id(account_id)
    if not is_valid:
        raise ToolInputError(error_message)

    if not campaign_id or not item_id:
        raise ToolInputError("campaign_id and item_id are both required")

    response = await client.get(f"/{quote(account_id, safe='')}/campaigns/{quote(campaign_id, safe='')}/items/{quote(item_id, safe='')}")

    return [types.TextContent(
        type="text",
        text=f"Campaign item {item_id} details:\n{format_response(response)}"
    )]


_CREATE_CAMPAIGN_REQUIRED = ("name", "marketing_objective", "branding_text", "spending_limit_model")
_CREATE_CAMPAIGN_BODY_FIELDS = (
    "name", "marketing_objective", "branding_text", "spending_limit_model",
    "spending_limit", "daily_cap", "cpc", "bid_strategy", "target_cpa",
    "start_date", "end_date", "tracking_code", "cpc_cap", "comments",
)


async def create_campaign(arguments: dict = None) -> List[types.TextContent]:
    """Create a single campaign (write operation)."""
    args = arguments or {}
    account_id = args.get("account_id")

    is_valid, error_message = validate_account_id(account_id)
    if not is_valid:
        raise ToolInputError(error_message)

    missing = [f for f in _CREATE_CAMPAIGN_REQUIRED if not args.get(f)]
    if missing:
        raise ToolInputError(f"Missing required field(s): {', '.join(missing)}")

    body = {f: args[f] for f in _CREATE_CAMPAIGN_BODY_FIELDS if args.get(f) is not None}

    response = await client.post(
        f"/{quote(account_id, safe='')}/campaigns",
        data=body,
    )

    return [types.TextContent(
        type="text",
        text=f"Campaign created in account {account_id}:\n{format_response(response)}"
    )]
