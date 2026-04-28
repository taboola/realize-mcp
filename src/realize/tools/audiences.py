"""Audience targeting helpers for update_campaign_my_audiences tool."""
from typing import Any

from realize.tools.errors import ToolInputError


# No ALL: my_audiences endpoint clears via empty outer collection, unlike geo/techno's type=ALL.
_RULE_TYPES = ("INCLUDE", "EXCLUDE")


def validate_my_audiences(targeting: Any) -> None:
    """Schema-level validation for update_campaign_my_audiences.

    Note the public API reuses 'collection' for both the outer rule wrapper and the
    inner audience-id list; the doubled key is intentional.

    Raises ToolInputError on the first violation.
    """
    if not isinstance(targeting, dict):
        raise ToolInputError("targeting must be an object with a 'collection' field")

    collection = targeting.get("collection")
    if not isinstance(collection, list):
        raise ToolInputError("targeting.collection must be a list of rules (use [] to clear)")

    for idx, rule in enumerate(collection):
        if not isinstance(rule, dict):
            raise ToolInputError(f"targeting.collection[{idx}] must be an object")

        r_type = rule.get("type")
        if r_type not in _RULE_TYPES:
            raise ToolInputError(
                f"targeting.collection[{idx}].type must be one of: {', '.join(_RULE_TYPES)}"
            )

        ids = rule.get("collection")
        if not isinstance(ids, list):
            raise ToolInputError(
                f"targeting.collection[{idx}].collection must be a list of integer audience IDs"
            )

        for id_idx, audience_id in enumerate(ids):
            if not isinstance(audience_id, int) or isinstance(audience_id, bool):
                raise ToolInputError(
                    f"targeting.collection[{idx}].collection[{id_idx}] must be an integer audience ID"
                )
