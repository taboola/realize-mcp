"""Technology targeting helpers for update_campaign_techno tool."""
from typing import Any, Dict, List, Tuple

from realize.tools.errors import ToolInputError


TECHNO_DIMENSIONS: Tuple[str, ...] = ("platform", "os", "browser", "connection_type")

_TECHNO_WIRE_FIELD: Dict[str, str] = {
    "platform": "platform_targeting",
    "os": "os_targeting",
    "browser": "browser_targeting",
    "connection_type": "connection_type_targeting",
}

_TECHNO_TYPES = ("INCLUDE", "EXCLUDE", "ALL")
_STRING_VALUE_DIMENSIONS = ("platform", "browser", "connection_type")


def techno_wire_field(dimension: str) -> str:
    """Map MCP dimension key to APICampaign wire field."""
    return _TECHNO_WIRE_FIELD[dimension]


def validate_techno(dimension: Any, targeting: Any) -> None:
    """Schema-level validation for update_campaign_techno.

    Raises ToolInputError with a specific message on the first violation.
    """
    if dimension not in _TECHNO_WIRE_FIELD:
        allowed = ", ".join(TECHNO_DIMENSIONS)
        raise ToolInputError(f"dimension must be one of: {allowed}")

    if not isinstance(targeting, dict):
        raise ToolInputError("targeting must be an object with 'type' and 'value' fields")

    t_type = targeting.get("type")
    if t_type not in _TECHNO_TYPES:
        raise ToolInputError(f"targeting.type must be one of: {', '.join(_TECHNO_TYPES)}")

    value = targeting.get("value")
    if not isinstance(value, list):
        raise ToolInputError("targeting.value must be a list")

    if t_type == "ALL" and value:
        raise ToolInputError("targeting.value must be empty when type=ALL (use [] to clear)")
    if t_type in ("INCLUDE", "EXCLUDE") and not value:
        raise ToolInputError(f"targeting.value must be non-empty when type={t_type}")

    if dimension in _STRING_VALUE_DIMENSIONS:
        for idx, item in enumerate(value):
            if not isinstance(item, str):
                raise ToolInputError(
                    f"for dimension={dimension}, targeting.value[{idx}] must be a string"
                )
        return

    for idx, item in enumerate(value):
        if not isinstance(item, dict):
            raise ToolInputError(
                f"for dimension=os, targeting.value[{idx}] must be an object with os_family"
            )
        os_family = item.get("os_family")
        if not isinstance(os_family, str):
            raise ToolInputError(
                f"for dimension=os, targeting.value[{idx}].os_family must be a string"
            )
        sub_categories = item.get("sub_categories")
        if sub_categories is None:
            continue
        if not isinstance(sub_categories, list):
            raise ToolInputError(
                f"for dimension=os, targeting.value[{idx}].sub_categories must be a list of strings"
            )
        for sc_idx, sc in enumerate(sub_categories):
            if not isinstance(sc, str):
                raise ToolInputError(
                    f"for dimension=os, targeting.value[{idx}].sub_categories[{sc_idx}] must be a string"
                )


def sanitize_techno_value(dimension: str, value: List[Any]) -> List[Any]:
    """Convert validated targeting.value to wire shape.

    String dims (platform/browser/connection_type) pass through unchanged.
    For dimension=os: drop empty/null sub_categories.
    """
    if dimension in _STRING_VALUE_DIMENSIONS:
        return value

    out: List[Dict[str, Any]] = []
    for item in value:
        wire_item: Dict[str, Any] = {"os_family": item["os_family"]}
        sub_categories = item.get("sub_categories")
        if sub_categories:
            wire_item["sub_categories"] = list(sub_categories)
        out.append(wire_item)
    return out
