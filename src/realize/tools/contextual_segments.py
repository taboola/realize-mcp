"""Contextual-segment targeting helpers (validation + wire-shape projection)."""
from typing import Any, Dict, List

from realize.tools.errors import ToolInputError


# Mirrors my_audiences: outer empty collection clears; no type=ALL on this sub-endpoint.
_RULE_TYPES = ("INCLUDE", "EXCLUDE")


def validate_contextual_segments(targeting: Any) -> None:
    """Schema-level validation for update_campaign_contextual_segments.

    The public API reuses 'collection' for both the outer rule wrapper and the inner
    segment-id list; the doubled key is intentional and mirrors the upstream shape.

    Raises ToolInputError on the first violation.
    """
    if not isinstance(targeting, dict):
        raise ToolInputError(
            "contextual_segments must be an object with a 'collection' field"
        )

    collection = targeting.get("collection")
    if not isinstance(collection, list):
        raise ToolInputError(
            "contextual_segments.collection must be a list of rules (use [] to clear)"
        )

    seen_types: set = set()
    for idx, rule in enumerate(collection):
        if not isinstance(rule, dict):
            raise ToolInputError(
                f"contextual_segments.collection[{idx}] must be an object"
            )

        r_type = rule.get("type")
        if r_type not in _RULE_TYPES:
            raise ToolInputError(
                f"contextual_segments.collection[{idx}].type must be one of: "
                f"{', '.join(_RULE_TYPES)}"
            )
        if r_type in seen_types:
            raise ToolInputError(
                f"contextual_segments.collection[{idx}].type duplicate: "
                f"{r_type!r} appears more than once"
            )
        seen_types.add(r_type)

        ids = rule.get("collection")
        if not isinstance(ids, list):
            raise ToolInputError(
                f"contextual_segments.collection[{idx}].collection must be a list "
                "of integer segment IDs"
            )

        seen_ids: set = set()
        for id_idx, segment_id in enumerate(ids):
            if not isinstance(segment_id, int) or isinstance(segment_id, bool):
                raise ToolInputError(
                    f"contextual_segments.collection[{idx}].collection[{id_idx}] "
                    "must be an integer segment ID"
                )
            if segment_id in seen_ids:
                raise ToolInputError(
                    f"contextual_segments.collection[{idx}].collection[{id_idx}] "
                    f"duplicate: {segment_id} appears more than once"
                )
            seen_ids.add(segment_id)


def to_wire_contextual_segments(contextual_segments: Dict[str, Any]) -> Dict[str, Any]:
    """Project validated contextual_segments input to APICampaign.contextual_segments_targeting wire shape.

    Input:  {collection: [{type: INCLUDE|EXCLUDE, collection: [int]}]}
    Output: MultiTargeting<Long> = {state, value: [{type, value: [int]}]}.
    Empty outer collection clears via state=ALL.
    """
    rules_in = contextual_segments.get("collection") or []
    rules_out: List[Dict[str, Any]] = []
    for rule in rules_in:
        items = rule.get("collection") or []
        if not items:
            continue
        rules_out.append({"type": rule["type"], "value": list(items)})
    if not rules_out:
        return {"state": "ALL", "value": []}
    return {"state": "EXISTS", "value": rules_out}
