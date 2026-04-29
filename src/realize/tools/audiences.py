"""Audience targeting helpers for update_campaign_my_audiences and lookalike tools."""
from typing import Any

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
