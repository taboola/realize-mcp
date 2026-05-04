"""Viewability-tag helpers for update_campaign_item (MOAT / IAS).

Public docs: list of {type, value}. Full-replace within the section: sending
the field overwrites the prior list; [] clears all tags.
"""
from typing import Any, Dict, List

from realize.tools.errors import ToolInputError


_TYPES = ("MOAT", "IAS")


def validate_viewability_tag(tags: Any) -> None:
    if not isinstance(tags, list):
        raise ToolInputError("viewability_tag must be a list (use [] to clear)")

    for idx, t in enumerate(tags):
        if not isinstance(t, dict):
            raise ToolInputError(f"viewability_tag[{idx}] must be an object")
        ttype = t.get("type")
        if ttype not in _TYPES:
            raise ToolInputError(
                f"viewability_tag[{idx}].type must be one of: {', '.join(_TYPES)}"
            )
        value = t.get("value")
        if not isinstance(value, str) or not value:
            raise ToolInputError(
                f"viewability_tag[{idx}].value must be a non-empty string"
            )


def to_wire_viewability_tag(tags: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    return [{"type": t["type"], "value": t["value"]} for t in tags]
