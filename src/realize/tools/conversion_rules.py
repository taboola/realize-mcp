"""Conversion-rule attachment helpers for update_campaign_conversion_rules tool."""
from typing import Any, Dict, List

from realize.tools.errors import ToolInputError


def validate_conversion_rules(rules: Any) -> None:
    """Schema-level validation for update_campaign_conversion_rules.

    Server enforces existence of each rule id under the account, marketing-objective
    compatibility (LEADS_GENERATION/ONLINE_PURCHASES typically require >=1 rule), and
    any account-level rule limits; those surface via the upstream 4xx body.

    Empty list is allowed and detaches all rules.

    Raises ToolInputError on the first violation.
    """
    if not isinstance(rules, list):
        raise ToolInputError("conversion_rules must be a list")

    seen: set = set()
    for idx, rule in enumerate(rules):
        if not isinstance(rule, dict):
            raise ToolInputError(
                f"conversion_rules[{idx}] must be an object with an 'id' field"
            )
        rule_id = rule.get("id")
        if not isinstance(rule_id, str) or not rule_id:
            raise ToolInputError(
                f"conversion_rules[{idx}].id must be a non-empty string"
            )
        if rule_id in seen:
            raise ToolInputError(
                f"conversion_rules[{idx}].id duplicate: {rule_id!r} appears more than once"
            )
        seen.add(rule_id)


def to_wire_conversion_rules(rules: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Project to the minimal {id} reference shape the Campaign update endpoint accepts."""
    return [{"id": r["id"]} for r in rules]
