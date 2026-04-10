#!/usr/bin/env python3
"""Realize MCP Server - Main entry point."""

import asyncio
import time
from typing import Any
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types
from realize.config import config
from realize.logger import Logger
from realize.tools.errors import ToolInputError, classify_api_error

# Configure logging with log4j-style format
_root_logger = Logger(name=__name__, level=config.log_level)
logger = _root_logger.logger

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
    from realize.app_metrics import metrics

    # Get tool configuration from registry
    registry = get_all_tools()
    if name not in registry:
        raise ValueError(f"Unknown tool: {name}")

    tool_config = registry[name]
    handler_path = tool_config["handler"]
    start = time.monotonic()

    try:
        # Dynamic handler import and execution
        if handler_path == "auth_handlers.get_auth_token":
            from realize.tools.auth_handlers import get_auth_token
            result = await get_auth_token()

        elif handler_path == "auth_handlers.get_token_details":
            from realize.tools.auth_handlers import get_token_details
            result = await get_token_details()

        elif handler_path == "account_handlers.search_accounts":
            from realize.tools.account_handlers import search_accounts
            result = await search_accounts(
                arguments.get("query"),
                page=arguments.get("page", 1),
                page_size=arguments.get("page_size", 10),
            )

        # Campaign handlers
        elif handler_path == "campaign_handlers.get_all_campaigns":
            from realize.tools.campaign_handlers import get_all_campaigns
            result = await get_all_campaigns(arguments)

        elif handler_path == "campaign_handlers.get_campaign":
            from realize.tools.campaign_handlers import get_campaign
            result = await get_campaign(arguments)

        elif handler_path == "campaign_handlers.get_campaign_items":
            from realize.tools.campaign_handlers import get_campaign_items
            result = await get_campaign_items(arguments)

        elif handler_path == "campaign_handlers.get_campaign_item":
            from realize.tools.campaign_handlers import get_campaign_item
            result = await get_campaign_item(arguments)

        # Report handlers
        elif handler_path == "report_handlers.get_top_campaign_content_report":
            from realize.tools.report_handlers import get_top_campaign_content_report
            result = await get_top_campaign_content_report(arguments)

        elif handler_path == "report_handlers.get_campaign_history_report":
            from realize.tools.report_handlers import get_campaign_history_report
            result = await get_campaign_history_report(arguments)

        elif handler_path == "report_handlers.get_campaign_breakdown_report":
            from realize.tools.report_handlers import get_campaign_breakdown_report
            result = await get_campaign_breakdown_report(arguments)

        elif handler_path == "report_handlers.get_campaign_site_day_breakdown_report":
            from realize.tools.report_handlers import get_campaign_site_day_breakdown_report
            result = await get_campaign_site_day_breakdown_report(arguments)

        else:
            raise ValueError(f"Handler not implemented: {handler_path}")

        duration = time.monotonic() - start
        metrics.record_tool_call(name, "success", duration)
        return result

    except ToolInputError as e:
        duration = time.monotonic() - start
        metrics.record_tool_call(name, "error", duration)
        logger.debug(f"Validation error for {name}: {e}")
        raise  # Local validation — message is already client-facing
    except Exception as e:
        duration = time.monotonic() - start
        metrics.record_tool_call(name, "error", duration)
        logger.error(f"Tool execution failed for {name}: {e}")
        raise Exception(classify_api_error(e)) from e


async def run_stdio_server():
    """Run MCP server with stdio transport."""
    logger.info("Starting Realize MCP Server with stdio transport...")

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


async def run_http_server():
    """Run MCP server with Streamable HTTP transport and OAuth 2.1."""
    import uvicorn
    from realize.transports.app import create_app

    logger.info(f"Starting Realize MCP Server with Streamable HTTP transport on port {config.mcp_server_port}...")

    app = create_app()
    main_config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=config.mcp_server_port,
        log_level=config.log_level.lower(),
        log_config=None,  # Preserve our log4j-style dictConfig
        proxy_headers=True,  # Respect X-Forwarded-Proto when available
    )
    main_server = uvicorn.Server(main_config)

    if config.metrics_enabled:
        from realize.transports.metrics_server import create_metrics_app

        logger.info(f"Starting metrics server on port {config.metrics_port}...")
        metrics_app = create_metrics_app()
        metrics_config = uvicorn.Config(
            metrics_app,
            host="0.0.0.0",
            port=config.metrics_port,
            log_level=config.log_level.lower(),
            log_config=None,
        )
        metrics_srv = uvicorn.Server(metrics_config)
        metrics_config.install_signal_handlers = False

        async def _run_main():
            await main_server.serve()
            logger.info("Main server stopped, shutting down metrics server...")
            metrics_srv.should_exit = True

        await asyncio.gather(_run_main(), metrics_srv.serve())
        logger.info("Metrics server stopped")
    else:
        logger.info("Metrics disabled, skipping metrics server")
        await main_server.serve()


async def main():
    """Main server entry point with transport selection."""
    if config.mcp_transport == "streamable-http":
        await run_http_server()
    else:
        await run_stdio_server()


def cli_main():
    """Synchronous entry point for command-line usage."""
    asyncio.run(main())


if __name__ == "__main__":
    cli_main()