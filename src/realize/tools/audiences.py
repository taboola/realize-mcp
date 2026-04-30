"""Audience targeting helpers (validation + wire-shape projection)."""
from typing import Any, Dict, List

from realize.tools.errors import ToolInputError


# No ALL: my_audiences endpoint clears via empty outer collection, unlike geo/techno's type=ALL.
_RULE_TYPES = ("INCLUDE", "EXCLUDE")

# Lookalike server rejects EXCLUDE; only INCLUDE allowed.
_LOOKALIKE_TYPES = ("INCLUDE",)
# Union of similarity_level percentages across audience subtypes:
#   CRM LOOKALIKE: 5/10/15/20/25 ; PIXEL_LOOKALIKE: 5 ; PBP_LOOKALIKE: 1/2/3/4/5
# Server resolves subtype from rule_id and rejects mismatches.
_LOOKALIKE_SIMILARITY_LEVELS = (1, 2, 3, 4, 5, 10, 15, 20, 25)


def validate_my_audiences(my_audiences: Any) -> None:
    """Schema-level validation for update_campaign_my_audiences.

    Note the public API reuses 'collection' for both the outer rule wrapper and the
    inner audience-id list; the doubled key is intentional.

    Inner empty collection (e.g. [{"type": "INCLUDE", "collection": []}]) is a
    server-accepted alternate clear path — MyAudiencesTargetingManager treats it
    as "remove audiences targeting".

    Raises ToolInputError on the first violation.
    """
    if not isinstance(my_audiences, dict):
        raise ToolInputError("my_audiences must be an object with a 'collection' field")

    collection = my_audiences.get("collection")
    if not isinstance(collection, list):
        raise ToolInputError("my_audiences.collection must be a list of rules (use [] to clear)")

    for idx, rule in enumerate(collection):
        if not isinstance(rule, dict):
            raise ToolInputError(f"my_audiences.collection[{idx}] must be an object")

        r_type = rule.get("type")
        if r_type not in _RULE_TYPES:
            raise ToolInputError(
                f"my_audiences.collection[{idx}].type must be one of: {', '.join(_RULE_TYPES)}"
            )

        ids = rule.get("collection")
        if not isinstance(ids, list):
            raise ToolInputError(
                f"my_audiences.collection[{idx}].collection must be a list of integer audience IDs"
            )

        for id_idx, audience_id in enumerate(ids):
            if not isinstance(audience_id, int) or isinstance(audience_id, bool):
                raise ToolInputError(
                    f"my_audiences.collection[{idx}].collection[{id_idx}] must be an integer audience ID"
                )


def validate_lookalike_audience(lookalike_audience: Any) -> None:
    """Schema-level validation for update_campaign_lookalike_audience.

    Server rules enforced client-side: outer collection size <= 1, INCLUDE-only,
    rule_id positive int, similarity_level in cross-subtype union. Server further
    restricts similarity_level by audience subtype (resolved from rule_id).

    Inner empty collection (e.g. [{"type": "INCLUDE", "collection": []}]) is a
    server-accepted no-op — LookalikeAudienceTargetingManager early-returns from
    validation when the inner list is empty.

    Raises ToolInputError on the first violation.
    """
    if not isinstance(lookalike_audience, dict):
        raise ToolInputError("lookalike_audience must be an object with a 'collection' field")

    collection = lookalike_audience.get("collection")
    if not isinstance(collection, list):
        raise ToolInputError("lookalike_audience.collection must be a list of rules (use [] to clear)")

    if len(collection) > 1:
        raise ToolInputError(
            "lookalike_audience.collection may contain at most one block (server constraint)"
        )

    for idx, rule in enumerate(collection):
        if not isinstance(rule, dict):
            raise ToolInputError(f"lookalike_audience.collection[{idx}] must be an object")

        r_type = rule.get("type")
        if r_type not in _LOOKALIKE_TYPES:
            raise ToolInputError(
                f"lookalike_audience.collection[{idx}].type must be 'INCLUDE' (server rejects EXCLUDE/ALL for lookalike)"
            )

        items = rule.get("collection")
        if not isinstance(items, list):
            raise ToolInputError(
                f"lookalike_audience.collection[{idx}].collection must be a list of {{rule_id, similarity_level}} objects"
            )

        for item_idx, item in enumerate(items):
            if not isinstance(item, dict):
                raise ToolInputError(
                    f"lookalike_audience.collection[{idx}].collection[{item_idx}] must be an object with rule_id and similarity_level"
                )

            rule_id = item.get("rule_id")
            if (
                not isinstance(rule_id, int)
                or isinstance(rule_id, bool)
                or rule_id <= 0
            ):
                raise ToolInputError(
                    f"lookalike_audience.collection[{idx}].collection[{item_idx}].rule_id must be a positive integer"
                )

            similarity = item.get("similarity_level")
            if (
                not isinstance(similarity, int)
                or isinstance(similarity, bool)
                or similarity not in _LOOKALIKE_SIMILARITY_LEVELS
            ):
                raise ToolInputError(
                    f"lookalike_audience.collection[{idx}].collection[{item_idx}].similarity_level must be one of: "
                    f"{', '.join(str(v) for v in _LOOKALIKE_SIMILARITY_LEVELS)}"
                )


def to_wire_my_audiences(my_audiences: Dict[str, Any]) -> Dict[str, Any]:
    """Project validated my_audiences input to APICampaign.audiences_targeting wire shape.

    Input:  {collection: [{type: INCLUDE|EXCLUDE, collection: [int]}]}
    Output: MultiTargeting<Long> = {state, value: [{type, value: [int]}]}.
    Empty inner collection (or empty outer) clears via state=ALL.
    """
    return _project_to_multi_targeting(my_audiences, value_projector=lambda items: list(items))


def to_wire_lookalike_audience(lookalike_audience: Dict[str, Any]) -> Dict[str, Any]:
    """Project validated lookalike_audience input to APICampaign.lookalike_audience_targeting wire shape.

    Input:  {collection: [{type: INCLUDE, collection: [{rule_id, similarity_level}]}]}
    Output: MultiTargeting<APICampaignLookalikeAudienceTargeting> =
            {state, value: [{type, value: [{rule_id, similarity_level}]}]}.
    """
    def _project_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [
            {"rule_id": it["rule_id"], "similarity_level": it["similarity_level"]}
            for it in items
        ]

    return _project_to_multi_targeting(lookalike_audience, value_projector=_project_items)


def _project_to_multi_targeting(
    block: Dict[str, Any],
    *,
    value_projector,
) -> Dict[str, Any]:
    """Translate {collection: [{type, collection: [V]}]} → {state, value: [{type, value: [V]}]}.

    Empty outer collection or all-empty inner collections → state=ALL, value=[] (clears).
    """
    rules_in = block.get("collection") or []
    rules_out: List[Dict[str, Any]] = []
    for rule in rules_in:
        items = rule.get("collection") or []
        if not items:
            continue
        rules_out.append({"type": rule["type"], "value": value_projector(items)})
    if not rules_out:
        return {"state": "ALL", "value": []}
    return {"state": "EXISTS", "value": rules_out}
