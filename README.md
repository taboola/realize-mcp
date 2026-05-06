# Realize MCP Server

A Model Context Protocol (MCP) server providing read and write access to Taboola's Realize API. Enables AI assistants to analyze campaigns, retrieve performance data, generate reports, and manage campaigns and items through natural language. Install with stdio transport for single-user local use, or Streamable HTTP transport for multi-user deployment.

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

### Account Management

**`search_accounts`** — Search accounts by numeric ID or text query. **Call this first** to get `account_id` values needed by all other tools. Results include `currency`, `country`, and `time_zone_name` so the LLM can pick the right budget amounts and timezone.

```
query        (string, required)            Cannot be empty. Numeric = exact ID; text = fuzzy name
page         (integer, default: 1)         min: 1
page_size    (integer, default: 10)        min: 1, max: 10 (hard cap)
```

### Campaign Management

A campaign holds budget, bidding, schedule, and targeting. It contains items.

**`list_campaigns`** — List all campaigns for an account.

```
account_id   (string, required)
```

**`get_campaign`** — Get specific campaign details.

```
account_id   (string, required)
campaign_id  (string, required)
```

#### Campaign write tools (`create_campaign`, `update_campaign`)

Both tools accept the same scalars and targeting blocks. Scalars partial-merge; targeting blocks full-replace within block. New campaigns ship paused unless `is_active=true` is sent.

Required differs:

```
create_campaign:  account_id, name, marketing_objective, branding_text, spending_limit_model, bid_strategy
update_campaign:  account_id, campaign_id
```

Scalars (all optional on update; the create-required ones above are mandatory on create):

```
name                     (string)
marketing_objective      (string enum)        BRAND_AWARENESS | DRIVE_WEBSITE_TRAFFIC | LEADS_GENERATION | ONLINE_PURCHASES | MOBILE_APP_INSTALL
branding_text            (string)             Brand name shown with ads
spending_limit_model     (string enum)        NONE | MONTHLY | ENTIRE
spending_limit           (number)             Budget amount in account's default currency
daily_cap                (number)             Daily spend cap
bid_strategy             (string enum)        SMART | FIXED | TARGET_CPA | MAX_CONVERSIONS | MAX_VALUE
cpc                      (number)             Fixed cost per click (FIXED only)
cpa_goal                 (number)             Target cost per acquisition (TARGET_CPA only)
cpc_cap                  (number)             Upper bound on bids
start_date               (string)             YYYY-MM-DD
end_date                 (string)             YYYY-MM-DD
tracking_code            (string)             Query string appended to item URLs
comments                 (string)             Internal notes
daily_ad_delivery_model  (string enum)        BALANCED | STRICT
traffic_allocation_mode  (string enum)        OPTIMIZED | EVEN
is_active                (boolean)            true to launch, false to pause
```

Targeting blocks (all `object`, optional, full-replace within block):

```
country_targeting              Classic country (codes from search_geos dimension=countries)
region_country_targeting       Classic region (codes from search_geos dimension=regions)
dma_country_targeting          Classic DMA — US-only (codes from search_geos dimension=dma)
city_targeting                 Classic city (codes from search_geos dimension=cities)
postal_code_targeting          Classic postal code (codes from search_geos dimension=postal_codes)
platform_targeting             DESK | PHON | TBLT | TV | OTHR
os_targeting                   OS family + version (versions via search_techno)
browser_targeting              Browser names from search_techno dimension=browsers
connection_type_targeting      WIFI
activity_schedule              Dayparting (time_zone via list_time_zones)
conversion_rules               Conversion rule attachments (rules via search_conversion_rules)
publisher_targeting            Publisher allow/block-list (search_publishers)
publisher_bid_modifier         Per-publisher CPC bid modifier
contextual_segments_targeting  Contextual segments (search_contextual_segments)
audiences_targeting            First-party + custom audiences (search_audiences)
lookalike_audience_targeting   Lookalike audiences (search_lookalike_audiences)
```

### Campaign Items

An item is a creative (headline, image, URL) served under a campaign. Standard `ITEM` type only — RSS, motion ads, performance video, display, hierarchy carousel, and the Creative Library are not supported.

**`list_campaign_items`** — List items for a campaign.

```
account_id   (string, required)
campaign_id  (string, required)
```

**`get_campaign_item`** — Get a specific item.

```
account_id   (string, required)
campaign_id  (string, required)
item_id      (string, required)
```

**`create_campaign_item`** — Create an item on a campaign. Omit `title` / `description` / `thumbnail_url` to trigger a server-side crawl of `url`.

```
account_id     (string, required)
campaign_id    (string, required)
url            (string, required)            Landing URL
title          (string)                      Headline
description    (string)                      Body
thumbnail_url  (string)                      Image URL
branding_text  (string)
cta            (object)                      {cta_type} — values from list_cta_types
```

**`update_campaign_item`** — Update specific fields on an item. Send `[]` for `verification_pixel` / `viewability_tag` to clear.

```
account_id          (string, required)
campaign_id         (string, required)
item_id             (string, required)
url                 (string)
title               (string)
description         (string)
thumbnail_url       (string)
branding_text       (string)
is_active           (boolean)                Pause/resume
cta                 (object)                 {cta_type}
verification_pixel  (object)                 Tracking pixels (full-replace within block)
viewability_tag     (object)                 Viewability tag (full-replace within block)
```

Editability: items in CRAWLING / PENDING_APPROVAL accept full edits; RUNNING / PAUSED accept only `is_active` toggles plus minor metadata; REJECTED items cannot be edited (recreate).

### Discovery

Use these to populate campaign and item targeting fields with valid values.

**`search_geos`** — Countries, regions, DMAs, cities, postal codes. Returns `{code, name}` pairs; use the `code` field for targeting.

```
dimension     (string enum, required)       countries | regions | dma | cities | postal_codes
country_code  (string)                      Required for regions / dma / cities / postal_codes
```

**`search_techno`** — OS versions and browsers.

```
dimension  (string enum, required)          operating_system_versions | browsers
os_family  (string)                         Required for operating_system_versions
```

**`search_audiences`** — First-party and custom audiences for an account.

```
account_id              (string, required)
country_codes           (string)
country_targeting_type  (string enum)       ALL | INCLUDE | EXCLUDE
```

**`search_lookalike_audiences`** — CRM / pixel / PBP lookalike audiences.

```
account_id    (string, required)
country_code  (string)
```

**`search_contextual_segments`** — Contextual segments.

```
account_id              (string, required)
country_codes           (string)
country_targeting_type  (string enum)       ALL | INCLUDE | EXCLUDE
```

**`search_publishers`** — Publishers an account may target.

```
account_id     (string, required)
query          (string, required)
publisher_ids  (array)
page           (integer, default: 1)        min: 1
page_size      (integer, default: 10)       min: 1, max: 50
```

**`search_conversion_rules`** — Conversion rules attached to an account.

```
account_id  (string, required)
```

**`list_time_zones`** — IANA time-zone names for `activity_schedule.time_zone`. No parameters.

**`list_cta_types`** — `cta.cta_type` values for `create_campaign_item` / `update_campaign_item`. No parameters.

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
sort_field      (string enum)             clicks | spent | impressions
sort_direction  (string enum, default: DESC)   ASC | DESC
filters         (object)                  JSON object with string values only
```

**`get_top_campaign_content_report`** — Top performing campaign content.
Supports: shared params + sort.

**`get_campaign_breakdown_report`** — Campaign performance breakdown.
Supports: shared params + sort + filters.

**`get_campaign_history_report`** — Historical campaign data.
Supports: shared params only (no sort, no filters).

**`get_campaign_site_day_breakdown_report`** — Site/day performance breakdown.
Supports: shared params + sort + filters.

### Authentication (stdio only)

These tools are only available in stdio mode. In Streamable HTTP mode authentication is handled at the transport layer via OAuth 2.1, so they are excluded.

**`get_auth_token`** — Authenticate via `REALIZE_CLIENT_ID` / `REALIZE_CLIENT_SECRET`.

**`get_token_details`** — Inspect the current token.

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

### Update a Campaign Budget

```
User: "Bump the daily cap on Marketing Corp's Spring Sale campaign to $500"
AI Process:
  Step 1: search_accounts("Marketing Corp") → account_id: "mktg_corp_001"
  Step 2: list_campaigns(account_id="mktg_corp_001") → find Spring Sale → campaign_id: "12345678"
  Step 3: update_campaign(
    account_id="mktg_corp_001",
    campaign_id="12345678",
    daily_cap=500
  )
  Result: Campaign updated; other fields and targeting untouched
```

### Create a Campaign Item

```
User: "Add a new ad to campaign 12345678 pointing at example.com/landing with a Shop Now CTA"
AI Process:
  Step 1: search_accounts(...) → account_id: "mktg_corp_001"
  Step 2: list_cta_types() → confirm "SHOP_NOW" is a valid cta_type
  Step 3: create_campaign_item(
    account_id="mktg_corp_001",
    campaign_id="12345678",
    url="https://example.com/landing",
    cta={"cta_type": "SHOP_NOW"}
  )
  Result: Item created; title/description/thumbnail server-crawled from url
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
