"""Native item (creative) write handlers for Realize MCP server.

Two native write tools (`create_native_item`, `update_native_item`) covering
URL-crawled creatives directly attached to a campaign. Native `ITEM` type
only — RSS feed items, motion ads / performance video, and hierarchy carousel
are out of scope. Third-party display ads live in `item_display_handlers`.
Type-agnostic read tools (`list_items`, `get_item`) live in `item_read_handlers`.
"""
from typing import Any, Dict, List
from urllib.parse import quote

import mcp.types as types

from realize.client import client
from realize.tools.cta import sanitize_cta, validate_cta
from realize.tools.errors import ToolInputError
from realize.tools.utils import format_response, validate_account_id
from realize.tools.verification_pixel import (
    sanitize_verification_pixel,
    validate_verification_pixel,
)
from realize.tools.viewability_tag import (
    sanitize_viewability_tag,
    validate_viewability_tag,
)


_CREATE_REQUIRED = ("url",)

_CREATE_BODY_FIELDS = (
    "url", "title", "description", "thumbnail_url",
    "branding_text",
)

_UPDATE_BODY_FIELDS = _CREATE_BODY_FIELDS + ("is_active",)


def _build_item_payload(args: Dict[str, Any], *, is_create: bool) -> Dict[str, Any]:
    """Validate and assemble the item-endpoint POST body.

    Skip-None for scalars; per-section validate-then-transform for nested
    objects. Used by both create_native_item and update_native_item.
    The is_create flag gates update-only fields (is_active, verification_pixel,
    viewability_tag) so the create surface stays minimal even if a caller passes them.
    """
    body: Dict[str, Any] = {}

    scalar_fields = _CREATE_BODY_FIELDS if is_create else _UPDATE_BODY_FIELDS
    for f in scalar_fields:
        if args.get(f) is not None:
            body[f] = args[f]

    cta = args.get("cta")
    if cta is not None:
        validate_cta(cta)
        body["cta"] = sanitize_cta(cta)

    if not is_create:
        verification_pixel = args.get("verification_pixel")
        if verification_pixel is not None:
            validate_verification_pixel(verification_pixel)
            body["verification_pixel"] = sanitize_verification_pixel(verification_pixel)

        viewability_tag = args.get("viewability_tag")
        if viewability_tag is not None:
            validate_viewability_tag(viewability_tag)
            body["viewability_tag"] = sanitize_viewability_tag(viewability_tag)

    return body


async def create_native_item(arguments: dict = None) -> List[types.TextContent]:
    """Create a native (`STATIC_IMAGE`) item directly attached to a campaign."""
    args = arguments or {}
    account_id = args.get("account_id")
    campaign_id = args.get("campaign_id")

    is_valid, error_message = validate_account_id(account_id)
    if not is_valid:
        raise ToolInputError(error_message)

    if not campaign_id:
        raise ToolInputError("campaign_id is required")

    missing = [f for f in _CREATE_REQUIRED if not args.get(f)]
    if missing:
        raise ToolInputError(f"Missing required field(s): {', '.join(missing)}")

    payload = _build_item_payload(args, is_create=True)

    # Backstage's single-item POST /items endpoint enforces "url-only" on create
    # (any of title/description/thumbnail_url/is_active triggers 404). The mass
    # endpoint POST /items/mass accepts the full payload via APICollection<APICampaignItem>;
    # we wrap a single-item collection and unwrap results[0] for callers.
    response = await client.post(
        f"/{quote(account_id, safe='')}/campaigns/{quote(campaign_id, safe='')}/items/mass",
        data={"collection": [payload]},
    )
    item = response["results"][0] if isinstance(response, dict) and response.get("results") else response

    return [types.TextContent(
        type="text",
        text=f"Campaign item created on campaign {campaign_id}:\n{format_response(item)}",
    )]


async def update_native_item(arguments: dict = None) -> List[types.TextContent]:
    """Update an existing native item (partial-merge for scalars)."""
    args = arguments or {}
    account_id = args.get("account_id")
    campaign_id = args.get("campaign_id")
    item_id = args.get("item_id")

    is_valid, error_message = validate_account_id(account_id)
    if not is_valid:
        raise ToolInputError(error_message)

    if not campaign_id:
        raise ToolInputError("campaign_id is required")

    if not item_id:
        raise ToolInputError("item_id is required")

    payload = _build_item_payload(args, is_create=False)

    if not payload:
        raise ToolInputError("at least one updatable field must be supplied")

    response = await client.post(
        f"/{quote(account_id, safe='')}/campaigns/{quote(campaign_id, safe='')}"
        f"/items/{quote(item_id, safe='')}",
        data=payload,
    )

    return [types.TextContent(
        type="text",
        text=f"Campaign item {item_id} updated:\n{format_response(response)}",
    )]
