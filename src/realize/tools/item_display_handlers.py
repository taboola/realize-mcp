"""Display item (creative) write handlers for Realize MCP server.

Two write tools (`create_display_item`, `update_display_item`) covering
display ads attached to a campaign. Two creative modes are supported:

- **Third-party tag** (3P, `display_ad_type=THIRD_PARTY_TAG`): caller supplies
  raw HTML/JS via `ad_tag` plus a single `dimensions` entry.
- **Realize-hosted asset by URL** (1P): caller supplies a public https
  `asset_url` pointing at an image, video, or HTML5 zip. Realize ingests
  by URL file extension; `dimensions` must be omitted (server populates
  them from the asset).

`ad_tag` and `asset_url` are mutually exclusive. On update, either field is
optional (partial-merge); `dimensions` may also be sent alone to update only
the size of an existing 3P item.

URL-crawled native items live in `item_native_handlers`. Type-agnostic
read tools (`list_items`, `get_item`) live in `item_read_handlers`.
"""
from typing import Any, Dict, List
from urllib.parse import quote

import mcp.types as types

from realize.client import client
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


_CREATE_REQUIRED_SCALARS = ("url", "creative_name")

# Top-level scalars carried across both create and update.
# Display items don't support branding_text or cta — the 3P ad tag handles
# branding and click itself; for 1P the hosted asset has no separate
# branding/CTA.
_CREATE_BODY_FIELDS = ("url",)

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


def _validate_creative_name(value: Any) -> None:
    if not isinstance(value, str):
        raise ToolInputError("creative_name must be a string")
    if not value.strip():
        raise ToolInputError("creative_name must be a non-empty string")


def _validate_dimensions(value: Any) -> None:
    # Realize rejects size>1 with 400 ("Only one dimension is allowed for 3rd
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


def _validate_asset_url(value: Any) -> None:
    if not isinstance(value, str):
        raise ToolInputError("asset_url must be a string")
    if not value.strip():
        raise ToolInputError("asset_url must be a non-empty string")
    if not value.startswith("https://"):
        raise ToolInputError(
            "asset_url must be an https URL — Realize only accepts https sources"
        )


def _sanitize_dimensions(value: List[Dict[str, Any]]) -> List[Dict[str, int]]:
    return [{"width": d["width"], "height": d["height"]} for d in value]


def _build_display_payload(args: Dict[str, Any], *, is_create: bool) -> Dict[str, Any]:
    """Validate and assemble the display-item POST body.

    `ad_tag` and `asset_url` are mutually exclusive. When `asset_url` is set,
    the payload uses `display_data.hosted_display_data.asset_url` and Realize
    ingests the asset server-side; `dimensions` must be absent. Otherwise the
    payload uses `display_data.{ad_tag,dimensions}` per the existing 3P flow.

    On update either branch's fields are individually optional (partial-merge);
    on create the caller must supply exactly one discriminator and the
    matching companion fields.

    Server infers `creative_type` (always DISPLAY) and
    `display_data.display_ad_type` from payload shape; both are read-only and
    rejected with 400 if sent.
    """
    body: Dict[str, Any] = {}

    scalar_fields = _CREATE_BODY_FIELDS if is_create else _UPDATE_BODY_FIELDS
    for f in scalar_fields:
        if args.get(f) is not None:
            body[f] = args[f]

    # Normalize blank strings to None so the mutex and required checks agree:
    # _check_create_required treats "" as missing (via truthy), while the rest
    # of this function would otherwise treat "" as set (via is-not-None).
    ad_tag = args.get("ad_tag")
    if isinstance(ad_tag, str) and not ad_tag.strip():
        ad_tag = None

    asset_url = args.get("asset_url")
    if isinstance(asset_url, str) and not asset_url.strip():
        asset_url = None

    dimensions = args.get("dimensions")

    if asset_url is not None and ad_tag is not None:
        raise ToolInputError(
            "ad_tag and asset_url are mutually exclusive — provide only one"
        )

    display_data: Dict[str, Any] = {}

    if asset_url is not None:
        _validate_asset_url(asset_url)
        if dimensions is not None:
            raise ToolInputError(
                "dimensions is not accepted with asset_url — Realize populates "
                "dimensions from the hosted asset"
            )
        display_data["hosted_display_data"] = {"asset_url": asset_url}
    else:
        if ad_tag is not None:
            _validate_ad_tag(ad_tag)
            display_data["ad_tag"] = ad_tag
        if dimensions is not None:
            _validate_dimensions(dimensions)
            display_data["dimensions"] = _sanitize_dimensions(dimensions)

    if display_data:
        body["display_data"] = display_data

    creative_name = args.get("creative_name")
    if creative_name is not None:
        _validate_creative_name(creative_name)
        body["custom_data"] = {"creative_name": creative_name}

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


def _check_create_required(args: Dict[str, Any]) -> None:
    """Build the create-time missing-field error.

    Always-required scalars (url, creative_name) plus the discriminator
    requirement (exactly one of ad_tag or asset_url; if ad_tag, also
    dimensions). Pooling these into one ``Missing required field(s)`` error
    matches the prior 3P-only behavior and keeps client-side feedback
    compact when multiple fields are missing at once.
    """
    missing: List[str] = []
    for field in _CREATE_REQUIRED_SCALARS:
        if not args.get(field):
            missing.append(field)

    has_ad_tag = bool(args.get("ad_tag"))
    has_asset_url = bool(args.get("asset_url"))

    if not has_ad_tag and not has_asset_url:
        missing.append("ad_tag or asset_url")
    elif has_ad_tag and not args.get("dimensions"):
        missing.append("dimensions")

    if missing:
        raise ToolInputError(f"Missing required field(s): {', '.join(missing)}")


async def create_display_item(arguments: dict = None) -> List[types.TextContent]:
    """Create a display item directly attached to a campaign (3P tag or 1P hosted URL)."""
    args = arguments or {}
    account_id = args.get("account_id")
    campaign_id = args.get("campaign_id")

    is_valid, error_message = validate_account_id(account_id)
    if not is_valid:
        raise ToolInputError(error_message)

    if not campaign_id:
        raise ToolInputError("campaign_id is required")

    _check_create_required(args)

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
