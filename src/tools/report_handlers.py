"""Report handlers for read-only reporting operations using raw JSON."""

import logging
from typing import List
import mcp.types as types
from realize.client import client
from tools.utils import format_response

logger = logging.getLogger(__name__)



async def get_campaign_breakdown_report(arguments: dict = None) -> List[types.TextContent]:
    """Get campaign breakdown report (read-only) - specific dimension hardcoded."""
    try:
        account_id = arguments.get("account_id") if arguments else None
        start_date = arguments.get("start_date") if arguments else None
        end_date = arguments.get("end_date") if arguments else None
        filters = arguments.get("filters") if arguments else {}
        
        if not account_id or not start_date or not end_date:
            return [types.TextContent(
                type="text",
                text="account_id, start_date, and end_date are required"
            )]
        
        # Build query parameters for the report request
        params = {
            "start_date": start_date,
            "end_date": end_date
        }
        
        # Add optional filters
        if filters:
            params.update(filters)
        
        # Make API request to get campaign breakdown report - hardcoded dimension
        endpoint = f"/{account_id}/reports/campaign-summary/dimensions/campaign_breakdown"
        response = await client.get(endpoint, params=params)
        
        return [types.TextContent(
            type="text",
            text=f"Campaign breakdown report for account {account_id} ({start_date} to {end_date}):\n{format_response(response)}"
        )]
        
    except Exception as e:
        logger.error(f"Failed to get campaign breakdown report: {e}")
        return [types.TextContent(
            type="text",
            text=f"Failed to get campaign breakdown report: {str(e)}"
        )]


async def get_campaign_site_day_breakdown_report(arguments: dict = None) -> List[types.TextContent]:
    """Get campaign site day breakdown report (read-only) - specific dimension hardcoded."""
    try:
        account_id = arguments.get("account_id") if arguments else None
        start_date = arguments.get("start_date") if arguments else None
        end_date = arguments.get("end_date") if arguments else None
        filters = arguments.get("filters") if arguments else {}
        
        if not account_id or not start_date or not end_date:
            return [types.TextContent(
                type="text",
                text="account_id, start_date, and end_date are required"
            )]
        
        # Build query parameters for the report request
        params = {
            "start_date": start_date,
            "end_date": end_date
        }
        
        # Add optional filters
        if filters:
            params.update(filters)
        
        # Make API request to get campaign site day breakdown report - hardcoded dimension
        endpoint = f"/{account_id}/reports/campaign-summary/dimensions/campaign_site_day_breakdown"
        response = await client.get(endpoint, params=params)
        
        return [types.TextContent(
            type="text",
            text=f"Campaign site day breakdown report for account {account_id} ({start_date} to {end_date}):\n{format_response(response)}"
        )]
        
    except Exception as e:
        logger.error(f"Failed to get campaign site day breakdown report: {e}")
        return [types.TextContent(
            type="text",
            text=f"Failed to get campaign site day breakdown report: {str(e)}"
        )]


async def get_top_campaign_content_report(arguments: dict = None) -> List[types.TextContent]:
    """Get top performing campaign content report (read-only)."""
    try:
        account_id = arguments.get("account_id") if arguments else None
        start_date = arguments.get("start_date") if arguments else None
        end_date = arguments.get("end_date") if arguments else None
        count = arguments.get("count", 10) if arguments else 10
        
        if not account_id or not start_date or not end_date:
            return [types.TextContent(
                type="text",
                text="account_id, start_date, and end_date are required"
            )]
        
        # Build query parameters for the report request
        params = {
            "start_date": start_date,
            "end_date": end_date,
            "count": count
        }
        
        # Make API request to get top campaign content report - returns raw JSON dict
        endpoint = f"/{account_id}/reports/top-campaign-content"
        response = await client.get(endpoint, params=params)
        
        return [types.TextContent(
            type="text",
            text=f"Top {count} campaign content for account {account_id} ({start_date} to {end_date}):\n{format_response(response)}"
        )]
        
    except Exception as e:
        logger.error(f"Failed to get top campaign content report: {e}")
        return [types.TextContent(
            type="text",
            text=f"Failed to get top campaign content report: {str(e)}"
        )]


async def get_campaign_history_report(arguments: dict = None) -> List[types.TextContent]:
    """Get campaign history report (read-only)."""
    try:
        account_id = arguments.get("account_id") if arguments else None
        start_date = arguments.get("start_date") if arguments else None
        end_date = arguments.get("end_date") if arguments else None
        
        if not account_id or not start_date or not end_date:
            return [types.TextContent(
                type="text",
                text="account_id, start_date, and end_date are required"
            )]
        
        # Build query parameters for the report request
        params = {
            "start_date": start_date,
            "end_date": end_date
        }
        
        # Make API request to get campaign history report - returns raw JSON dict
        endpoint = f"/{account_id}/reports/campaign-summary/campaign-history"
        response = await client.get(endpoint, params=params)
        
        return [types.TextContent(
            type="text",
            text=f"Campaign history report for account {account_id} ({start_date} to {end_date}):\n{format_response(response)}"
        )]
        
    except Exception as e:
        logger.error(f"Failed to get campaign history report: {e}")
        return [types.TextContent(
            type="text",
            text=f"Failed to get campaign history report: {str(e)}"
        )] 