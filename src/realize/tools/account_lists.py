"""Per-account list handlers — discover IDs/names to pass to write tools.

Each handler wraps an existing publisher-console list endpoint, returns the raw
response as JSON so the LLM can pick IDs (audience, conversion rule, segment,
publisher) for use in update_campaign_* write tools.
"""
import json
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import mcp.types as types

from realize.client import client
from realize.tools.errors import ToolInputError
from realize.tools.utils import validate_account_id


def _validate_required(args: Optional[dict]) -> str:
    """Common account_id validation; returns the validated id."""
    args = args or {}
    account_id = args.get("account_id")
    is_valid, error_message = validate_account_id(account_id)
    if not is_valid:
        raise ToolInputError(error_message)
    return account_id


def _format(label: str, payload: Any) -> List[types.TextContent]:
    return [
        types.TextContent(
            type="text",
            text=f"{label}\n{json.dumps(payload, ensure_ascii=False, indent=2)}",
        )
    ]


async def list_account_audiences(arguments: dict = None) -> List[types.TextContent]:
    """List first-party + custom + lookalike audiences on an account.

    Wraps GET /api/1.0/{accountId}/my_audiences_unified — the unified endpoint
    that returns custom audiences and lookalikes together. Pass the resulting
    audience IDs to update_campaign_my_audiences (custom) or
    update_campaign_lookalike_audience (lookalike rule_ids).
    """
    account_id = _validate_required(arguments)
    response = await client.get(f"/{quote(account_id, safe='')}/my_audiences_unified")
    return _format(f"Audiences for account {account_id}:", response)


async def list_account_conversion_rules(arguments: dict = None) -> List[types.TextContent]:
    """List conversion rules defined on an account.

    Wraps GET /api/1.0/{accountId}/universal_pixel/conversion_rule. Pass the
    resulting rule IDs to update_campaign_conversion_rules.
    """
    account_id = _validate_required(arguments)
    response = await client.get(
        f"/{quote(account_id, safe='')}/universal_pixel/conversion_rule"
    )
    return _format(f"Conversion rules for account {account_id}:", response)


async def list_account_publishers(arguments: dict = None) -> List[types.TextContent]:
    """List publishers an account is allowed to target.

    Wraps GET /api/1.0/{accountId}/allowed-publishers. Optional `search_text`
    narrows the list (useful when an account has thousands of allowed publishers).
    Pass the resulting publisher names to update_campaign_publishers
    (publisher_targeting / publisher_bid_modifier values).
    """
    args = arguments or {}
    account_id = _validate_required(args)
    params: Dict[str, str] = {}
    search_text = args.get("search_text")
    if search_text:
        if not isinstance(search_text, str):
            raise ToolInputError("search_text must be a string")
        params["search_text"] = search_text
    response = await client.get(
        f"/{quote(account_id, safe='')}/allowed-publishers",
        params=params or None,
    )
    return _format(f"Allowed publishers for account {account_id}:", response)


async def list_account_contextual_segments(arguments: dict = None) -> List[types.TextContent]:
    """List contextual segments available for targeting on an account.

    Wraps GET /api/1.0/{accountId}/dictionary/contextual_segments. Optional
    `country_codes` (comma-separated) narrows segments to those available in the
    given markets. Pass the resulting segment IDs to
    update_campaign_contextual_segments.
    """
    args = arguments or {}
    account_id = _validate_required(args)
    params: Dict[str, str] = {}
    country_codes = args.get("country_codes")
    if country_codes:
        if not isinstance(country_codes, str):
            raise ToolInputError("country_codes must be a comma-separated string")
        params["countryCodes"] = country_codes
    response = await client.get(
        f"/{quote(account_id, safe='')}/dictionary/contextual_segments",
        params=params or None,
    )
    return _format(f"Contextual segments for account {account_id}:", response)
