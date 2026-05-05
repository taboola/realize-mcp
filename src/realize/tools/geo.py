"""Geo targeting helpers for classic geo dimension fields on create_campaign / update_campaign."""
from typing import Any, Dict, Tuple

from realize.tools.errors import ToolInputError


CLASSIC_DIMENSIONS: Tuple[str, ...] = ("country", "region_country", "dma_country", "city", "postal_code")

_CLASSIC_WIRE_FIELD: Dict[str, str] = {
    "country": "country_targeting",
    "region_country": "region_country_targeting",
    "dma_country": "dma_country_targeting",
    "city": "city_targeting",
    "postal_code": "postal_code_targeting",
}

_CLASSIC_TYPES = ("INCLUDE", "EXCLUDE", "ALL")


def geo_classic_wire_field(dimension: str) -> str:
    """Map MCP dimension key to APICampaign wire field."""
    return _CLASSIC_WIRE_FIELD[dimension]


def validate_geo_classic(dimension: Any, targeting: Any) -> None:
    """Schema-level validation for classic geo dimension fields on create_campaign / update_campaign.

    Raises ToolInputError with a specific message on the first violation.
    """
    if dimension not in _CLASSIC_WIRE_FIELD:
        allowed = ", ".join(CLASSIC_DIMENSIONS)
        raise ToolInputError(f"dimension must be one of: {allowed}")

    if not isinstance(targeting, dict):
        raise ToolInputError("targeting must be an object with 'type' and 'value' fields")

    t_type = targeting.get("type")
    if t_type not in _CLASSIC_TYPES:
        raise ToolInputError(f"targeting.type must be one of: {', '.join(_CLASSIC_TYPES)}")

    value = targeting.get("value")
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise ToolInputError("targeting.value must be a list of strings")

    if t_type == "ALL" and value:
        raise ToolInputError("targeting.value must be empty when type=ALL (use [] to clear)")
    if t_type in ("INCLUDE", "EXCLUDE") and not value:
        raise ToolInputError(f"targeting.value must be non-empty when type={t_type}")
