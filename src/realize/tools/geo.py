"""Geo targeting helpers for update_campaign_geo_* tools."""
from typing import Any, Dict, List, Tuple

from realize.tools.errors import ToolInputError


CLASSIC_DIMENSIONS: Tuple[str, ...] = ("country", "region", "dma", "city", "postal_code")

_CLASSIC_WIRE_FIELD: Dict[str, str] = {
    "country": "country_targeting",
    "region": "region_country_targeting",
    "dma": "dma_country_targeting",
    "city": "city_targeting",
    "postal_code": "postal_code_targeting",
}

_CLASSIC_TYPES = ("INCLUDE", "EXCLUDE", "ALL")
_ADVANCED_STATES = ("ALL", "EXISTS")
_ADVANCED_RULE_TYPES = ("INCLUDE", "EXCLUDE")
_ADVANCED_VECTOR_DIMS = ("country", "region", "dma", "city", "postal_code")
_ADVANCED_VECTOR_DIM_WIRE: Dict[str, str] = {
    "country": "country",
    "region": "region",
    "dma": "dma",
    "city": "city",
    "postal_code": "postal_code",
}


def geo_classic_wire_field(dimension: str) -> str:
    """Map MCP dimension key to APICampaign wire field."""
    return _CLASSIC_WIRE_FIELD[dimension]


def validate_geo_classic(dimension: Any, targeting: Any) -> None:
    """Schema-level validation for update_campaign_geo_classic.

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


def validate_geo_advanced(geo: Any) -> None:
    """Schema-level validation for update_campaign_geo_advanced.

    Raises ToolInputError on the first violation.
    """
    if not isinstance(geo, dict):
        raise ToolInputError("geo_targeting must be an object with 'state' and 'value' fields")

    state = geo.get("state")
    if state not in _ADVANCED_STATES:
        raise ToolInputError(f"geo_targeting.state must be one of: {', '.join(_ADVANCED_STATES)}")

    rules = geo.get("value")
    if not isinstance(rules, list):
        raise ToolInputError("geo_targeting.value must be a list of rules")

    if state == "ALL" and rules:
        raise ToolInputError("geo_targeting.value must be empty when state=ALL")
    if state == "EXISTS" and not rules:
        raise ToolInputError("geo_targeting.value must be non-empty when state=EXISTS")

    for idx, rule in enumerate(rules):
        if not isinstance(rule, dict):
            raise ToolInputError(f"geo_targeting.value[{idx}] must be an object")
        r_type = rule.get("type")
        if r_type not in _ADVANCED_RULE_TYPES:
            raise ToolInputError(
                f"geo_targeting.value[{idx}].type must be one of: {', '.join(_ADVANCED_RULE_TYPES)}"
            )
        vectors = rule.get("value")
        if not isinstance(vectors, list) or not vectors:
            raise ToolInputError(f"geo_targeting.value[{idx}].value must be a non-empty list of vectors")
        for v_idx, vector in enumerate(vectors):
            if not isinstance(vector, dict):
                raise ToolInputError(
                    f"geo_targeting.value[{idx}].value[{v_idx}] must be an object"
                )
            if not any(vector.get(dim) is not None for dim in _ADVANCED_VECTOR_DIMS):
                raise ToolInputError(
                    f"geo_targeting.value[{idx}].value[{v_idx}] must set at least one of: "
                    f"{', '.join(_ADVANCED_VECTOR_DIMS)}"
                )


def to_wire_geo_advanced(geo: Dict[str, Any]) -> Dict[str, Any]:
    """Convert validated advanced geo input to APICampaign wire shape.

    Drops null geo dims from vectors so the wire payload is minimal.
    Caller-provided 'state'/'type' values pass through unchanged.
    """
    rules_out: List[Dict[str, Any]] = []
    for rule in geo.get("value", []):
        vectors_out: List[Dict[str, Any]] = []
        for vector in rule.get("value", []):
            v_out: Dict[str, Any] = {}
            for dim, wire_key in _ADVANCED_VECTOR_DIM_WIRE.items():
                val = vector.get(dim)
                if val is not None:
                    v_out[wire_key] = val
            vectors_out.append(v_out)
        rules_out.append({"type": rule["type"], "value": vectors_out})
    return {"state": geo["state"], "value": rules_out}
