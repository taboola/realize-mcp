"""Campaign handlers for Realize MCP server.

Two write tools — `create_campaign` and `update_campaign` — accept full campaign
state inline (scalars + targeting). Backstage partitions targeting between the
main campaign endpoint and three sub-resource endpoints; the handlers fan out
internally so the LLM completes a campaign in one tool call.
"""
import json
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

import httpx
import mcp.types as types

from realize.client import client
from realize.tools.audiences import validate_lookalike_audience, validate_my_audiences
from realize.tools.contextual_segments import validate_contextual_segments
from realize.tools.conversion_rules import (
    to_wire_conversion_rules,
    validate_conversion_rules,
)
from realize.tools.errors import ToolInputError
from realize.tools.geo import (
    geo_classic_wire_field,
    to_wire_geo_advanced,
    validate_geo_advanced,
    validate_geo_classic,
)
from realize.tools.publishers import (
    to_wire_publisher_bid_modifier,
    validate_publisher_bid_modifier,
    validate_publisher_groups_targeting,
    validate_publisher_targeting,
)
from realize.tools.schedule import to_wire_schedule, validate_schedule
from realize.tools.techno import (
    techno_wire_field,
    to_wire_techno_value,
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

_CLASSIC_GEO_DIMENSIONS = ("country", "region", "dma", "city", "postal_code")
_CLASSIC_GEO_ARG_KEYS = tuple(f"{d}_targeting" for d in _CLASSIC_GEO_DIMENSIONS)

_TECHNO_DIMENSIONS = ("platform", "os", "browser", "connection_type")

# Sub-resource endpoints: (mcp_arg_key, endpoint_suffix, validator).
# All three are full-replace; body is the validated input verbatim.
_SUB_RESOURCES: Tuple[Tuple[str, str, Any], ...] = (
    ("my_audiences", "my_audiences", validate_my_audiences),
    ("lookalike_audience", "lookalike_audience", validate_lookalike_audience),
    ("contextual_segments", "contextual_segments", validate_contextual_segments),
)


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


async def list_campaign_items(arguments: dict = None) -> List[types.TextContent]:
    """List all items for a campaign (read-only)."""
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


def _check_geo_mutex(args: Dict[str, Any]) -> None:
    """Reject mixing advanced geo_targeting with any classic dimension field."""
    has_advanced = args.get("geo_targeting") is not None
    classic_present = [k for k in _CLASSIC_GEO_ARG_KEYS if args.get(k) is not None]
    if has_advanced and classic_present:
        raise ToolInputError(
            "send geo_targeting (advanced) OR classic geo fields "
            f"({', '.join(_CLASSIC_GEO_ARG_KEYS)}), not both"
        )


def _reject_classic_geo_on_create(args: Dict[str, Any]) -> None:
    """create_campaign accepts advanced geo_targeting only."""
    classic_present = [k for k in _CLASSIC_GEO_ARG_KEYS if args.get(k) is not None]
    if classic_present:
        raise ToolInputError(
            "create_campaign accepts geo_targeting (advanced) only; classic geo fields "
            f"({', '.join(classic_present)}) not allowed on create. Use update_campaign for classic geo edits."
        )


def _build_main_payload(args: Dict[str, Any], *, is_create: bool) -> Dict[str, Any]:
    """Validate and assemble the main-endpoint POST body.

    Includes scalars + main-endpoint targeting (geo, techno, schedule,
    conversion_rules, publishers). Classic geo dimensions accepted on update only.
    Raises ToolInputError on the first invalid block.
    """
    body: Dict[str, Any] = {}

    for f in _SCALAR_BODY_FIELDS:
        if args.get(f) is not None:
            body[f] = args[f]

    geo = args.get("geo_targeting")
    if geo is not None:
        validate_geo_advanced(geo)
        body["geo_targeting"] = to_wire_geo_advanced(geo)

    if not is_create:
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
            "value": to_wire_techno_value(dim, block["value"]),
        }

    schedule = args.get("activity_schedule")
    if schedule is not None:
        validate_schedule(schedule)
        body["activity_schedule"] = to_wire_schedule(schedule)

    conversion_rules = args.get("conversion_rules")
    if conversion_rules is not None:
        validate_conversion_rules(conversion_rules)
        body["conversion_rules"] = to_wire_conversion_rules(conversion_rules)

    publisher_targeting = args.get("publisher_targeting")
    if publisher_targeting is not None:
        validate_publisher_targeting(publisher_targeting)
        body["publisher_targeting"] = {
            "type": publisher_targeting["type"],
            "value": publisher_targeting["value"],
        }

    publisher_groups_targeting = args.get("publisher_groups_targeting")
    if publisher_groups_targeting is not None:
        validate_publisher_groups_targeting(publisher_groups_targeting)
        body["publisher_groups_targeting"] = {
            "type": publisher_groups_targeting["type"],
            "value": publisher_groups_targeting["value"],
        }

    publisher_bid_modifier = args.get("publisher_bid_modifier")
    if publisher_bid_modifier is not None:
        validate_publisher_bid_modifier(publisher_bid_modifier)
        body["publisher_bid_modifier"] = to_wire_publisher_bid_modifier(publisher_bid_modifier)

    return body


def _validate_and_collect_sub_payloads(args: Dict[str, Any]) -> List[Tuple[str, Any]]:
    """Validate sub-resource blocks and return [(endpoint_suffix, body)].

    Each is full-replace; body is the validated input verbatim.
    """
    out: List[Tuple[str, Any]] = []
    for arg_key, suffix, validator in _SUB_RESOURCES:
        value = args.get(arg_key)
        if value is None:
            continue
        validator(value)
        out.append((suffix, value))
    return out


async def _post_sub_resources(
    account_id: str,
    campaign_id: str,
    sub_payloads: List[Tuple[str, Any]],
) -> List[Dict[str, Any]]:
    """POST each sub-resource. Collect failures; do not short-circuit."""
    partial_failures: List[Dict[str, Any]] = []
    encoded_account = quote(account_id, safe="")
    encoded_campaign = quote(str(campaign_id), safe="")

    for suffix, body in sub_payloads:
        endpoint = f"/{encoded_account}/campaigns/{encoded_campaign}/targeting/{suffix}"
        try:
            await client.post(endpoint, data=body)
        except httpx.HTTPStatusError as exc:
            partial_failures.append({
                "section": suffix,
                "status_code": exc.response.status_code,
                "error": _safe_error_body(exc.response),
            })
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            partial_failures.append({
                "section": suffix,
                "error": f"{type(exc).__name__}: {exc}",
            })

    return partial_failures


def _safe_error_body(response: httpx.Response) -> Any:
    """Best-effort extract of upstream error body as JSON, falling back to text."""
    try:
        return response.json()
    except ValueError:
        return response.text


def _format_composed_response(
    verb: str,
    account_id: str,
    campaign_id: str,
    final_state: Dict[str, Any],
    partial_failures: List[Dict[str, Any]],
) -> List[types.TextContent]:
    parts = [f"Campaign {campaign_id} {verb} in account {account_id}:"]
    parts.append(format_response(final_state))
    if partial_failures:
        parts.append("")
        parts.append("partial_failures:")
        parts.append(json.dumps(partial_failures, indent=2, ensure_ascii=False))
    return [types.TextContent(type="text", text="\n".join(parts))]


async def create_campaign(arguments: dict = None) -> List[types.TextContent]:
    """Create a campaign, fanning out to targeting sub-resources as needed."""
    args = arguments or {}
    account_id = args.get("account_id")

    is_valid, error_message = validate_account_id(account_id)
    if not is_valid:
        raise ToolInputError(error_message)

    missing = [f for f in _CREATE_CAMPAIGN_REQUIRED if not args.get(f)]
    if missing:
        raise ToolInputError(f"Missing required field(s): {', '.join(missing)}")

    _reject_classic_geo_on_create(args)
    main_payload = _build_main_payload(args, is_create=True)
    sub_payloads = _validate_and_collect_sub_payloads(args)

    response = await client.post(
        f"/{quote(account_id, safe='')}/campaigns",
        data=main_payload,
    )

    if not sub_payloads:
        return [types.TextContent(
            type="text",
            text=f"Campaign created in account {account_id}:\n{format_response(response)}"
        )]

    campaign_id = response.get("id")
    if campaign_id is None:
        raise ValueError("Backstage create response missing 'id'; cannot fan out targeting")

    partial_failures = await _post_sub_resources(account_id, str(campaign_id), sub_payloads)
    final = await client.get(
        f"/{quote(account_id, safe='')}/campaigns/{quote(str(campaign_id), safe='')}"
    )
    return _format_composed_response("created", account_id, str(campaign_id), final, partial_failures)


async def update_campaign(arguments: dict = None) -> List[types.TextContent]:
    """Update an existing campaign, fanning out to targeting sub-resources as needed."""
    args = arguments or {}
    account_id = args.get("account_id")
    campaign_id = args.get("campaign_id")

    is_valid, error_message = validate_account_id(account_id)
    if not is_valid:
        raise ToolInputError(error_message)

    if not campaign_id:
        raise ToolInputError("campaign_id is required")

    _check_geo_mutex(args)
    main_payload = _build_main_payload(args, is_create=False)
    sub_payloads = _validate_and_collect_sub_payloads(args)

    if not main_payload and not sub_payloads:
        raise ToolInputError("at least one updatable field must be supplied")

    encoded_account = quote(account_id, safe="")
    encoded_campaign = quote(str(campaign_id), safe="")

    main_response: Optional[Dict[str, Any]] = None
    if main_payload:
        main_response = await client.post(
            f"/{encoded_account}/campaigns/{encoded_campaign}",
            data=main_payload,
        )

    if not sub_payloads:
        return [types.TextContent(
            type="text",
            text=f"Campaign {campaign_id} updated:\n{format_response(main_response)}"
        )]

    partial_failures = await _post_sub_resources(account_id, campaign_id, sub_payloads)
    final = await client.get(f"/{encoded_account}/campaigns/{encoded_campaign}")
    return _format_composed_response("updated", account_id, campaign_id, final, partial_failures)
