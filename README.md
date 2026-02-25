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

### Server Installation

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

### Server Installation

```bash
git clone https://github.com/taboola/realize-mcp.git
cd realize-mcp

# Set required credentials
export OAUTH_DCR_CLIENT_ID=your_dcr_client_id
export OAUTH_DCR_CLIENT_SECRET=your_dcr_client_secret

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
- `GET /.well-known/oauth-authorization-server` - RFC 8414 metadata (registration_endpoint rewritten)
- `POST /register` - RFC 7591 Dynamic Client Registration
- `GET /sse` - SSE connection endpoint (requires Bearer token)
- `POST /messages` - MCP protocol message handling
- `GET /health` - Health check endpoint for Kubernetes probes

---

## Tools Reference

> All 12 tools are **read-only**. No create/update/delete operations.

### Authentication

**`get_auth_token`** — Authenticate with Realize API.
No parameters. In stdio mode, uses client credentials (`REALIZE_CLIENT_ID`/`REALIZE_CLIENT_SECRET`). In SSE mode, confirms the OAuth 2.1 session token is active.

**`get_token_details`** — Get details about the current authentication token.
No parameters. Works with both stdio (client credentials token) and SSE (OAuth session token).

### Account Management

**`search_accounts`** — Search accounts by numeric ID or text query. **Call this first** to get `account_id` values needed by all other tools.

```
query       (string, required)            Cannot be empty. Numeric = exact ID; text = fuzzy name
page        (integer, default: 1)         min: 1
page_size   (integer, default: 10)        min: 1, max: 10 (hard cap)
```

### Campaign Management

All campaign tools require `account_id` (string from `search_accounts`), not a raw numeric ID.
No pagination — all results returned in a single response.

**`get_all_campaigns`** — List all campaigns for an account.

```
account_id  (string, required)
```

**`get_campaign`** — Get specific campaign details.

```
account_id  (string, required)
campaign_id (string, required)
```

**`get_campaign_items`** — Get all items/creatives for a campaign.

```
account_id  (string, required)
campaign_id (string, required)
```

**`get_campaign_item`** — Get a specific campaign item's details.

```
account_id  (string, required)
campaign_id (string, required)
item_id     (string, required)
```

### Reporting (CSV Format)

All report tools return CSV with a summary header. Every report requires these parameters:

```
account_id  (string, required)            From search_accounts
start_date  (string, required)            Format: YYYY-MM-DD
end_date    (string, required)            Format: YYYY-MM-DD
page        (integer, default: 1)         min: 1
page_size   (integer, default: 20)        min: 1, max: 100
```

Some reports also support sorting and filtering:

```
sort_field      (string, optional)        Allowed: clicks, spent, impressions
sort_direction  (string, default: DESC)   Allowed: ASC, DESC
filters         (object, optional)        JSON object with string values only
```

**`get_top_campaign_content_report`** — Top performing campaign content.
Supports: shared params + sort.

**`get_campaign_breakdown_report`** — Campaign performance breakdown.
Supports: shared params + sort + filters.

**`get_campaign_history_report`** — Historical campaign data.
Supports: shared params only (no sort, no filters).

**`get_campaign_site_day_breakdown_report`** — Site/day performance breakdown.
Supports: shared params + sort + filters.

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
- `MCP_SERVER_SCHEME` — defaults to `https`. Set to `http` for local dev without TLS.

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