"""Third-party verification pixel helpers for update_campaign_item.

Public docs: list of {type, url}. Full-replace within the section: sending the
field overwrites the prior list; [] clears all pixels.
"""
from typing import Any, Dict, List

from realize.tools.errors import ToolInputError


_TYPES = ("CLICK", "VIEWABLE_IMPRESSION", "IMPRESSION")


def validate_verification_pixel(pixels: Any) -> None:
    if not isinstance(pixels, list):
        raise ToolInputError("verification_pixel must be a list (use [] to clear)")

    for idx, p in enumerate(pixels):
        if not isinstance(p, dict):
            raise ToolInputError(f"verification_pixel[{idx}] must be an object")
        ptype = p.get("type")
        if ptype not in _TYPES:
            raise ToolInputError(
                f"verification_pixel[{idx}].type must be one of: {', '.join(_TYPES)}"
            )
        url = p.get("url")
        if not isinstance(url, str) or not url:
            raise ToolInputError(
                f"verification_pixel[{idx}].url must be a non-empty string"
            )


def to_wire_verification_pixel(pixels: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    return [{"type": p["type"], "url": p["url"]} for p in pixels]
