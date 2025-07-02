"""Utility functions for tools."""
import json
from typing import Dict, Any, Tuple


def format_response(data: Dict[str, Any]) -> str:
    """Format API response data for display."""
    return json.dumps(data, indent=2, ensure_ascii=False)


def safe_get(data: Dict[str, Any], key: str, default: Any = "N/A") -> Any:
    """Safely get value from dictionary with default."""
    return data.get(key, default)


def validate_account_id(account_id: str) -> Tuple[bool, str]:
    """
    Validate account_id format and provide helpful errors.
    
    Args:
        account_id: The account ID string to validate
        
    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if account_id is valid, False otherwise
        - error_message: Empty string if valid, helpful error message if invalid
    """
    if not account_id:
        return False, "account_id is required"
    
    if account_id.isdigit():
        return False, (
            f"This appears to be a numeric account ID ({account_id}). Please use the search_accounts tool first "
            "to get the proper account_id field value. REQUIRED WORKFLOW: "
            f"1) search_accounts('{account_id}') 2) Extract 'account_id' field from response 3) Use that account_id value instead"
        )
    
    return True, "" 