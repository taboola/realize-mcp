"""Utility functions for tools."""
import json
from typing import Dict, Any


def format_response(data: Dict[str, Any]) -> str:
    """Format API response data for display."""
    return json.dumps(data, indent=2, ensure_ascii=False)


def safe_get(data: Dict[str, Any], key: str, default: Any = "N/A") -> Any:
    """Safely get value from dictionary with default."""
    return data.get(key, default) 