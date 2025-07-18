#!/usr/bin/env python3
"""Realize MCP Server - Main entry point."""

import asyncio
import logging
from typing import Any, Sequence
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types
from realize.config import config

# Configure logging
logging.basicConfig(level=getattr(logging, config.log_level))
logger = logging.getLogger(__name__)

# Create server instance
server = Server("realize-mcp")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available MCP tools from registry."""
    from realize.tools.registry import get_all_tools
    
    tools = []
    for tool_name, tool_config in get_all_tools().items():
        tools.append(
            types.Tool(
                name=tool_name,
                description=tool_config["description"],
                inputSchema=tool_config["schema"]
            )
        )
    
    return tools

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict[str, Any] | None
) -> list[types.TextContent]:
    """Handle tool calls using registry-based dispatch."""
    from realize.tools.registry import get_all_tools
    from realize.tools.utils import format_response
    from realize.client import client
    
    # Get tool configuration from registry
    registry = get_all_tools()
    if name not in registry:
        raise ValueError(f"Unknown tool: {name}")
    
    tool_config = registry[name]
    handler_path = tool_config["handler"]
    
    try:
        # Dynamic handler import and execution
        if handler_path == "auth_handlers.get_auth_token":
            from realize.tools.auth_handlers import get_auth_token
            return await get_auth_token()
            
        elif handler_path == "auth_handlers.get_token_details":
            from realize.tools.auth_handlers import get_token_details
            return await get_token_details()
            
        elif handler_path == "account_handlers.search_accounts":
            from realize.tools.account_handlers import search_accounts
            return await search_accounts(arguments.get("query"))
            
        # Campaign handlers
        elif handler_path == "campaign_handlers.get_all_campaigns":
            from realize.tools.campaign_handlers import get_all_campaigns
            return await get_all_campaigns(arguments)
            
        elif handler_path == "campaign_handlers.get_campaign":
            from realize.tools.campaign_handlers import get_campaign
            return await get_campaign(arguments)
            
        elif handler_path == "campaign_handlers.get_campaign_items":
            from realize.tools.campaign_handlers import get_campaign_items
            return await get_campaign_items(arguments)
            
        elif handler_path == "campaign_handlers.get_campaign_item":
            from realize.tools.campaign_handlers import get_campaign_item
            return await get_campaign_item(arguments)
            
        # Report handlers
        elif handler_path == "report_handlers.get_top_campaign_content_report":
            from realize.tools.report_handlers import get_top_campaign_content_report
            return await get_top_campaign_content_report(arguments)
            
        elif handler_path == "report_handlers.get_campaign_history_report":
            from realize.tools.report_handlers import get_campaign_history_report
            return await get_campaign_history_report(arguments)
            
        elif handler_path == "report_handlers.get_campaign_breakdown_report":
            from realize.tools.report_handlers import get_campaign_breakdown_report
            return await get_campaign_breakdown_report(arguments)
            
        elif handler_path == "report_handlers.get_campaign_site_day_breakdown_report":
            from realize.tools.report_handlers import get_campaign_site_day_breakdown_report
            return await get_campaign_site_day_breakdown_report(arguments)
            
        else:
            raise ValueError(f"Handler not implemented: {handler_path}")
            
    except Exception as e:
        logger.error(f"Tool execution failed for {name}: {e}")
        return [
            types.TextContent(
                type="text",
                text=f"Tool execution failed: {str(e)}"
            )
        ]




async def main():
    """Main server entry point."""
    logger.info("Starting Realize MCP Server...")
    
    # Run the server using stdio transport
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="realize-mcp",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


def cli_main():
    """Synchronous entry point for command-line usage."""
    asyncio.run(main())


if __name__ == "__main__":
    cli_main()