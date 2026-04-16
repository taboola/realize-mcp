"""Sanitize user-supplied strings before logging or echoing.

Strips CRLF / control chars, ANSI CSI sequences, and ${...} substitution
patterns (defense against Log4Shell-style injection into log sinks).
"""
import re
import unicodedata
from typing import Any

MAX_LEN = 4096
MAX_DEPTH = 32

_ANSI_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
_CONTROL_RE = re.compile(r"[\x00-\x1F\x7F-\x9F]")
_SUBST_RE = re.compile(r"\$\{[^${}]*\}")
_MAX_SUBST_ITER = 5


class SanitizeError(ValueError):
    """Raised when input exceeds sanitizer structural limits (e.g., nesting depth)."""


def sanitize_str(v: str) -> str:
    out = v[:MAX_LEN]
    out = unicodedata.normalize("NFKC", out)
    out = _ANSI_RE.sub("", out)
    out = _CONTROL_RE.sub("", out)
    for _ in range(_MAX_SUBST_ITER):
        new = _SUBST_RE.sub("", out)
        if new == out:
            break
        out = new
    return out[:MAX_LEN]


def sanitize(v: Any, _depth: int = 0) -> Any:
    if _depth > MAX_DEPTH:
        raise SanitizeError("input nesting exceeds maximum depth")
    if isinstance(v, str):
        return sanitize_str(v)
    if isinstance(v, list):
        return [sanitize(x, _depth + 1) for x in v]
    if isinstance(v, dict):
        return {
            (sanitize_str(k) if isinstance(k, str) else k): sanitize(x, _depth + 1)
            for k, x in v.items()
        }
    return v
