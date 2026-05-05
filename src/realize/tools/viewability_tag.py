"""Viewability-tag helpers for update_campaign_item.

Public Realize wire shape (matches Backstage APIViewabilityTag):
{
  "values": [
    {"tag": "<JS tag>", "type": "IAS|GOOGLE_DCM|DOUBLE_VERIFY|ADLOOX"}
  ]
}
Send {"values": []} to clear all tags.
"""
from typing import Any, Dict, List

from realize.tools.errors import ToolInputError


_TYPES = ("IAS", "GOOGLE_DCM", "DOUBLE_VERIFY", "ADLOOX")


def validate_viewability_tag(viewability: Any) -> None:
    if not isinstance(viewability, dict):
        raise ToolInputError(
            "viewability_tag must be an object with a 'values' list"
        )

    values = viewability.get("values")
    if not isinstance(values, list):
        raise ToolInputError(
            "viewability_tag.values must be a list (use [] to clear)"
        )

    for idx, item in enumerate(values):
        if not isinstance(item, dict):
            raise ToolInputError(f"viewability_tag.values[{idx}] must be an object")
        ttype = item.get("type")
        if ttype not in _TYPES:
            raise ToolInputError(
                f"viewability_tag.values[{idx}].type must be one of: {', '.join(_TYPES)}"
            )
        tag = item.get("tag")
        if not isinstance(tag, str) or not tag:
            raise ToolInputError(
                f"viewability_tag.values[{idx}].tag must be a non-empty string"
            )


def sanitize_viewability_tag(viewability: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "values": [
            {"tag": item["tag"], "type": item["type"]}
            for item in viewability["values"]
        ]
    }
