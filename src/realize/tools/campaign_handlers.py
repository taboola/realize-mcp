"""Campaign handlers for Realize MCP server."""
from typing import List
from urllib.parse import quote
import mcp.types as types
from realize.tools.utils import format_response, validate_account_id
from realize.tools.errors import ToolInputError
from realize.tools.geo import (
    geo_classic_wire_field,
    to_wire_geo_advanced,
    validate_geo_advanced,
    validate_geo_classic,
)
from realize.tools.techno import (
    techno_wire_field,
    to_wire_techno_value,
    validate_techno,
)
from realize.tools.audiences import validate_my_audiences
from realize.tools.schedule import to_wire_schedule, validate_schedule
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


async def update_campaign_geo_classic(arguments: dict = None) -> List[types.TextContent]:
    """Update one classic geo dimension on a campaign (write operation)."""
    args = arguments or {}
    account_id = args.get("account_id")
    campaign_id = args.get("campaign_id")
    dimension = args.get("dimension")
    targeting = args.get("targeting")

    is_valid, error_message = validate_account_id(account_id)
    if not is_valid:
        raise ToolInputError(error_message)

    if not campaign_id:
        raise ToolInputError("campaign_id is required")

    validate_geo_classic(dimension, targeting)

    body = {
        geo_classic_wire_field(dimension): {
            "type": targeting["type"],
            "value": targeting["value"],
        }
    }

    response = await client.post(
        f"/{quote(account_id, safe='')}/campaigns/{quote(campaign_id, safe='')}",
        data=body,
    )

    return [types.TextContent(
        type="text",
        text=f"Campaign {campaign_id} geo ({dimension}) updated:\n{format_response(response)}"
    )]


async def update_campaign_geo_advanced(arguments: dict = None) -> List[types.TextContent]:
    """Update advanced (MultiTargeting) geo on a campaign (write operation)."""
    args = arguments or {}
    account_id = args.get("account_id")
    campaign_id = args.get("campaign_id")
    geo_targeting = args.get("geo_targeting")

    is_valid, error_message = validate_account_id(account_id)
    if not is_valid:
        raise ToolInputError(error_message)

    if not campaign_id:
        raise ToolInputError("campaign_id is required")

    validate_geo_advanced(geo_targeting)

    body = {"geoTargeting": to_wire_geo_advanced(geo_targeting)}

    response = await client.post(
        f"/{quote(account_id, safe='')}/campaigns/{quote(campaign_id, safe='')}",
        data=body,
    )

    return [types.TextContent(
        type="text",
        text=f"Campaign {campaign_id} advanced geo updated:\n{format_response(response)}"
    )]


async def update_campaign_techno(arguments: dict = None) -> List[types.TextContent]:
    """Update one technology targeting dimension on a campaign (write operation)."""
    args = arguments or {}
    account_id = args.get("account_id")
    campaign_id = args.get("campaign_id")
    dimension = args.get("dimension")
    targeting = args.get("targeting")

    is_valid, error_message = validate_account_id(account_id)
    if not is_valid:
        raise ToolInputError(error_message)

    if not campaign_id:
        raise ToolInputError("campaign_id is required")

    validate_techno(dimension, targeting)

    body = {
        techno_wire_field(dimension): {
            "type": targeting["type"],
            "value": to_wire_techno_value(dimension, targeting["value"]),
        }
    }

    response = await client.post(
        f"/{quote(account_id, safe='')}/campaigns/{quote(campaign_id, safe='')}",
        data=body,
    )

    return [types.TextContent(
        type="text",
        text=f"Campaign {campaign_id} techno ({dimension}) updated:\n{format_response(response)}"
    )]


async def update_campaign_my_audiences(arguments: dict = None) -> List[types.TextContent]:
    """Update first-party + custom audience targeting on a campaign (write operation)."""
    args = arguments or {}
    account_id = args.get("account_id")
    campaign_id = args.get("campaign_id")
    targeting = args.get("targeting")

    is_valid, error_message = validate_account_id(account_id)
    if not is_valid:
        raise ToolInputError(error_message)

    if not campaign_id:
        raise ToolInputError("campaign_id is required")

    validate_my_audiences(targeting)

    response = await client.post(
        f"/{quote(account_id, safe='')}/campaigns/{quote(campaign_id, safe='')}/targeting/my_audiences",
        data=targeting,
    )

    return [types.TextContent(
        type="text",
        text=f"Campaign {campaign_id} my_audiences targeting updated:\n{format_response(response)}"
    )]


async def update_campaign_schedule(arguments: dict = None) -> List[types.TextContent]:
    """Update a campaign's activity schedule (dayparting) (write operation)."""
    args = arguments or {}
    account_id = args.get("account_id")
    campaign_id = args.get("campaign_id")
    schedule = args.get("schedule")

    is_valid, error_message = validate_account_id(account_id)
    if not is_valid:
        raise ToolInputError(error_message)

    if not campaign_id:
        raise ToolInputError("campaign_id is required")

    validate_schedule(schedule)

    body = {"activitySchedule": to_wire_schedule(schedule)}

    response = await client.post(
        f"/{quote(account_id, safe='')}/campaigns/{quote(campaign_id, safe='')}",
        data=body,
    )

    return [types.TextContent(
        type="text",
        text=f"Campaign {campaign_id} activity schedule updated:\n{format_response(response)}"
    )]
