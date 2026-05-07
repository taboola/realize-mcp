"""CTA helpers for create_native_item / update_native_item.

Validator checks shape only (object with non-empty `cta_type` string). The
cta_type enum itself is curated by the server and changes over time; do not
enforce the enum locally — list_cta_types is the source of truth.
"""
from typing import Any, Dict

from realize.tools.errors import ToolInputError


def validate_cta(cta: Any) -> None:
    if not isinstance(cta, dict):
        raise ToolInputError("cta must be an object with a 'cta_type' field")
    cta_type = cta.get("cta_type")
    if not isinstance(cta_type, str) or not cta_type:
        raise ToolInputError(
            "cta.cta_type must be a non-empty string. Discover allowed values via list_cta_types."
        )


def sanitize_cta(cta: Dict[str, Any]) -> Dict[str, str]:
    return {"cta_type": cta["cta_type"]}
