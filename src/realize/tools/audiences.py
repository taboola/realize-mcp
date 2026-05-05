"""Audience targeting helpers (validation only — wire shape is identity).

MCP exposes the Backstage MultiTargeting wire shape directly:
  {state: ALL|EXISTS, value: [Targeting<V>]}
where each Targeting<V> = {type: INCLUDE|EXCLUDE, value: [V]}.

For audiences_targeting V is an int (audience id).
For lookalike_audience_targeting V is {rule_id, similarity_level}.
"""
from typing import Any, Dict

from realize.tools.errors import ToolInputError


# audiences_targeting allows EXCLUDE; lookalike rejects EXCLUDE / ALL.
_RULE_TYPES = ("INCLUDE", "EXCLUDE")
_LOOKALIKE_TYPES = ("INCLUDE",)
_STATES = ("ALL", "EXISTS")
# Union of similarity_level percentages across audience subtypes:
#   CRM LOOKALIKE: 5/10/15/20/25 ; PIXEL_LOOKALIKE: 5 ; PBP_LOOKALIKE: 1/2/3/4/5
_LOOKALIKE_SIMILARITY_LEVELS = (1, 2, 3, 4, 5, 10, 15, 20, 25)


def _validate_multi_targeting_envelope(field_name: str, payload: Any) -> list:
    if not isinstance(payload, dict):
        raise ToolInputError(f"{field_name} must be an object with 'state' and 'value' fields")

    state = payload.get("state")
    if state not in _STATES:
        raise ToolInputError(
            f"{field_name}.state must be one of: {', '.join(_STATES)} (use ALL with value=[] to clear)"
        )

    value = payload.get("value")
    if not isinstance(value, list):
        raise ToolInputError(f"{field_name}.value must be a list (use [] with state=ALL to clear)")

    if state == "ALL" and value:
        raise ToolInputError(f"{field_name}.value must be empty when state=ALL")

    return value


def validate_my_audiences(my_audiences: Any) -> None:
    """Schema-level validation for audiences_targeting block.

    Wire shape: {state: ALL|EXISTS, value: [{type: INCLUDE|EXCLUDE, value: [int]}]}.
    state=ALL with value=[] clears all audience targeting.

    Raises ToolInputError on the first violation.
    """
    rules = _validate_multi_targeting_envelope("audiences_targeting", my_audiences)

    for idx, rule in enumerate(rules):
        if not isinstance(rule, dict):
            raise ToolInputError(f"audiences_targeting.value[{idx}] must be an object")

        r_type = rule.get("type")
        if r_type not in _RULE_TYPES:
            raise ToolInputError(
                f"audiences_targeting.value[{idx}].type must be one of: {', '.join(_RULE_TYPES)}"
            )

        ids = rule.get("value")
        if not isinstance(ids, list):
            raise ToolInputError(
                f"audiences_targeting.value[{idx}].value must be a list of integer audience IDs"
            )

        for id_idx, audience_id in enumerate(ids):
            if not isinstance(audience_id, int) or isinstance(audience_id, bool):
                raise ToolInputError(
                    f"audiences_targeting.value[{idx}].value[{id_idx}] must be an integer audience ID"
                )


def validate_lookalike_audience(lookalike_audience: Any) -> None:
    """Schema-level validation for lookalike_audience_targeting block.

    Wire shape: {state: ALL|EXISTS, value: [{type: INCLUDE, value: [{rule_id, similarity_level}]}]}.
    Server constraints: at most one outer block, INCLUDE-only, similarity_level in
    cross-subtype union (resolved per rule_id by server).

    Raises ToolInputError on the first violation.
    """
    rules = _validate_multi_targeting_envelope("lookalike_audience_targeting", lookalike_audience)

    if len(rules) > 1:
        raise ToolInputError(
            "lookalike_audience_targeting.value may contain at most one block (server constraint)"
        )

    for idx, rule in enumerate(rules):
        if not isinstance(rule, dict):
            raise ToolInputError(f"lookalike_audience_targeting.value[{idx}] must be an object")

        r_type = rule.get("type")
        if r_type not in _LOOKALIKE_TYPES:
            raise ToolInputError(
                f"lookalike_audience_targeting.value[{idx}].type must be 'INCLUDE' "
                f"(server rejects EXCLUDE/ALL for lookalike)"
            )

        items = rule.get("value")
        if not isinstance(items, list):
            raise ToolInputError(
                f"lookalike_audience_targeting.value[{idx}].value must be a list of "
                f"{{rule_id, similarity_level}} objects"
            )

        for item_idx, item in enumerate(items):
            if not isinstance(item, dict):
                raise ToolInputError(
                    f"lookalike_audience_targeting.value[{idx}].value[{item_idx}] must be an object "
                    f"with rule_id and similarity_level"
                )

            rule_id = item.get("rule_id")
            if (
                not isinstance(rule_id, int)
                or isinstance(rule_id, bool)
                or rule_id <= 0
            ):
                raise ToolInputError(
                    f"lookalike_audience_targeting.value[{idx}].value[{item_idx}].rule_id "
                    f"must be a positive integer"
                )

            similarity = item.get("similarity_level")
            if (
                not isinstance(similarity, int)
                or isinstance(similarity, bool)
                or similarity not in _LOOKALIKE_SIMILARITY_LEVELS
            ):
                raise ToolInputError(
                    f"lookalike_audience_targeting.value[{idx}].value[{item_idx}].similarity_level "
                    f"must be one of: {', '.join(str(v) for v in _LOOKALIKE_SIMILARITY_LEVELS)}"
                )


def sanitize_my_audiences(my_audiences: Dict[str, Any]) -> Dict[str, Any]:
    """Identity: input already matches APICampaign.audiences_targeting wire shape."""
    return {
        "state": my_audiences["state"],
        "value": [
            {"type": rule["type"], "value": list(rule["value"])}
            for rule in my_audiences["value"]
        ],
    }


def sanitize_lookalike_audience(lookalike_audience: Dict[str, Any]) -> Dict[str, Any]:
    """Identity: input already matches APICampaign.lookalike_audience_targeting wire shape."""
    return {
        "state": lookalike_audience["state"],
        "value": [
            {
                "type": rule["type"],
                "value": [
                    {"rule_id": item["rule_id"], "similarity_level": item["similarity_level"]}
                    for item in rule["value"]
                ],
            }
            for rule in lookalike_audience["value"]
        ],
    }
