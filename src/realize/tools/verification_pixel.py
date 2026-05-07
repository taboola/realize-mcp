"""Third-party verification pixel helpers for update_native_item.

Public Realize wire shape (matches Backstage APIVerificationPixel):
{
  "verification_pixel_items": [
    {"url": str, "verification_pixel_type": "CLICK|VIEWABLE_IMPRESSION|IMPRESSION"}
  ]
}
Send {"verification_pixel_items": []} to clear all pixels.
"""
from typing import Any, Dict, List

from realize.tools.errors import ToolInputError


_TYPES = ("CLICK", "VIEWABLE_IMPRESSION", "IMPRESSION")


def validate_verification_pixel(pixel: Any) -> None:
    if not isinstance(pixel, dict):
        raise ToolInputError(
            "verification_pixel must be an object with a 'verification_pixel_items' list"
        )

    items = pixel.get("verification_pixel_items")
    if not isinstance(items, list):
        raise ToolInputError(
            "verification_pixel.verification_pixel_items must be a list (use [] to clear)"
        )

    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            raise ToolInputError(
                f"verification_pixel.verification_pixel_items[{idx}] must be an object"
            )
        ptype = item.get("verification_pixel_type")
        if ptype not in _TYPES:
            raise ToolInputError(
                f"verification_pixel.verification_pixel_items[{idx}].verification_pixel_type "
                f"must be one of: {', '.join(_TYPES)}"
            )
        url = item.get("url")
        if not isinstance(url, str) or not url:
            raise ToolInputError(
                f"verification_pixel.verification_pixel_items[{idx}].url must be a non-empty string"
            )


def sanitize_verification_pixel(pixel: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "verification_pixel_items": [
            {"url": item["url"], "verification_pixel_type": item["verification_pixel_type"]}
            for item in pixel["verification_pixel_items"]
        ]
    }
