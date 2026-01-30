# Realize MCP Server

A Model Context Protocol (MCP) server that provides read-only access to Taboola's Realize API, enabling AI assistants to analyze campaigns, retrieve performance data, and generate reports through natural language. Install the MCP Server with stdio transport for single-user local use, or SSE transport for multi-user deployment.

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Python-3.10+-green.svg)](https://python.org)
[![MCP](https://img.shields.io/badge/MCP-Compatible-orange.svg)](https://modelcontextprotocol.io/)
[![Latest Version][mdversion-button]][md-pypi]

[mdversion-button]: https://img.shields.io/pypi/v/realize-mcp.svg
[md-pypi]: https://pypi.org/project/realize-mcp/

---

## Option 1: Stdio Quick Start

Standard MCP transport for local clients. The server runs on your machine and uses server-side credentials for Taboola API authentication.

### Installation

```bash
pip install realize-mcp
```

### Client Setup

**Cursor IDE** - Add to Settings → Features → Model Context Protocol:

```json
{
  "mcpServers": {
    "realize-mcp": {
      "command": "realize-mcp-server",
      "env": {
        "REALIZE_CLIENT_ID": "your_client_id",
        "REALIZE_CLIENT_SECRET": "your_client_secret"
      }
    }
  }
}
```

**Claude Desktop** - Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "realize-mcp": {
      "command": "realize-mcp-server",
      "env": {
        "REALIZE_CLIENT_ID": "your_client_id",
        "REALIZE_CLIENT_SECRET": "your_client_secret"
      }
    }
  }
}
```

---

## Option 2: SSE Quick Start

HTTP-based Server-Sent Events (SSE) transport supporting multiple users via OAuth 2.1

### Server Deployment

SSE transport requires cloning the repository (the startup script is not included in the pip package):

```bash
git clone https://github.com/taboola/realize-mcp.git
cd realize-mcp

# Set required credentials
export OAUTH_DCR_CLIENT_ID=your_dcr_client_id
export OAUTH_DCR_CLIENT_SECRET=your_dcr_client_secret
export MCP_SERVER_URL=https://your-mcp-server.example.com

# Run the SSE server
./scripts/run-sse.sh
```

### Client Setup

**Claude Desktop**

1. Go to Settings → Connectors → Add Custom Connector
2. Enter the MCP Server name and URL (e.g., `https://your-mcp-server.example.com/sse`)
3. Select **Connect** to initiate the OAuth 2.1 flow
4. A browser window will open to Taboola SSO—enter your credentials to obtain a bearer token used by Realize tools

**Cursor IDE**

⚠️ Temporarily unavailable — blocked by [Cursor OAuth redirect bug](https://forum.cursor.com/t/oauth-browser-redirect-not-triggered-for-http-based-mcp-servers/146988/6).

### SSE Endpoints

- `GET /.well-known/oauth-protected-resource` - RFC 9728 metadata
- `GET /.well-known/oauth-authorization-server` - RFC 8414 metadata (proxied)
- `GET /authorize` - Redirects to upstream auth server
- `POST /register` - RFC 7591 Dynamic Client Registration
- `POST /oauth/token` - Token endpoint (proxied to auth server)
- `POST /token` - Alternative token endpoint
- `GET /sse` - SSE connection endpoint (requires Bearer token)
- `POST /messages` - MCP protocol message handling

---

## Available Tools

### Account Management
- `search_accounts` - **[REQUIRED FIRST]** Find accounts and get account_id values for other tools (page_size max 10)

### Campaign Tools
- `get_all_campaigns` - List all campaigns for an account
- `get_campaign` - Get detailed campaign information
- `get_campaign_items` - List campaign creative items
- `get_campaign_item` - Get specific item details

### Reporting Tools (CSV Format)
- `get_top_campaign_content_report` - Top performing content with sorting & pagination
- `get_campaign_breakdown_report` - Campaign performance breakdown with sorting & pagination
- `get_campaign_history_report` - Historical campaign data with pagination
- `get_campaign_site_day_breakdown_report` - Site/day performance breakdown with sorting & pagination

### Authentication
- `get_auth_token` - Authenticate with Realize API
- `get_token_details` - Check token information

---

## Usage Examples

### Basic Usage

```
User: "Show me campaigns for Marketing Corp"
AI:
  1. Searches accounts for "Marketing Corp"
  2. Retrieves campaigns using the found account_id
  3. Returns campaign list with performance metrics
```

**Important**: All operations require getting `account_id` values from `search_accounts` first - never use numeric IDs directly.

### Find Account and List Campaigns

```
User: "Show campaigns for account 12345"
AI Process:
  Step 1: search_accounts("12345") → Returns account_id: "advertiser_12345_prod"
  Step 2: get_all_campaigns(account_id="advertiser_12345_prod")
  Result: List of campaigns with details
```

### Get Performance Report

```
User: "Get campaign performance for Marketing Corp last month"
AI Process:
  Step 1: search_accounts("Marketing Corp") → account_id: "mktg_corp_001"
  Step 2: get_campaign_breakdown_report(
    account_id="mktg_corp_001",
    start_date="2024-01-01",
    end_date="2024-01-31"
  )
  Result: CSV report with campaign metrics
```

### Top Performing Content

```
User: "Show top 20 performing content items"
AI Process:
  get_top_campaign_content_report(
    account_id="account_id_from_search",
    start_date="2024-01-01",
    end_date="2024-01-31",
    page_size=20,
    sort_field="spent",
    sort_direction="DESC"
  )
  Result: Top content sorted by spend
```

---

## Prerequisites

**Common:**
- Python 3.10+ (Python 3.11+ recommended)
- MCP-compatible client (Claude Desktop, Cursor, VS Code, etc.)

**For stdio transport:**
- Taboola Realize API credentials (`REALIZE_CLIENT_ID` and `REALIZE_CLIENT_SECRET`)

**For SSE transport:**
- OAuth Dynamic Client Registration credentials (`OAUTH_DCR_CLIENT_ID` and `OAUTH_DCR_CLIENT_SECRET`)
- Publicly accessible server URL for OAuth callbacks

---

## Important Workflow Notes

### Account ID Requirement

**All campaign and report tools require `account_id` values from `search_accounts`:**

✅ **Correct Workflow:**
```
1. search_accounts("company name" or "numeric_id")
2. Extract account_id from response
3. Use account_id in other tools
```

❌ **Incorrect:**
```
get_all_campaigns(account_id="12345")  # Numeric IDs won't work
```

### Report Features

- **CSV Format**: Reports return efficient CSV data with headers and pagination info
- **Pagination**: Default page_size=20, max=100 to prevent overwhelming responses
- **Sorting**: Available for most reports by `clicks`, `spent`, or `impressions`
- **Size Optimization**: Automatic truncation for large datasets

---

## Troubleshooting

Test the server manually:

```bash
REALIZE_CLIENT_ID=test REALIZE_CLIENT_SECRET=test realize-mcp-server
```

You should see: `INFO:realize.realize_server:Starting Realize MCP Server...`

---

## Detailed Documentation

For comprehensive information, see [design.md](design.md):

- **Recent Fixes & Version History** - Detailed release notes and upgrade instructions
- **Installation Options** - PyPI & Source installation with troubleshooting
- **Architecture & Design Principles** - Technical implementation details
- **Advanced Features** - CSV format, pagination, sorting, and optimization
- **Development Guide & Testing** - Setup, testing, and contribution guidelines
- **Comprehensive Troubleshooting** - Detailed solutions for common issues
- **Security Best Practices** - Credential management and operational security
- **Complete API Reference** - Full technical API documentation
- **Technology Stack Details** - Dependencies and system requirements

---

## License

Licensed under the Apache License 2.0. See [LICENSE](LICENSE) for details.

---

**Realize MCP Server** - Safe, efficient, read-only access to Taboola's advertising platform through natural language.