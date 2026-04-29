# Realize MCP Server

A Model Context Protocol (MCP) server for Taboola's Realize API. Provides read access to accounts, campaigns, items, and reports, plus write access to create and update campaigns (including targeting, scheduling, audiences, and conversion rules). Install with stdio transport for single-user local use, or Streamable HTTP transport for multi-user deployment.

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0) [![Python](https://img.shields.io/badge/Python-3.10+-green.svg)](https://python.org) [![MCP](https://img.shields.io/badge/MCP-Compatible-orange.svg)](https://modelcontextprotocol.io/) [![Latest Version][mdversion-button]][md-pypi]

[mdversion-button]: https://img.shields.io/pypi/v/realize-mcp.svg
[md-pypi]: https://pypi.org/project/realize-mcp/

---

## Quick Start (Remote MCP)

Connect to the hosted Realize MCP server using [Streamable HTTP](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports#streamable-http) transport with OAuth 2.1. Multi-user, stateless, no local install required.

**Cursor IDE / Claude Desktop** — Add to your MCP client config:

```json
{
  "mcpServers": {
    "realize-mcp": {
      "url": "https://mcp.realize.com/mcp"
    }
  }
}
```

**Claude Desktop (UI)**

1. Go to Settings → Connectors → Add Custom Connector
2. Enter the MCP Server name and URL: `https://mcp.realize.com/mcp`
3. Select **Connect** to initiate the OAuth 2.1 flow
4. A browser window will open to Taboola SSO—enter your credentials to obtain a bearer token used by Realize tools

**Claude Code (CLI)**

```bash
claude mcp add --transport http --callback-port 3000 realize-mcp https://mcp.realize.com/mcp
```

---

## Tools Reference

All tools (except `search_accounts`) require an `account_id` returned by `search_accounts` — never a raw numeric ID. Write tools are annotated `destructiveHint: true`.

### Accounts

- **`search_accounts`** — Search accounts by numeric ID (exact) or text (fuzzy). Call first to obtain `account_id`.

### Campaigns (read)

- **`get_all_campaigns`** — List all campaigns for an account.
- **`get_campaign`** — Get a campaign's full details.
- **`get_campaign_items`** — List items/creatives on a campaign.
- **`get_campaign_item`** — Get one item's details.

### Campaigns (write)

- **`create_campaign`** — Create a campaign (returns `status=PAUSED`, no targeting; use update tools after).
- **`update_campaign`** — Partial-merge update of campaign scalar fields (name, bidding, budget, schedule dates, `is_active`, etc.).
- **`update_campaign_geo_classic`** — Set one classic geo dimension (`country | region | dma | city | postal_code`); sub-dim mutex.
- **`update_campaign_geo_advanced`** — Set advanced (MultiTargeting) geo; one-way migration from classic.
- **`update_campaign_techno`** — Set one technology dimension (`platform | os | browser | connection_type`).
- **`update_campaign_my_audiences`** — Full-replace first-party + custom audience targeting.
- **`update_campaign_lookalike_audience`** — Full-replace lookalike (CRM/pixel) targeting; INCLUDE only, max one block.
- **`update_campaign_schedule`** — Set activity schedule (`ALWAYS`, or `CUSTOM` dayparting with IANA time zone).
- **`update_campaign_conversion_rules`** — Full-replace attached conversion rule IDs (authoring in Realize UI).
- **`update_campaign_publishers`** — Update publisher targeting, group targeting, and per-publisher CPC bid modifiers.
- **`update_campaign_contextual_segments`** — Full-replace contextual segment targeting (INCLUDE/EXCLUDE blocks).

### Resource Discovery

- **`list_realize_resource`** — Look up Realize platform vocabulary (countries, regions, dma, cities, postal codes, platforms, OS, OS versions, browsers, connection types, marketing objectives, bid strategies, spending limit models, time zones). Some require `args` (e.g. `country_code` for regions; `os_family` for OS versions).

### Reporting (CSV)

Shared params: `account_id`, `start_date`, `end_date` (`YYYY-MM-DD`), `page` (default 1), `page_size` (default 20, max 100).

- **`get_top_campaign_content_report`** — Top performing content. Supports sort.
- **`get_campaign_breakdown_report`** — Campaign performance breakdown. Supports sort + filters.
- **`get_campaign_history_report`** — Historical campaign data. Shared params only.
- **`get_campaign_site_day_breakdown_report`** — Site/day performance breakdown. Supports sort + filters.

Sort: `sort_field` (`clicks | spent | impressions`), `sort_direction` (`ASC | DESC`, default `DESC`). Filters: object with string values only.

### Authentication (stdio only)

Excluded in Streamable HTTP mode (auth handled by OAuth 2.1 at transport layer).

- **`get_auth_token`** — Authenticate via `REALIZE_CLIENT_ID` / `REALIZE_CLIENT_SECRET`.
- **`get_token_details`** — Inspect current token.

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

### Report Features

- **CSV Format**: Reports return efficient CSV data with headers and pagination info
- **Pagination**: Default page_size=20, max=100 to prevent overwhelming responses
- **Sorting**: Available for most reports by `clicks`, `spent`, or `impressions`
- **Size Optimization**: Automatic truncation for large datasets

---

## Prometheus Metrics

Enabled by default (`METRICS_ENABLED=true`). Served on a dedicated port (default `8092`, configurable via `METRICS_PORT`) in Streamable HTTP mode.

| Metric | Type | Labels |
|--------|------|--------|
| `realize_mcp_http_requests_total` | Counter | `method`, `endpoint`, `http_status` |
| `realize_mcp_http_request_latency_seconds` | Histogram | `endpoint` |
| `realize_mcp_tool_calls_total` | Counter | `tool_name`, `status` |
| `realize_mcp_tool_call_latency_seconds` | Histogram | `tool_name` |
| `realize_mcp_client_connections_total` | Counter | `client_name`, `client_version` |
| `realize_mcp_api_requests_total` | Counter | `method`, `endpoint_pattern`, `http_status` |
| `realize_mcp_api_request_latency_seconds` | Histogram | `method`, `endpoint_pattern` |
| `realize_mcp_api_errors_total` | Counter | `method`, `endpoint_pattern`, `error_type` |

---

## Local Setup

Run the MCP server locally if you prefer to manage your own credentials or host the server yourself.

### Prerequisites

- Python 3.10+ (Python 3.11+ recommended)
- MCP-compatible client (Claude Desktop, Cursor, VS Code, etc.)

### Option A: Stdio Transport (single-user, local)

Standard MCP transport for local clients. The server runs on your machine and uses server-side credentials for Taboola API authentication.

**Prerequisites:** Taboola Realize API credentials (`REALIZE_CLIENT_ID` and `REALIZE_CLIENT_SECRET`)

**Install:**

```bash
pip install realize-mcp
```

**Cursor IDE** - Add to Settings → Tools & MCP:

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

**Claude Code (CLI)**

```bash
claude mcp add realize-mcp --transport stdio -e REALIZE_CLIENT_ID=your_client_id -e REALIZE_CLIENT_SECRET=your_client_secret -- realize-mcp-server
```

### Option B: Self-Hosted Streamable HTTP

Run the Streamable HTTP transport yourself (multi-user via OAuth 2.1, stateless, k8s-friendly).

**Prerequisites:**
- OAuth Dynamic Client Registration client ID (`OAUTH_DCR_CLIENT_ID`)
- Optional: `OAUTH_SERVER_URL` (defaults to `https://authentication.taboola.com/authentication`)
- Publicly accessible server URL for OAuth callbacks
- `MCP_SERVER_SCHEME` — defaults to `https`. Set to `http` for local dev without TLS.

**Install:**

```bash
pip install realize-mcp
```

**Start the server:**

```bash
MCP_TRANSPORT=streamable-http OAUTH_DCR_CLIENT_ID=your_dcr_client_id realize-mcp-server
```

**Client config** (point to your self-hosted URL):

```json
{
  "mcpServers": {
    "realize-mcp": {
      "type": "streamable-http",
      "url": "https://your-mcp-server.example.com/mcp"
    }
  }
}
```

**Endpoints:**

- `GET /.well-known/oauth-protected-resource` - RFC 9728 Protected Resource Metadata (supports path-based discovery)
- `GET /.well-known/oauth-authorization-server` - RFC 8414 metadata (registration_endpoint rewritten)
- `POST /register` - RFC 7591 Dynamic Client Registration
- `POST|GET|DELETE /mcp` - MCP Streamable HTTP endpoint (requires Bearer token)
- `GET /health` - Health check endpoint for Kubernetes probes
- `GET /` on port 8092 - Prometheus metrics endpoint (separate port)

### Troubleshooting

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

**Realize MCP Server** - Safe, efficient, access to Taboola's advertising platform through natural language.
