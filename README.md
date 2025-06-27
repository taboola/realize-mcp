# Realize MCP - Taboola

An MCP (Model Context Protocol) server that wraps Realize API, enabling AI assistants to interact with Taboola's advertising platform through natural language.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
  - [High-Level Design](#high-level-design)
  - [Core Components](#core-components)
- [Available Tools](#available-tools)
  - [Authentication & Token Management](#authentication--token-management)
  - [Account Management](#account-management)
  - [Campaign Management](#campaign-management)
  - [Campaign Items](#campaign-items)
  - [Reports](#reports)
- [Read-Only Benefits](#read-only-benefits)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Installation](#installation)
  - [Prerequisites](#prerequisites)
  - [Setup](#setup)
- [MCP Server Configuration](#mcp-server-configuration)
  - [Cursor IDE Setup](#cursor-ide-setup)
  - [Claude Desktop Setup](#claude-desktop-setup)
  - [Configuration Notes](#configuration-notes)
- [Configuration](#configuration)
  - [Environment Variables](#environment-variables)
- [Usage Examples](#usage-examples)
  - [Query Campaigns](#query-campaigns)
  - [Get Campaign Details](#get-campaign-details)
  - [Performance Reports](#performance-reports)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
  - [Common Issues](#common-issues)
  - [Debug Mode](#debug-mode)
- [Production Checklist](#production-checklist)
- [Development](#development)
  - [Local Development Setup](#local-development-setup)
- [Security Considerations](#security-considerations)
- [API Reference](#api-reference)
- [License](#license)

## Overview

Realize MCP is a lightweight wrapper around the [Taboola Realize API](https://developers.taboola.com/backstage-api/reference/welcome) that exposes advertising operations as MCP tools. This allows AI assistants to manage campaigns, analyze performance, and handle advertising operations through natural language interactions.

**Architecture Philosophy**: This MCP server uses a **raw JSON response handling** approach for maximum flexibility. Only the `Token` model is explicitly parsed - all other API responses are handled as Python dictionaries, making the system adaptable to API changes and easy to extend.

## Architecture

### High-Level Design

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   AI Assistant  │    │   Realize MCP   │    │   Realize API   │
│   (Claude, GPT) │◄──►│     Server      │◄──►│   (Taboola)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Core Components

#### 1. MCP Server
- **Protocol Implementation**: MCP specification compliance
- **Tool Registry**: Available advertising operations as tools
- **Request Handling**: Process natural language requests and convert to API calls

#### 2. Realize API Client
- **Authentication**: Handle client credentials and token management
- **HTTP Client**: Make HTTPS requests to `https://backstage.taboola.com/backstage/` API endpoints
- **Error Handling**: Process API responses and handle errors gracefully

#### 3. Tool Implementations
- **Campaign Management**: Create, update, and manage campaigns
- **Performance Reporting**: Retrieve and analyze campaign data
- **Campaign Items**: Manage campaign creative items and assets

## Available Tools

Based on the [Realize API](https://developers.taboola.com/backstage-api/reference/welcome), the following tools are available:

### Authentication & Token Management
- `get_auth_token` - Authenticate with client credentials
- `get_token_details` - Retrieve token information and validity

### Account Management
- `search_accounts` - Search for accounts to get account_id values needed for other tools (read-only)

### Campaign Management
- `get_all_campaigns` - Get all campaigns for an account (read-only)
- `get_campaign` - Get specific campaign details (read-only)

### Campaign Items
- `get_campaign_items` - Get all items for a campaign (read-only)
- `get_campaign_item` - Get specific campaign item details (read-only)

### Reports
- `get_top_campaign_content_report` - Get top performing campaign content report (read-only)
- `get_campaign_breakdown_report` - Get campaign breakdown report with hardcoded dimension (read-only)
- `get_campaign_site_day_breakdown_report` - Get campaign site day breakdown report with hardcoded dimension (read-only)
- `get_campaign_history_report` - Get campaign history report (read-only)

## Read-Only Benefits

1. **Safety**: No risk of accidental data modification or deletion
2. **Flexibility**: Raw JSON responses adapt to API changes
3. **Simplicity**: Less complexity without write operations
4. **Production-Ready**: Safe for immediate production deployment
5. **AI-Friendly**: Perfect for analysis, reporting, and insights

## Technology Stack

- **Python 3.10+** - Primary programming language (3.11+ recommended)
- **MCP SDK** - Model Context Protocol implementation
- **httpx** - Async HTTP client for Realize API calls
- **Pydantic** - Data validation and serialization (minimal usage)
- **python-dotenv** - Environment configuration

## Project Structure

```
realize_mcp/
├── src/
│   ├── realize_server.py        # Main MCP server
│   ├── config.py                # Configuration management
│   ├── tools/                   # MCP tool implementations
│   │   ├── registry.py          # Centralized tool registry
│   │   ├── auth_handlers.py     # Authentication tools
│   │   ├── account_handlers.py  # Account management tools
│   │   ├── campaign_handlers.py # Campaign & items tools
│   │   ├── report_handlers.py   # Reporting tools
│   │   └── utils.py             # Utility functions
│   ├── realize/                 # Realize API client
│   │   ├── auth.py              # Authentication handling
│   │   └── client.py            # API client wrapper
│   └── models/
│       └── realize.py           # Token model (minimal)
├── tests/                       # Comprehensive test suite
│   ├── test_production.py       # Production readiness tests
│   └── test_integration.py      # Integration tests
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

## Installation

### Prerequisites
- Python 3.10 or higher (3.11+ recommended)
- Access to Taboola Realize API credentials
- MCP-compatible AI assistant

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/taboola/realize-mcp.git
   cd realize-mcp
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   Set your Realize API credentials as environment variables:
   ```bash
   export REALIZE_CLIENT_ID="your_client_id_here"
   export REALIZE_CLIENT_SECRET="your_client_secret_here"
   ```

4. **Run the server**
   ```bash
   python src/realize_server.py
   ```

## MCP Server Configuration

### Cursor IDE Setup

To use Realize MCP with Cursor, add the following configuration to your Cursor settings:

1. **Open Cursor Settings** (⌘/Ctrl + ,)
2. **Navigate to Features > Model Context Protocol**
3. **Add the following server configuration**:

```json
{
  "mcpServers": {
    "realize-mcp": {
      "command": "python",
      "args": ["/absolute/path/to/realize_mcp/src/realize_server.py"],
      "env": {
        "REALIZE_CLIENT_ID": "your_client_id_here",
        "REALIZE_CLIENT_SECRET": "your_client_secret_here"
      }
    }
  }
}
```

### Claude Desktop Setup

For Claude Desktop, add this to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "realize-mcp": {
      "command": "python",
      "args": ["/absolute/path/to/realize_mcp/src/realize_server.py"],
      "env": {
        "REALIZE_CLIENT_ID": "your_client_id_here",
        "REALIZE_CLIENT_SECRET": "your_client_secret_here"
      }
    }
  }
}
```

### Configuration Notes

- **Replace `/absolute/path/to/realize_mcp/`** with the actual absolute path to your project directory
- **Replace credential placeholders** with your actual Taboola API credentials
- **Restart your AI assistant** after adding the configuration
- **Verify connection** by asking the assistant to list your campaigns

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `REALIZE_CLIENT_ID` | Realize API client ID | Yes |
| `REALIZE_CLIENT_SECRET` | Realize API client secret | Yes |

> **Note**: The server makes HTTPS requests to `https://backstage.taboola.com` for all API operations. This base URL is configured internally and does not require user configuration.

## Usage Examples

### Query Campaigns
```
User: "Show me all campaigns for account 123"
AI Assistant: [Uses get_all_campaigns tool to retrieve all campaigns]
```

### Get Campaign Details
```
User: "Get details for campaign 456 in account 123"
AI Assistant: [Uses get_campaign tool with campaign details]
```

### Performance Reports
```
User: "Get campaign performance report for last month"
AI Assistant: [Uses get_campaign_summary_report tool to get performance data]
```

### Account Discovery
```
User: "Find accounts with 'Marketing' in the name"
AI Assistant: [Uses search_accounts tool to find matching accounts with account_id values]
```

### Find Account by ID
```
User: "Get details for account 12345"
AI Assistant: [Uses search_accounts tool to get account_id for other operations]
```

### Account Resolution Workflow
```
1. User: "Show campaigns for Marketing Corp"
2. AI: Uses search_accounts("Marketing Corp") to get account_id
3. AI: Extracts account_id from response (e.g., "1234567890")
4. AI: Uses get_all_campaigns(account_id="1234567890") with the account_id
```

## Testing

Run the comprehensive test suite:

```bash
# Run all tests
python -m pytest tests/ -v

# Run production tests
python -m pytest tests/test_production.py -v

# Run integration tests
python -m pytest tests/test_integration.py -v

# Run tests with coverage
python -m pytest tests/ --cov=src --cov-report=html
```

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Verify credentials are correct in environment variables
   - Check if API access is enabled for your account
   - Ensure credentials have proper permissions

2. **Server Won't Start**
   - Check Python version (3.10+ required, 3.11+ recommended)
   - Verify all dependencies are installed
   - Check for import errors

3. **Tools Not Available**
   - Restart AI assistant after configuration changes
   - Verify MCP server path is absolute
   - Check server logs for errors

4. **JSON Response Issues**
   - All responses are raw JSON dictionaries
   - No model parsing means flexible field access
   - Use `dict.get()` for safe field access in custom handlers

### Debug Mode
Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
python src/realize_server.py
```

## Production Checklist

- [ ] Credentials configured securely
- [ ] Server starts without errors
- [ ] All tests pass
- [ ] MCP client configuration added
- [ ] AI assistant restarted
- [ ] Basic functionality tested
- [ ] Error handling verified
- [ ] Monitoring configured
- [ ] Documentation reviewed

## Development

### Local Development Setup

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run tests**
   ```bash
   python -m pytest tests/
   ```

3. **Start the server**
   ```bash
   python src/realize_server.py
   ```

## Security Considerations

- Store credentials securely using environment variables
- Never commit credentials to version control
- Use HTTPS for all API communications
- Regularly rotate API credentials
- Monitor API usage and access logs
- **Safe by Design**: Read-only operations eliminate data modification risks

## API Reference

For detailed API documentation, please refer to:
- [Taboola Realize API Documentation](https://developers.taboola.com/backstage-api/reference/welcome)
- [Taboola Realize API Java Client](https://github.com/taboola/backstage-api-java-client) (Reference implementation)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)

## License

This project is licensed under the Apache License 2.0 - see the [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0) for details.

---

**Realize MCP** - Safe, read-only MCP server wrapper for Taboola's Realize API with comprehensive analysis and reporting capabilities. 