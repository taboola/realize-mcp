"""Display item (creative) write handlers for Realize MCP server.

Two write tools (`create_display_item`, `update_display_item`) covering
third-party display ads attached to a campaign. 3P only — `display_ad_type`
is fixed at `THIRD_PARTY_TAG`. First-party Realize-hosted assets
(HOSTED_IMAGE / HOSTED_HTML / HOSTED_VIDEO / HOSTED_SOCIAL) are out of scope.
URL-crawled native items live in `item_native_handlers`. Type-agnostic
read tools (`list_items`, `get_item`) live in `item_read_handlers`.
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


_CREATE_REQUIRED = ("url", "ad_tag", "dimensions")

# Top-level scalars carried across both create and update.
_CREATE_BODY_FIELDS = ("url", "branding_text")

_UPDATE_BODY_FIELDS = _CREATE_BODY_FIELDS + ("is_active",)

# Soft cap to catch obvious paste mistakes; structural validation happens
# server-side in DisplayAdTagValidator on item POST.
_AD_TAG_MAX_BYTES = 16 * 1024


def _validate_ad_tag(value: Any) -> None:
    if not isinstance(value, str):
        raise ToolInputError("ad_tag must be a string (raw 3P HTML/JS ad tag)")
    if not value.strip():
        raise ToolInputError("ad_tag must be a non-empty string")
    if len(value.encode("utf-8")) > _AD_TAG_MAX_BYTES:
        raise ToolInputError(
            f"ad_tag exceeds {_AD_TAG_MAX_BYTES} bytes; trim or host externally"
        )


def _validate_dimensions(value: Any) -> None:
    # Backstage rejects size>1 with 400 ("Only one dimension is allowed for 3rd
    # party tags"); enforce here for fast feedback.
    if not isinstance(value, list) or not value:
        raise ToolInputError(
            "dimensions must be a non-empty array of {width, height} objects"
        )
    if len(value) > 1:
        raise ToolInputError(
            "dimensions accepts exactly one {width, height} entry for 3P tags"
        )
    for i, dim in enumerate(value):
        if not isinstance(dim, dict):
            raise ToolInputError(f"dimensions[{i}] must be an object with width and height")
        for key in ("width", "height"):
            v = dim.get(key)
            # bool is an int subclass — exclude it explicitly.
            if not isinstance(v, int) or isinstance(v, bool) or v <= 0:
                raise ToolInputError(
                    f"dimensions[{i}].{key} must be a positive integer"
                )


def _sanitize_dimensions(value: List[Dict[str, Any]]) -> List[Dict[str, int]]:
    return [{"width": d["width"], "height": d["height"]} for d in value]


def _build_display_payload(args: Dict[str, Any], *, is_create: bool) -> Dict[str, Any]:
    """Validate and assemble the display-item POST body.

    Skip-None for top-level scalars; per-section validate-then-sanitize for
    nested blocks. The is_create flag (1) gates update-only top-level fields
    (`is_active`, `verification_pixel`, `viewability_tag`), and (2) injects
    `creative_type` + `display_data.display_ad_type` only on create — both are
    fixed and not editable on update.
    """
    body: Dict[str, Any] = {}

    scalar_fields = _CREATE_BODY_FIELDS if is_create else _UPDATE_BODY_FIELDS
    for f in scalar_fields:
        if args.get(f) is not None:
            body[f] = args[f]

    display_data: Dict[str, Any] = {}
    if is_create:
        display_data["display_ad_type"] = "THIRD_PARTY_TAG"

    ad_tag = args.get("ad_tag")
    if ad_tag is not None:
        _validate_ad_tag(ad_tag)
        display_data["ad_tag"] = ad_tag

    dimensions = args.get("dimensions")
    if dimensions is not None:
        _validate_dimensions(dimensions)
        display_data["dimensions"] = _sanitize_dimensions(dimensions)

    if is_create or display_data:
        body["display_data"] = display_data

    if is_create:
        body["creative_type"] = "DISPLAY"

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


async def create_display_item(arguments: dict = None) -> List[types.TextContent]:
    """Create a 3P display item directly attached to a campaign."""
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

    payload = _build_display_payload(args, is_create=True)

    # Mass endpoint accepts the full payload via APICollection<APICampaignItem>;
    # wrap the single item and unwrap results[0] for callers, matching the
    # native create flow.
    response = await client.post(
        f"/{quote(account_id, safe='')}/campaigns/{quote(campaign_id, safe='')}/items/mass",
        data={"collection": [payload]},
    )
    item = response["results"][0] if isinstance(response, dict) and response.get("results") else response

    return [types.TextContent(
        type="text",
        text=f"Display item created on campaign {campaign_id}:\n{format_response(item)}",
    )]


async def update_display_item(arguments: dict = None) -> List[types.TextContent]:
    """Update an existing display item (partial-merge for scalars and display_data)."""
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

    payload = _build_display_payload(args, is_create=False)

    if not payload:
        raise ToolInputError("at least one updatable field must be supplied")

    response = await client.post(
        f"/{quote(account_id, safe='')}/campaigns/{quote(campaign_id, safe='')}"
        f"/items/{quote(item_id, safe='')}",
        data=payload,
    )

    return [types.TextContent(
        type="text",
        text=f"Display item {item_id} updated:\n{format_response(response)}",
    )]
