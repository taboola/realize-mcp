"""Conversion-rule attachment helpers.

Wire shape matches Backstage APICampaignUnipRules: {rules: [{id}]}. Validator
operates directly on that shape; sanitizer is identity.
"""
from typing import Any, Dict

from realize.tools.errors import ToolInputError


def validate_conversion_rules(payload: Any) -> None:
    """Schema-level validation for conversion_rules block.

    Wire shape: {rules: [{id}]}. Empty rules list detaches all rules.

    Server enforces existence of each rule id under the account and
    marketing-objective compatibility; those surface via upstream 4xx.

    Raises ToolInputError on the first violation.
    """
    if not isinstance(payload, dict):
        raise ToolInputError(
            "conversion_rules must be an object with a 'rules' list"
        )

    rules = payload.get("rules")
    if not isinstance(rules, list):
        raise ToolInputError(
            "conversion_rules.rules must be a list (use [] to detach all)"
        )

    seen: set = set()
    for idx, rule in enumerate(rules):
        if not isinstance(rule, dict):
            raise ToolInputError(
                f"conversion_rules.rules[{idx}] must be an object with an 'id' field"
            )
        rule_id = rule.get("id")
        if (
            not isinstance(rule_id, int)
            or isinstance(rule_id, bool)
            or rule_id <= 0
        ):
            raise ToolInputError(
                f"conversion_rules.rules[{idx}].id must be a positive integer"
            )
        if rule_id in seen:
            raise ToolInputError(
                f"conversion_rules.rules[{idx}].id duplicate: {rule_id} appears more than once"
            )
        seen.add(rule_id)


def sanitize_conversion_rules(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Identity: input already matches APICampaignUnipRules wire shape."""
    return {"rules": [{"id": rule["id"]} for rule in payload.get("rules", [])]}
