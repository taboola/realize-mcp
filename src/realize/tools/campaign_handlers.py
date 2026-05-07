"""Campaign handlers for Realize MCP server.

Read tools (`list_campaigns`, `get_campaign`) plus two write tools —
`create_campaign` and `update_campaign` — that accept full campaign state inline
(scalars + targeting). All targeting fields ride in a single atomic POST to the
APICampaign endpoint; one tool call → one HTTP request.

Item-level handlers live in `item_handlers`.
"""
from typing import Any, Dict, List
from urllib.parse import quote

import mcp.types as types

from realize.client import client
from realize.tools.audiences import (
    sanitize_lookalike_audience,
    sanitize_my_audiences,
    validate_lookalike_audience,
    validate_my_audiences,
)
from realize.tools.contextual_segments import (
    sanitize_contextual_segments,
    validate_contextual_segments,
)
from realize.tools.conversion_rules import (
    sanitize_conversion_rules,
    validate_conversion_rules,
)
from realize.tools.errors import ToolInputError
from realize.tools.geo import (
    geo_classic_wire_field,
    validate_geo_classic,
)
from realize.tools.publishers import (
    sanitize_publisher_bid_modifier,
    validate_publisher_bid_modifier,
    validate_publisher_targeting,
)
from realize.tools.schedule import sanitize_schedule, validate_schedule
from realize.tools.techno import (
    techno_wire_field,
    sanitize_techno_value,
    validate_techno,
)
from realize.tools.utils import format_response, validate_account_id


_CREATE_CAMPAIGN_REQUIRED = ("name", "marketing_objective", "branding_text", "spending_limit_model")

_SCALAR_BODY_FIELDS = (
    "name", "marketing_objective", "branding_text", "spending_limit_model",
    "spending_limit", "daily_cap", "cpc", "bid_strategy", "cpa_goal",
    "start_date", "end_date", "tracking_code", "cpc_cap", "comments",
    "daily_ad_delivery_model", "traffic_allocation_mode", "is_active",
)

_CLASSIC_GEO_DIMENSIONS = ("country", "region_country", "dma_country", "city", "postal_code")

_TECHNO_DIMENSIONS = ("platform", "os", "browser", "connection_type")


async def list_campaigns(arguments: dict = None) -> List[types.TextContent]:
    """List all campaigns for an account (read-only)."""
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


def _build_main_payload(args: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and assemble the main-endpoint POST body.

    Includes scalars + main-endpoint targeting (geo, techno, schedule,
    conversion_rules, publishers). Classic geo dimensions accepted on both
    create and update. Raises ToolInputError on the first invalid block.
    """
    body: Dict[str, Any] = {}

    for f in _SCALAR_BODY_FIELDS:
        if args.get(f) is not None:
            body[f] = args[f]

    for dim in _CLASSIC_GEO_DIMENSIONS:
        arg_key = f"{dim}_targeting"
        block = args.get(arg_key)
        if block is None:
            continue
        validate_geo_classic(dim, block)
        body[geo_classic_wire_field(dim)] = {
            "type": block["type"],
            "value": block["value"],
        }

    for dim in _TECHNO_DIMENSIONS:
        arg_key = f"{dim}_targeting"
        block = args.get(arg_key)
        if block is None:
            continue
        validate_techno(dim, block)
        body[techno_wire_field(dim)] = {
            "type": block["type"],
            "value": sanitize_techno_value(dim, block["value"]),
        }

    schedule = args.get("activity_schedule")
    if schedule is not None:
        validate_schedule(schedule)
        body["activity_schedule"] = sanitize_schedule(schedule)

    conversion_rules = args.get("conversion_rules")
    if conversion_rules is not None:
        validate_conversion_rules(conversion_rules)
        body["conversion_rules"] = sanitize_conversion_rules(conversion_rules)

    publisher_targeting = args.get("publisher_targeting")
    if publisher_targeting is not None:
        validate_publisher_targeting(publisher_targeting)
        body["publisher_targeting"] = {
            "type": publisher_targeting["type"],
            "value": publisher_targeting["value"],
        }

    publisher_bid_modifier = args.get("publisher_bid_modifier")
    if publisher_bid_modifier is not None:
        validate_publisher_bid_modifier(publisher_bid_modifier)
        body["publisher_bid_modifier"] = sanitize_publisher_bid_modifier(publisher_bid_modifier)

    audiences_targeting = args.get("audiences_targeting")
    if audiences_targeting is not None:
        validate_my_audiences(audiences_targeting)
        body["audiences_targeting"] = sanitize_my_audiences(audiences_targeting)

    lookalike_audience_targeting = args.get("lookalike_audience_targeting")
    if lookalike_audience_targeting is not None:
        validate_lookalike_audience(lookalike_audience_targeting)
        body["lookalike_audience_targeting"] = sanitize_lookalike_audience(lookalike_audience_targeting)

    contextual_segments_targeting = args.get("contextual_segments_targeting")
    if contextual_segments_targeting is not None:
        validate_contextual_segments(contextual_segments_targeting)
        body["contextual_segments_targeting"] = sanitize_contextual_segments(contextual_segments_targeting)

    predefined_premium_site_targeting = args.get("predefined_premium_site_targeting")
    if predefined_premium_site_targeting is not None:
        body["predefined_targeting_options"] = {
            "predefined_premium_site_targeting": predefined_premium_site_targeting,
        }

    return body


async def create_campaign(arguments: dict = None) -> List[types.TextContent]:
    """Create a campaign in one atomic POST including all targeting."""
    args = arguments or {}
    account_id = args.get("account_id")

    is_valid, error_message = validate_account_id(account_id)
    if not is_valid:
        raise ToolInputError(error_message)

    missing = [f for f in _CREATE_CAMPAIGN_REQUIRED if not args.get(f)]
    if missing:
        raise ToolInputError(f"Missing required field(s): {', '.join(missing)}")

    payload = _build_main_payload(args)

    response = await client.post(
        f"/{quote(account_id, safe='')}/campaigns",
        data=payload,
    )

    return [types.TextContent(
        type="text",
        text=f"Campaign created in account {account_id}:\n{format_response(response)}"
    )]


async def update_campaign(arguments: dict = None) -> List[types.TextContent]:
    """Update an existing campaign in one atomic POST including any targeting subset."""
    args = arguments or {}
    account_id = args.get("account_id")
    campaign_id = args.get("campaign_id")

    is_valid, error_message = validate_account_id(account_id)
    if not is_valid:
        raise ToolInputError(error_message)

    if not campaign_id:
        raise ToolInputError("campaign_id is required")

    payload = _build_main_payload(args)

    if not payload:
        raise ToolInputError("at least one updatable field must be supplied")

    response = await client.post(
        f"/{quote(account_id, safe='')}/campaigns/{quote(str(campaign_id), safe='')}",
        data=payload,
    )

    return [types.TextContent(
        type="text",
        text=f"Campaign {campaign_id} updated:\n{format_response(response)}"
    )]
