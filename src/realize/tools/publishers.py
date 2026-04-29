"""Publisher targeting + bid modifier helpers for update_campaign_publishers tool."""
import math
from typing import Any, Dict, List

from realize.tools.errors import ToolInputError


_TARGETING_TYPES = ("INCLUDE", "EXCLUDE", "ALL")


def _validate_targeting_block(field_name: str, targeting: Any) -> None:
    if not isinstance(targeting, dict):
        raise ToolInputError(f"{field_name} must be an object with 'type' and 'value' fields")

    t_type = targeting.get("type")
    if t_type not in _TARGETING_TYPES:
        raise ToolInputError(
            f"{field_name}.type must be one of: {', '.join(_TARGETING_TYPES)}"
        )

    value = targeting.get("value")
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise ToolInputError(f"{field_name}.value must be a list of strings")

    if t_type == "ALL" and value:
        raise ToolInputError(f"{field_name}.value must be empty when type=ALL (use [] to clear)")
    if t_type in ("INCLUDE", "EXCLUDE") and not value:
        raise ToolInputError(f"{field_name}.value must be non-empty when type={t_type}")


def validate_publisher_targeting(targeting: Any) -> None:
    """Validate publisher_targeting Targeting<String> block."""
    _validate_targeting_block("publisher_targeting", targeting)


def validate_publisher_groups_targeting(targeting: Any) -> None:
    """Validate publisher_groups_targeting Targeting<String> block."""
    _validate_targeting_block("publisher_groups_targeting", targeting)


def validate_publisher_bid_modifier(bid_modifier: Any) -> None:
    """Validate publisher_bid_modifier BidModifiers<String> block.

    Shape: {values: [{target: <publisher_name>, cpc_modification: <number>}]}.
    Empty values list = clear (full replace).
    """
    if not isinstance(bid_modifier, dict):
        raise ToolInputError("publisher_bid_modifier must be an object with a 'values' field")

    values = bid_modifier.get("values")
    if not isinstance(values, list):
        raise ToolInputError("publisher_bid_modifier.values must be a list")

    seen_targets: Dict[str, int] = {}
    for idx, entry in enumerate(values):
        if not isinstance(entry, dict):
            raise ToolInputError(
                f"publisher_bid_modifier.values[{idx}] must be an object with 'target' and 'cpc_modification'"
            )

        target = entry.get("target")
        if not isinstance(target, str):
            raise ToolInputError(
                f"publisher_bid_modifier.values[{idx}].target must be a string"
            )

        cpc_modification = entry.get("cpc_modification")
        if isinstance(cpc_modification, bool) or not isinstance(cpc_modification, (int, float)):
            raise ToolInputError(
                f"publisher_bid_modifier.values[{idx}].cpc_modification must be a number"
            )
        if math.isnan(cpc_modification) or math.isinf(cpc_modification):
            raise ToolInputError(
                f"publisher_bid_modifier.values[{idx}].cpc_modification must be finite"
            )

        if target in seen_targets:
            raise ToolInputError(
                f"publisher_bid_modifier.values[{idx}].target duplicates entry [{seen_targets[target]}]: '{target}'"
            )
        seen_targets[target] = idx


def to_wire_publisher_bid_modifier(bid_modifier: Dict[str, Any]) -> Dict[str, Any]:
    """Convert validated bid modifier to APICampaign wire shape."""
    out_values: List[Dict[str, Any]] = []
    for entry in bid_modifier.get("values", []):
        out_values.append({
            "target": entry["target"],
            "cpc_modification": float(entry["cpc_modification"]),
        })
    return {"values": out_values}
