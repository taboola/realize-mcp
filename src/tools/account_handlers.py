"""Account management tool handlers."""
import logging
from typing import List
import json
import mcp.types as types
from realize.client import client

logger = logging.getLogger(__name__)



async def search_accounts(query: str) -> List[types.TextContent]:
    """
    Search for accounts by numeric ID or text query to get account_id values.
    
    This tool helps resolve account IDs for use with other campaign and report tools.
    The response contains 'account_id' fields (camelCase strings) that are required
    parameters for campaign management, reporting, and other account-specific operations.
    
    You can search by:
    - Numeric account ID (exact match)
    - Company/account name (fuzzy search)
    
    Args:
        query: Account ID (numeric) or search term (text)
        
    Returns:
        List of matching accounts with their details including 'account_id' field
        
    Example response structure:
        {
          "results": [
            {
              "account_id": "1234567890",  // Use this value for other tools
              "name": "Example Corp",
              "type": "advertiser",
              "status": "active"
            }
          ]
        }
    """
    try:
        # Validate input
        if not query or not query.strip():
            return [
                types.TextContent(
                    type="text",
                    text="Error: Query parameter cannot be empty"
                )
            ]
        
        # Build query parameters based on query type
        params = {}
        cleaned_query = query.strip()
        if cleaned_query.isdigit():
            params["id"] = cleaned_query
        else:
            params["search"] = cleaned_query
        
        # Call the API directly
        data = await client.get("/advertisers", params=params)
        
        # Return raw JSON response with all fields
        return [
            types.TextContent(
                type="text",
                text=json.dumps(data, indent=2, ensure_ascii=False)
            )
        ]
    except Exception as e:
        logger.error(f"Failed to search accounts: {e}")
        return [
            types.TextContent(
                type="text",
                text=f"Failed to search accounts: {str(e)}"
            )
        ] 