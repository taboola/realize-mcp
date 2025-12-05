"""Campaign handlers for Realize MCP server."""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import mcp.types as types
from realize.tools.utils import format_response, validate_account_id
from realize.client import client

logger = logging.getLogger(__name__)


async def get_all_campaigns(arguments: dict = None) -> List[types.TextContent]:
    """Get all campaigns for an account (read-only)."""
    try:
        account_id = arguments.get("account_id") if arguments else None
        
        # Validate account_id format
        is_valid, error_message = validate_account_id(account_id)
        if not is_valid:
            return [types.TextContent(
                type="text",
                text=error_message
            )]
        
        # Make API request to get campaigns - returns raw JSON dict
        response = await client.get(f"/{account_id}/campaigns")
        
        return [types.TextContent(
            type="text", 
            text=f"Campaigns for account {account_id}:\n{format_response(response)}"
        )]
        
    except Exception as e:
        logger.error(f"Failed to get campaigns: {e}")
        return [types.TextContent(
            type="text",
            text=f"Failed to get campaigns: {str(e)}"
        )]


async def get_campaign(arguments: dict = None) -> List[types.TextContent]:
    """Get specific campaign details (read-only)."""
    try:
        account_id = arguments.get("account_id") if arguments else None
        campaign_id = arguments.get("campaign_id") if arguments else None
        
        # Validate account_id format
        is_valid, error_message = validate_account_id(account_id)
        if not is_valid:
            return [types.TextContent(
                type="text",
                text=error_message
            )]
        
        if not campaign_id:
            return [types.TextContent(
                type="text",
                text="campaign_id is required"
            )]
        
        # Make API request to get campaign details - returns raw JSON dict
        response = await client.get(f"/{account_id}/campaigns/{campaign_id}")
        
        return [types.TextContent(
            type="text",
            text=f"Campaign {campaign_id} details:\n{format_response(response)}"
        )]
        
    except Exception as e:
        logger.error(f"Failed to get campaign details: {e}")
        return [types.TextContent(
            type="text",
            text=f"Failed to get campaign details: {str(e)}"
        )]


async def get_campaign_items(arguments: dict = None) -> List[types.TextContent]:
    """Get all items for a campaign (read-only)."""
    try:
        account_id = arguments.get("account_id") if arguments else None
        campaign_id = arguments.get("campaign_id") if arguments else None
        
        # Validate account_id format
        is_valid, error_message = validate_account_id(account_id)
        if not is_valid:
            return [types.TextContent(
                type="text",
                text=error_message
            )]
        
        if not campaign_id:
            return [types.TextContent(
                type="text",
                text="campaign_id is required"
            )]
        
        # Make API request to get campaign items - returns raw JSON dict
        response = await client.get(f"/{account_id}/campaigns/{campaign_id}/items/")
        
        return [types.TextContent(
            type="text",
            text=f"Campaign items for campaign {campaign_id}:\n{format_response(response)}"
        )]
        
    except Exception as e:
        logger.error(f"Failed to get campaign items: {e}")
        return [types.TextContent(
            type="text",
            text=f"Failed to get campaign items: {str(e)}"
        )]


async def get_campaign_item(arguments: dict = None) -> List[types.TextContent]:
    """Get specific campaign item details (read-only)."""
    try:
        account_id = arguments.get("account_id") if arguments else None
        campaign_id = arguments.get("campaign_id") if arguments else None
        item_id = arguments.get("item_id") if arguments else None
        
        # Validate account_id format
        is_valid, error_message = validate_account_id(account_id)
        if not is_valid:
            return [types.TextContent(
                type="text",
                text=error_message
            )]
        
        if not campaign_id or not item_id:
            return [types.TextContent(
                type="text",
                text="campaign_id and item_id are both required"
            )]
        
        # Make API request to get campaign item details - returns raw JSON dict
        response = await client.get(f"/{account_id}/campaigns/{campaign_id}/items/{item_id}")
        
        return [types.TextContent(
            type="text",
            text=f"Campaign item {item_id} details:\n{format_response(response)}"
        )]
        
    except Exception as e:
        logger.error(f"Failed to get campaign item details: {e}")
        return [types.TextContent(
            type="text",
            text=f"Failed to get campaign item details: {str(e)}"
        )] 