"""Activity-schedule helpers for update_campaign_schedule tool."""
from typing import Any, Dict, List

from realize.tools.errors import ToolInputError


_MODES = ("ALWAYS", "CUSTOM")
_RULE_TYPES = ("INCLUDE", "EXCLUDE")
_DAYS = (
    "MONDAY",
    "TUESDAY",
    "WEDNESDAY",
    "THURSDAY",
    "FRIDAY",
    "SATURDAY",
    "SUNDAY",
)


def _is_int(x: Any) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def _validate_rule(idx: int, rule: Any) -> None:
    if not isinstance(rule, dict):
        raise ToolInputError(f"schedule.rules[{idx}] must be an object")

    r_type = rule.get("type")
    if r_type not in _RULE_TYPES:
        raise ToolInputError(
            f"schedule.rules[{idx}].type must be one of: {', '.join(_RULE_TYPES)}"
        )

    day = rule.get("day")
    if day not in _DAYS:
        raise ToolInputError(
            f"schedule.rules[{idx}].day must be one of: {', '.join(_DAYS)}"
        )

    from_hour = rule.get("from_hour")
    if not _is_int(from_hour) or from_hour < 0 or from_hour > 23:
        raise ToolInputError(
            f"schedule.rules[{idx}].from_hour must be an integer in [0, 23]"
        )

    until_hour = rule.get("until_hour")
    if not _is_int(until_hour) or until_hour < 1 or until_hour > 24:
        raise ToolInputError(
            f"schedule.rules[{idx}].until_hour must be an integer in [1, 24]"
        )

    if until_hour <= from_hour:
        raise ToolInputError(
            f"schedule.rules[{idx}].until_hour must be greater than from_hour"
        )


def validate_schedule(schedule: Any) -> None:
    """Schema-level validation for update_campaign_schedule.

    Server enforces additional cross-rule constraints (per-day INCLUDE/EXCLUDE mutex,
    window overlap, publisher minimum-window-duration, IANA timezone validity); those
    are surfaced via the upstream 4xx body.

    Raises ToolInputError on the first violation.
    """
    if not isinstance(schedule, dict):
        raise ToolInputError("schedule must be an object with a 'mode' field")

    mode = schedule.get("mode")
    if mode not in _MODES:
        raise ToolInputError(f"schedule.mode must be one of: {', '.join(_MODES)}")

    rules = schedule.get("rules")
    time_zone = schedule.get("time_zone")

    if mode == "ALWAYS":
        if rules:
            raise ToolInputError("schedule.rules must be empty or omitted when mode=ALWAYS")
        return

    if not isinstance(time_zone, str) or not time_zone:
        raise ToolInputError("schedule.time_zone is required when mode=CUSTOM (IANA name, e.g. 'America/New_York')")

    if not isinstance(rules, list) or not rules:
        raise ToolInputError("schedule.rules must be a non-empty list when mode=CUSTOM")

    for idx, rule in enumerate(rules):
        _validate_rule(idx, rule)


def to_wire_schedule(schedule: Dict[str, Any]) -> Dict[str, Any]:
    """Convert validated schedule input to the APICampaign.activity_schedule wire shape.

    Mode-specific shaping: ALWAYS emits only mode (+ time_zone if caller provided one);
    CUSTOM emits full body.
    """
    mode = schedule["mode"]
    out: Dict[str, Any] = {"mode": mode}

    if mode == "ALWAYS":
        time_zone = schedule.get("time_zone")
        if isinstance(time_zone, str) and time_zone:
            out["time_zone"] = time_zone
        return out

    out["time_zone"] = schedule["time_zone"]
    rules_out: List[Dict[str, Any]] = []
    for rule in schedule["rules"]:
        rules_out.append({
            "type": rule["type"],
            "day": rule["day"],
            "from_hour": rule["from_hour"],
            "until_hour": rule["until_hour"],
        })
    out["rules"] = rules_out
    return out
