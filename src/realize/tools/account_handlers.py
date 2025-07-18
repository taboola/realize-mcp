"""Account management tool handlers."""
import logging
from typing import List
import json
import mcp.types as types
from realize.client import client

logger = logging.getLogger(__name__)



async def search_accounts(query: str, page: int = 1, page_size: int = 10) -> List[types.TextContent]:
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
        page: Page number for pagination (default: 1)
        page_size: Records per page (default: 10, max: 10)
        
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
            params["search_text"] = cleaned_query
        
        # Add pagination parameters
        params["page"] = page
        params["page_size"] = min(page_size, 10)  # Enforce max page_size of 10
        
        # Call the API directly
        data = await client.get("/advertisers", params=params)
        
        # Enhanced formatting with guidance
        if isinstance(data, dict) and "results" in data and data["results"]:
            # Extract account_id values for summary
            account_ids = []
            for result in data["results"]:
                if "account_id" in result:
                    account_ids.append(result["account_id"])
            
            # Create formatted response with guidance
            response_text = f"🎯 ACCOUNT SEARCH RESULTS (Page {page}, Page Size {min(page_size, 10)})\n"
            
            if account_ids:
                response_text += "📋 ACCOUNT_ID VALUES FOR OTHER TOOLS:\n"
                for i, account_id in enumerate(account_ids, 1):
                    result = data["results"][i-1]
                    name = result.get("name", "Unknown")
                    response_text += f"  {i}. account_id: '{account_id}' ({name})\n"
                
                response_text += "\n⚠️  IMPORTANT: Use these exact 'account_id' values (in quotes above) for campaign and report tools.\n\n"
            
            response_text += "📊 FULL DETAILS:\n"
            response_text += json.dumps(data, indent=2, ensure_ascii=False)
            
            return [
                types.TextContent(
                    type="text",
                    text=response_text
                )
            ]
        else:
            # Handle case where no results or unexpected format
            return [
                types.TextContent(
                    type="text",
                    text=f"No accounts found for query: '{query}'\n\nRaw response:\n{json.dumps(data, indent=2, ensure_ascii=False)}"
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