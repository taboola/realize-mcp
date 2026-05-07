"""Contextual-segment targeting helpers (validation only — wire shape is identity).

MCP exposes the Backstage MultiTargeting wire shape directly:
  {state: ALL|EXISTS, value: [{type: INCLUDE|EXCLUDE, value: [int]}]}.
"""
from typing import Any, Dict

from realize.tools.errors import ToolInputError


_RULE_TYPES = ("INCLUDE", "EXCLUDE")
_STATES = ("ALL", "EXISTS")


def validate_contextual_segments(targeting: Any) -> None:
    """Schema-level validation for contextual_segments_targeting block.

    Wire shape: {state: ALL|EXISTS, value: [{type: INCLUDE|EXCLUDE, value: [int]}]}.
    state=ALL with value=[] clears all contextual targeting. At most one rule per
    type (INCLUDE / EXCLUDE).

    Raises ToolInputError on the first violation.
    """
    if not isinstance(targeting, dict):
        raise ToolInputError(
            "contextual_segments_targeting must be an object with 'state' and 'value' fields"
        )

    state = targeting.get("state")
    if state not in _STATES:
        raise ToolInputError(
            f"contextual_segments_targeting.state must be one of: {', '.join(_STATES)} "
            f"(use ALL with value=[] to clear)"
        )

    rules = targeting.get("value")
    if not isinstance(rules, list):
        raise ToolInputError(
            "contextual_segments_targeting.value must be a list (use [] with state=ALL to clear)"
        )

    if state == "ALL" and rules:
        raise ToolInputError(
            "contextual_segments_targeting.value must be empty when state=ALL"
        )

    seen_types: set = set()
    for idx, rule in enumerate(rules):
        if not isinstance(rule, dict):
            raise ToolInputError(
                f"contextual_segments_targeting.value[{idx}] must be an object"
            )

        r_type = rule.get("type")
        if r_type not in _RULE_TYPES:
            raise ToolInputError(
                f"contextual_segments_targeting.value[{idx}].type must be one of: "
                f"{', '.join(_RULE_TYPES)}"
            )
        if r_type in seen_types:
            raise ToolInputError(
                f"contextual_segments_targeting.value[{idx}].type duplicate: "
                f"{r_type!r} appears more than once"
            )
        seen_types.add(r_type)

        ids = rule.get("value")
        if not isinstance(ids, list):
            raise ToolInputError(
                f"contextual_segments_targeting.value[{idx}].value must be a list "
                "of integer segment IDs"
            )

        seen_ids: set = set()
        for id_idx, segment_id in enumerate(ids):
            if not isinstance(segment_id, int) or isinstance(segment_id, bool):
                raise ToolInputError(
                    f"contextual_segments_targeting.value[{idx}].value[{id_idx}] "
                    "must be an integer segment ID"
                )
            if segment_id in seen_ids:
                raise ToolInputError(
                    f"contextual_segments_targeting.value[{idx}].value[{id_idx}] "
                    f"duplicate: {segment_id} appears more than once"
                )
            seen_ids.add(segment_id)


def sanitize_contextual_segments(contextual_segments: Dict[str, Any]) -> Dict[str, Any]:
    """Identity: input already matches APICampaign.contextual_segments_targeting wire shape."""
    return {
        "state": contextual_segments["state"],
        "value": [
            {"type": rule["type"], "value": list(rule["value"])}
            for rule in contextual_segments["value"]
        ],
    }
