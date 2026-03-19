"""Report handlers for Realize MCP server."""
from typing import List
import mcp.types as types
from realize.tools.utils import format_large_response_with_csv_truncation, validate_account_id
from realize.tools.errors import ToolInputError
from realize.config import SORT_CONFIG
from realize.client import client

# Report-specific pagination configuration
REPORT_PAGINATION = {
    "default_page": 1,
    "default_page_size": 20,  # Smaller default for detailed report data
    "max_page_size": 100      # Lower max to keep response sizes manageable
}


async def get_campaign_breakdown_report(arguments: dict = None) -> List[types.TextContent]:
    """Get campaign breakdown report (read-only) - returns CSV format."""
    account_id = arguments.get("account_id") if arguments else None
    start_date = arguments.get("start_date") if arguments else None
    end_date = arguments.get("end_date") if arguments else None
    filters = arguments.get("filters") if arguments else {}

    # Get pagination parameters with report-specific defaults
    page = arguments.get("page", REPORT_PAGINATION["default_page"]) if arguments else REPORT_PAGINATION["default_page"]
    page_size = arguments.get("page_size", REPORT_PAGINATION["default_page_size"]) if arguments else REPORT_PAGINATION["default_page_size"]

    if page_size > REPORT_PAGINATION["max_page_size"]:
        raise ToolInputError(f"page_size ({page_size}) exceeds maximum allowed for reports ({REPORT_PAGINATION['max_page_size']})")

    # Get sort parameters with defaults
    sort_field = arguments.get("sort_field") if arguments else None
    sort_direction = arguments.get("sort_direction", SORT_CONFIG["default_direction"]) if arguments else SORT_CONFIG["default_direction"]

    is_valid, error_message = validate_account_id(account_id)
    if not is_valid:
        raise ToolInputError(error_message)

    if not start_date or not end_date:
        raise ToolInputError("start_date and end_date are required")

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
        params["sort"] = f"{sort_field},{sort_direction}"

    endpoint = f"/{account_id}/reports/campaign-summary/dimensions/campaign_breakdown"
    response = await client.get(endpoint, params=params)

    # Add pagination context to response for better formatting
    if isinstance(response, dict) and "metadata" not in response:
        response["metadata"] = {"page": page, "page_size": page_size}

    return [types.TextContent(
        type="text",
        text=f"🏆 **Campaign Breakdown Report CSV** - Account: {account_id} | Period: {start_date} to {end_date}\n\n{format_large_response_with_csv_truncation(response)}"
    )]


async def get_campaign_site_day_breakdown_report(arguments: dict = None) -> List[types.TextContent]:
    """Get campaign site day breakdown report (read-only) - returns CSV format."""
    account_id = arguments.get("account_id") if arguments else None
    start_date = arguments.get("start_date") if arguments else None
    end_date = arguments.get("end_date") if arguments else None
    filters = arguments.get("filters") if arguments else {}

    # Get pagination parameters with report-specific defaults
    page = arguments.get("page", REPORT_PAGINATION["default_page"]) if arguments else REPORT_PAGINATION["default_page"]
    page_size = arguments.get("page_size", REPORT_PAGINATION["default_page_size"]) if arguments else REPORT_PAGINATION["default_page_size"]

    if page_size > REPORT_PAGINATION["max_page_size"]:
        raise ToolInputError(f"page_size ({page_size}) exceeds maximum allowed for reports ({REPORT_PAGINATION['max_page_size']})")

    # Get sort parameters with defaults
    sort_field = arguments.get("sort_field") if arguments else None
    sort_direction = arguments.get("sort_direction", SORT_CONFIG["default_direction"]) if arguments else SORT_CONFIG["default_direction"]

    is_valid, error_message = validate_account_id(account_id)
    if not is_valid:
        raise ToolInputError(error_message)

    if not start_date or not end_date:
        raise ToolInputError("start_date and end_date are required")

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
        params["sort"] = f"{sort_field},{sort_direction}"

    endpoint = f"/{account_id}/reports/campaign-summary/dimensions/campaign_site_day_breakdown"
    response = await client.get(endpoint, params=params)

    # Add pagination context to response for better formatting
    if isinstance(response, dict) and "metadata" not in response:
        response["metadata"] = {"page": page, "page_size": page_size}

    return [types.TextContent(
        type="text",
        text=f"📅 **Campaign Site Day Breakdown Report CSV** - Account: {account_id} | Period: {start_date} to {end_date}\n\n{format_large_response_with_csv_truncation(response)}"
    )]


async def get_top_campaign_content_report(arguments: dict = None) -> List[types.TextContent]:
    """Get top performing campaign content report (read-only) - returns CSV format."""
    account_id = arguments.get("account_id") if arguments else None
    start_date = arguments.get("start_date") if arguments else None
    end_date = arguments.get("end_date") if arguments else None

    # Get pagination parameters with report-specific defaults
    page = arguments.get("page", REPORT_PAGINATION["default_page"]) if arguments else REPORT_PAGINATION["default_page"]
    page_size = arguments.get("page_size", REPORT_PAGINATION["default_page_size"]) if arguments else REPORT_PAGINATION["default_page_size"]

    if page_size > REPORT_PAGINATION["max_page_size"]:
        raise ToolInputError(f"page_size ({page_size}) exceeds maximum allowed for reports ({REPORT_PAGINATION['max_page_size']})")

    # Get sort parameters with defaults
    sort_field = arguments.get("sort_field") if arguments else None
    sort_direction = arguments.get("sort_direction", SORT_CONFIG["default_direction"]) if arguments else SORT_CONFIG["default_direction"]

    is_valid, error_message = validate_account_id(account_id)
    if not is_valid:
        raise ToolInputError(error_message)

    if not start_date or not end_date:
        raise ToolInputError("start_date and end_date are required")

    # Build query parameters for the report request
    params = {
        "start_date": start_date,
        "end_date": end_date,
        "page": page,
        "page_size": page_size
    }

    # Handle sort parameter construction
    if sort_field:
        params["sort"] = f"{sort_field},{sort_direction}"

    endpoint = f"/{account_id}/reports/top-campaign-content/dimensions/item_breakdown"
    response = await client.get(endpoint, params=params)

    # Add pagination context to response for better formatting
    if isinstance(response, dict) and "metadata" not in response:
        response["metadata"] = {"page": page, "page_size": page_size}

    return [types.TextContent(
        type="text",
        text=f"🎯 **Top Campaign Content Report CSV** - Account: {account_id} | Period: {start_date} to {end_date}\n\n{format_large_response_with_csv_truncation(response)}"
    )]


async def get_campaign_history_report(arguments: dict = None) -> List[types.TextContent]:
    """Get campaign history report (read-only) - returns CSV format."""
    account_id = arguments.get("account_id") if arguments else None
    start_date = arguments.get("start_date") if arguments else None
    end_date = arguments.get("end_date") if arguments else None

    # Get pagination parameters with report-specific defaults
    page = arguments.get("page", REPORT_PAGINATION["default_page"]) if arguments else REPORT_PAGINATION["default_page"]
    page_size = arguments.get("page_size", REPORT_PAGINATION["default_page_size"]) if arguments else REPORT_PAGINATION["default_page_size"]

    if page_size > REPORT_PAGINATION["max_page_size"]:
        raise ToolInputError(f"page_size ({page_size}) exceeds maximum allowed for reports ({REPORT_PAGINATION['max_page_size']})")

    is_valid, error_message = validate_account_id(account_id)
    if not is_valid:
        raise ToolInputError(error_message)

    if not start_date or not end_date:
        raise ToolInputError("start_date and end_date are required")

    # Build query parameters for the report request
    params = {
        "start_date": start_date,
        "end_date": end_date,
        "page": page,
        "page_size": page_size
    }

    endpoint = f"/{account_id}/reports/campaign-history/dimensions/by_account"
    response = await client.get(endpoint, params=params)

    # Add pagination context to response for better formatting
    if isinstance(response, dict) and "metadata" not in response:
        response["metadata"] = {"page": page, "page_size": page_size}

    return [types.TextContent(
        type="text",
        text=f"📈 **Campaign History Report CSV** - Account: {account_id} | Period: {start_date} to {end_date}\n\n{format_large_response_with_csv_truncation(response)}"
    )]
