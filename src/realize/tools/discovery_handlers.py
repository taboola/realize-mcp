"""Discovery handlers for account-scoped catalogs that feed campaign payloads.

Five tools surface IDs / names the LLM otherwise has to source from the Realize UI:
- search_audiences           → my_audiences.collection[].collection
- search_lookalike_audiences → lookalike_audience.collection[].collection[].rule_id
- search_contextual_segments → contextual_segments.collection[].collection
- search_publishers          → publisher_targeting.value (publisher's `account_id`)
- search_conversion_rules    → conversion_rules: [{id}]

All wrap /api/1.0 endpoints. Read-only; no destructive annotations.
"""
import json
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import mcp.types as types

from realize.client import client
from realize.tools.errors import ToolInputError
from realize.tools.utils import flatten_results, format_discovery_payload, validate_account_id


_COUNTRY_TARGETING_TYPES = ("ALL", "INCLUDE", "EXCLUDE")


def _format_payload(label: str, label_value: str, values: Any) -> List[types.TextContent]:
    return [
        types.TextContent(type="text", text=format_discovery_payload(label, label_value, values))
    ]


def _require_account_id(args: Dict[str, Any]) -> str:
    account_id = args.get("account_id")
    is_valid, error_message = validate_account_id(account_id)
    if not is_valid:
        raise ToolInputError(error_message)
    return account_id


async def search_audiences(arguments: dict = None) -> List[types.TextContent]:
    """List first-party + custom audiences for an account.

    Endpoint: GET /api/1.0/{accountId}/my_audiences_unified
    Optional filters: country_codes (comma-separated ISO-2), country_targeting_type.
    Result IDs feed my_audiences.collection[].collection on create_campaign / update_campaign.
    """
    args = arguments or {}
    account_id = _require_account_id(args)

    params: Dict[str, Any] = {}
    country_codes = args.get("country_codes")
    if country_codes:
        params["countryCodes"] = country_codes
    country_targeting_type = args.get("country_targeting_type")
    if country_targeting_type is not None:
        if country_targeting_type not in _COUNTRY_TARGETING_TYPES:
            raise ToolInputError(
                f"country_targeting_type must be one of: {', '.join(_COUNTRY_TARGETING_TYPES)}"
            )
        params["countryTargetingType"] = country_targeting_type

    response = await client.get(
        f"/{quote(account_id, safe='')}/my_audiences_unified",
        params=params or None,
    )
    return _format_payload("account_id", account_id, flatten_results(response))


async def search_lookalike_audiences(arguments: dict = None) -> List[types.TextContent]:
    """List lookalike audiences (CRM/pixel/PBP) available for targeting.

    Endpoint: GET /api/1.0/{accountId}/dictionary/lookalike_audiences[/{countryCode}]
    Optional filter: country_code (ISO-2). Path-variant used when supplied.
    Result rule_ids feed lookalike_audience.collection[].collection[].rule_id.
    """
    args = arguments or {}
    account_id = _require_account_id(args)

    country_code: Optional[str] = args.get("country_code")

    encoded_account = quote(account_id, safe="")
    if country_code:
        endpoint = f"/{encoded_account}/dictionary/lookalike_audiences/{quote(country_code, safe='')}"
    else:
        endpoint = f"/{encoded_account}/dictionary/lookalike_audiences"

    response = await client.get(endpoint)
    return _format_payload("account_id", account_id, flatten_results(response))


_PUBLISHER_FIELDS = ("id", "name", "account_id", "country", "is_active")


def _trim_publisher(entry: Any) -> Any:
    if not isinstance(entry, dict):
        return entry
    return {k: entry[k] for k in _PUBLISHER_FIELDS if k in entry}


async def search_publishers(arguments: dict = None) -> List[types.TextContent]:
    """List publishers an account is allowed to target.

    Endpoint: GET /api/1.0/{accountId}/allowed-publishers
    The publisher's `account_id` feeds publisher_targeting.value and
    publisher_bid_modifier.values[].target on create_campaign / update_campaign;
    the upstream API does not resolve display names.
    """
    args = arguments or {}
    account_id = _require_account_id(args)

    query = args.get("query")
    if not isinstance(query, str) or not query.strip():
        raise ToolInputError("query is required (use '*' to list all)")
    cleaned_query = query.strip()

    params: Dict[str, Any] = {}
    if cleaned_query != "*":
        params["search_text"] = cleaned_query

    publisher_ids = args.get("publisher_ids")
    if publisher_ids:
        if isinstance(publisher_ids, list):
            params["publisher_ids"] = ",".join(str(p) for p in publisher_ids)
        else:
            params["publisher_ids"] = str(publisher_ids)

    page = args.get("page", 1)
    page_size = min(int(args.get("page_size", 10)), 50)
    params["page"] = int(page)
    params["page_size"] = page_size

    response = await client.get(
        f"/{quote(account_id, safe='')}/allowed-publishers",
        params=params,
    )
    return _render_search_publishers(account_id, params["page"], page_size, response)


def _render_search_publishers(
    account_id: str,
    page: int,
    page_size: int,
    response: Any,
) -> List[types.TextContent]:
    flattened = flatten_results(response)
    trimmed = [_trim_publisher(e) for e in flattened] if isinstance(flattened, list) else flattened

    if not isinstance(trimmed, list) or not trimmed:
        text = (
            f"No publishers found on account {account_id!r}.\n\n"
            f"Raw response:\n{json.dumps(response, indent=2, ensure_ascii=False)}"
        )
        return [types.TextContent(type="text", text=text)]

    metadata = response.get("metadata", {}) if isinstance(response, dict) else {}
    total = metadata.get("total", len(trimmed))

    lines = [
        f"Publisher search results — page {page}, page_size {page_size}, total {total}",
        "",
        "Resolved publisher account_ids (use these in publisher_targeting.value "
        "and publisher_bid_modifier.values[].target):",
    ]
    for i, entry in enumerate(trimmed, 1):
        if not isinstance(entry, dict):
            lines.append(f"  {i}. {entry!r}")
            continue
        publisher_account_id = entry.get("account_id", "<missing>")
        name = entry.get("name", "Unknown")
        country = entry.get("country")
        is_active = entry.get("is_active")
        meta_parts = []
        if country:
            meta_parts.append(country)
        if is_active is not None:
            meta_parts.append("active" if is_active else "inactive")
        meta = f" [{' · '.join(meta_parts)}]" if meta_parts else ""
        lines.append(f"  {i}. account_id={publisher_account_id!r} ({name}){meta}")
    lines.append("")
    lines.append("Full response:")
    lines.append(format_discovery_payload("account_id", account_id, trimmed))

    return [types.TextContent(type="text", text="\n".join(lines))]


_CONTEXTUAL_SEGMENT_FIELDS = ("id", "label", "provider", "taxonomy", "isActive", "isTargetable")


def _trim_contextual_segment(entry: Any) -> Any:
    if not isinstance(entry, dict):
        return entry
    return {k: entry[k] for k in _CONTEXTUAL_SEGMENT_FIELDS if k in entry}


async def search_contextual_segments(arguments: dict = None) -> List[types.TextContent]:
    """List contextual segments available for targeting.

    Endpoint: GET /api/1.0/{accountId}/dictionary/contextual_segments
    Optional filters: country_codes (comma-separated ISO-2), country_targeting_type.
    Result IDs feed contextual_segments.collection[].collection on create_campaign / update_campaign.
    """
    args = arguments or {}
    account_id = _require_account_id(args)

    params: Dict[str, Any] = {}
    country_codes = args.get("country_codes")
    if country_codes:
        params["countryCodes"] = country_codes
    country_targeting_type = args.get("country_targeting_type")
    if country_targeting_type is not None:
        if country_targeting_type not in _COUNTRY_TARGETING_TYPES:
            raise ToolInputError(
                f"country_targeting_type must be one of: {', '.join(_COUNTRY_TARGETING_TYPES)}"
            )
        params["countryTargetingType"] = country_targeting_type

    response = await client.get(
        f"/{quote(account_id, safe='')}/dictionary/contextual_segments",
        params=params or None,
    )
    flattened = flatten_results(response)
    if isinstance(flattened, list):
        flattened = [_trim_contextual_segment(e) for e in flattened]
    return _format_payload("account_id", account_id, flattened)


async def search_conversion_rules(arguments: dict = None) -> List[types.TextContent]:
    """List conversion rules attached to an account.

    Endpoint: GET /api/1.0/{accountId}/universal_pixel/conversion_rule
    Result IDs feed conversion_rules: [{id}] on create_campaign / update_campaign.
    """
    args = arguments or {}
    account_id = _require_account_id(args)

    response = await client.get(f"/{quote(account_id, safe='')}/universal_pixel/conversion_rule")
    return _format_payload("account_id", account_id, flatten_results(response))
