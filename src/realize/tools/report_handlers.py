"""Report handlers for Realize MCP server."""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import mcp.types as types
from realize.tools.utils import format_large_response_with_csv_truncation, validate_account_id
from realize.config import SORT_CONFIG
from realize.client import client

logger = logging.getLogger(__name__)

# Report-specific pagination configuration
REPORT_PAGINATION = {
    "default_page": 1,
    "default_page_size": 20,  # Smaller default for detailed report data
    "max_page_size": 100      # Lower max to keep response sizes manageable
}


async def get_campaign_breakdown_report(arguments: dict = None) -> List[types.TextContent]:
    """Get campaign breakdown report (read-only) - returns CSV format."""
    try:
        account_id = arguments.get("account_id") if arguments else None
        start_date = arguments.get("start_date") if arguments else None
        end_date = arguments.get("end_date") if arguments else None
        filters = arguments.get("filters") if arguments else {}
        
        # Get pagination parameters with report-specific defaults
        page = arguments.get("page", REPORT_PAGINATION["default_page"]) if arguments else REPORT_PAGINATION["default_page"]
        page_size = arguments.get("page_size", REPORT_PAGINATION["default_page_size"]) if arguments else REPORT_PAGINATION["default_page_size"]
        
        # Validate page_size doesn't exceed report maximum
        if page_size > REPORT_PAGINATION["max_page_size"]:
            return [types.TextContent(
                type="text",
                text=f"❌ **Error:** page_size ({page_size}) exceeds maximum allowed for reports ({REPORT_PAGINATION['max_page_size']})"
            )]
        
        # Get sort parameters with defaults
        sort_field = arguments.get("sort_field") if arguments else None
        sort_direction = arguments.get("sort_direction", SORT_CONFIG["default_direction"]) if arguments else SORT_CONFIG["default_direction"]
        
        # Validate account_id format
        is_valid, error_message = validate_account_id(account_id)
        if not is_valid:
            return [types.TextContent(
                type="text",
                text=error_message
            )]
        
        if not start_date or not end_date:
            return [types.TextContent(
                type="text",
                text="start_date and end_date are required"
            )]
        
        # Build query parameters for the report request
        params = {
            "start_date": start_date,
            "end_date": end_date,
            "page": page,
            "page_size": page_size
        }
        
        # Add optional filters
        if filters:
            params.update(filters)
        
        # Handle sort parameter construction
        if sort_field:
            # Convert to API string format: ?sort=spent,DESC
            params["sort"] = f"{sort_field},{sort_direction}"
        
        # Make API request to get campaign breakdown report - hardcoded dimension
        endpoint = f"/{account_id}/reports/campaign-summary/dimensions/campaign_breakdown"
        response = await client.get(endpoint, params=params)
        
        # Add pagination context to response for better formatting
        if isinstance(response, dict) and "metadata" not in response:
            response["metadata"] = {"page": page, "page_size": page_size}
        
        return [types.TextContent(
            type="text",
            text=f"🏆 **Campaign Breakdown Report CSV** - Account: {account_id} | Period: {start_date} to {end_date}\n\n{format_large_response_with_csv_truncation(response)}"
        )]
        
    except Exception as e:
        logger.error(f"Failed to get campaign breakdown report: {e}")
        return [types.TextContent(
            type="text",
            text=f"❌ **Error:** Failed to get campaign breakdown report: {str(e)}"
        )]


async def get_campaign_site_day_breakdown_report(arguments: dict = None) -> List[types.TextContent]:
    """Get campaign site day breakdown report (read-only) - returns CSV format."""
    try:
        account_id = arguments.get("account_id") if arguments else None
        start_date = arguments.get("start_date") if arguments else None
        end_date = arguments.get("end_date") if arguments else None
        filters = arguments.get("filters") if arguments else {}
        
        # Get pagination parameters with report-specific defaults
        page = arguments.get("page", REPORT_PAGINATION["default_page"]) if arguments else REPORT_PAGINATION["default_page"]
        page_size = arguments.get("page_size", REPORT_PAGINATION["default_page_size"]) if arguments else REPORT_PAGINATION["default_page_size"]
        
        # Validate page_size doesn't exceed report maximum
        if page_size > REPORT_PAGINATION["max_page_size"]:
            return [types.TextContent(
                type="text",
                text=f"❌ **Error:** page_size ({page_size}) exceeds maximum allowed for reports ({REPORT_PAGINATION['max_page_size']})"
            )]
        
        # Get sort parameters with defaults
        sort_field = arguments.get("sort_field") if arguments else None
        sort_direction = arguments.get("sort_direction", SORT_CONFIG["default_direction"]) if arguments else SORT_CONFIG["default_direction"]
        
        # Validate account_id format
        is_valid, error_message = validate_account_id(account_id)
        if not is_valid:
            return [types.TextContent(
                type="text",
                text=error_message
            )]
        
        if not start_date or not end_date:
            return [types.TextContent(
                type="text",
                text="start_date and end_date are required"
            )]
        
        # Build query parameters for the report request
        params = {
            "start_date": start_date,
            "end_date": end_date,
            "page": page,
            "page_size": page_size
        }
        
        # Add optional filters
        if filters:
            params.update(filters)
        
        # Handle sort parameter construction
        if sort_field:
            # Convert to API string format: ?sort=spent,DESC
            params["sort"] = f"{sort_field},{sort_direction}"
        
        # Make API request to get campaign site day breakdown report - hardcoded dimension
        endpoint = f"/{account_id}/reports/campaign-summary/dimensions/campaign_site_day_breakdown"
        response = await client.get(endpoint, params=params)
        
        # Add pagination context to response for better formatting
        if isinstance(response, dict) and "metadata" not in response:
            response["metadata"] = {"page": page, "page_size": page_size}
        
        return [types.TextContent(
            type="text",
            text=f"📅 **Campaign Site Day Breakdown Report CSV** - Account: {account_id} | Period: {start_date} to {end_date}\n\n{format_large_response_with_csv_truncation(response)}"
        )]
        
    except Exception as e:
        logger.error(f"Failed to get campaign site day breakdown report: {e}")
        return [types.TextContent(
            type="text",
            text=f"❌ **Error:** Failed to get campaign site day breakdown report: {str(e)}"
        )]


async def get_top_campaign_content_report(arguments: dict = None) -> List[types.TextContent]:
    """Get top performing campaign content report (read-only) - returns CSV format."""
    try:
        account_id = arguments.get("account_id") if arguments else None
        start_date = arguments.get("start_date") if arguments else None
        end_date = arguments.get("end_date") if arguments else None
        
        # Get pagination parameters with report-specific defaults
        page = arguments.get("page", REPORT_PAGINATION["default_page"]) if arguments else REPORT_PAGINATION["default_page"]
        page_size = arguments.get("page_size", REPORT_PAGINATION["default_page_size"]) if arguments else REPORT_PAGINATION["default_page_size"]
        
        # Validate page_size doesn't exceed report maximum
        if page_size > REPORT_PAGINATION["max_page_size"]:
            return [types.TextContent(
                type="text",
                text=f"❌ **Error:** page_size ({page_size}) exceeds maximum allowed for reports ({REPORT_PAGINATION['max_page_size']})"
            )]
        
        # Get sort parameters with defaults
        sort_field = arguments.get("sort_field") if arguments else None
        sort_direction = arguments.get("sort_direction", SORT_CONFIG["default_direction"]) if arguments else SORT_CONFIG["default_direction"]
        
        # Validate account_id format
        is_valid, error_message = validate_account_id(account_id)
        if not is_valid:
            return [types.TextContent(
                type="text",
                text=error_message
            )]
        
        if not start_date or not end_date:
            return [types.TextContent(
                type="text",
                text="start_date and end_date are required"
            )]
        
        # Build query parameters for the report request
        params = {
            "start_date": start_date,
            "end_date": end_date,
            "page": page,
            "page_size": page_size
        }
        
        # Handle sort parameter construction
        if sort_field:
            # Convert to API string format: ?sort=spent,DESC
            params["sort"] = f"{sort_field},{sort_direction}"
        
        # Make API request to get top campaign content report - returns raw JSON dict
        endpoint = f"/{account_id}/reports/top-campaign-content/dimensions/item_breakdown"
        response = await client.get(endpoint, params=params)
        
        # Add pagination context to response for better formatting
        if isinstance(response, dict) and "metadata" not in response:
            response["metadata"] = {"page": page, "page_size": page_size}
        
        return [types.TextContent(
            type="text",
            text=f"🎯 **Top Campaign Content Report CSV** - Account: {account_id} | Period: {start_date} to {end_date}\n\n{format_large_response_with_csv_truncation(response)}"
        )]
        
    except Exception as e:
        logger.error(f"Failed to get top campaign content report: {e}")
        return [types.TextContent(
            type="text",
            text=f"❌ **Error:** Failed to get top campaign content report: {str(e)}"
        )]


async def get_campaign_history_report(arguments: dict = None) -> List[types.TextContent]:
    """Get campaign history report (read-only) - returns CSV format."""
    try:
        account_id = arguments.get("account_id") if arguments else None
        start_date = arguments.get("start_date") if arguments else None
        end_date = arguments.get("end_date") if arguments else None
        
        # Get pagination parameters with report-specific defaults
        page = arguments.get("page", REPORT_PAGINATION["default_page"]) if arguments else REPORT_PAGINATION["default_page"]
        page_size = arguments.get("page_size", REPORT_PAGINATION["default_page_size"]) if arguments else REPORT_PAGINATION["default_page_size"]
        
        # Validate page_size doesn't exceed report maximum
        if page_size > REPORT_PAGINATION["max_page_size"]:
            return [types.TextContent(
                type="text",
                text=f"❌ **Error:** page_size ({page_size}) exceeds maximum allowed for reports ({REPORT_PAGINATION['max_page_size']})"
            )]
        
        # Validate account_id format
        is_valid, error_message = validate_account_id(account_id)
        if not is_valid:
            return [types.TextContent(
                type="text",
                text=error_message
            )]
        
        if not start_date or not end_date:
            return [types.TextContent(
                type="text",
                text="start_date and end_date are required"
            )]
        
        # Build query parameters for the report request
        params = {
            "start_date": start_date,
            "end_date": end_date,
            "page": page,
            "page_size": page_size
        }
        
        # Make API request to get campaign history report - returns raw JSON dict
        endpoint = f"/{account_id}/reports/campaign-history/dimensions/by_account"
        response = await client.get(endpoint, params=params)
        
        # Add pagination context to response for better formatting
        if isinstance(response, dict) and "metadata" not in response:
            response["metadata"] = {"page": page, "page_size": page_size}
        
        return [types.TextContent(
            type="text",
            text=f"📈 **Campaign History Report CSV** - Account: {account_id} | Period: {start_date} to {end_date}\n\n{format_large_response_with_csv_truncation(response)}"
        )]
        
    except Exception as e:
        logger.error(f"Failed to get campaign history report: {e}")
        return [types.TextContent(
            type="text",
            text=f"❌ **Error:** Failed to get campaign history report: {str(e)}"
        )] 