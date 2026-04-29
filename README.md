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

#### Write tools

These tools mutate campaign state and are annotated `destructiveHint: true` for MCP host UIs that gate writes.

**`create_campaign`** — Create a campaign. Returns the new campaign with `status=PAUSED` (will not serve until items are added and the campaign is activated). Targeting is not supported here; use the update tools below after creation.

```
account_id           (string, required)   From search_accounts
name                 (string, required)
marketing_objective  (string, required)   BRAND_AWARENESS | DRIVE_WEBSITE_TRAFFIC |
                                          LEADS_GENERATION | ONLINE_PURCHASES | MOBILE_APP_INSTALL
branding_text        (string, required)   Brand name shown with ads
spending_limit_model (string, required)   NONE | MONTHLY | ENTIRE
spending_limit       (number, optional)   Required when model = MONTHLY or ENTIRE
daily_cap            (number, optional)   Required when model = NONE
cpc                  (number, optional)   For BRAND_AWARENESS / DRIVE_WEBSITE_TRAFFIC
bid_strategy         (string, optional)   SMART | FIXED | TARGET_CPA | MAX_CONVERSIONS | MAX_VALUE
cpa_goal             (number, optional)   Required when bid_strategy = TARGET_CPA
start_date, end_date (string, optional)   YYYY-MM-DD
tracking_code        (string, optional)
cpc_cap              (number, optional)
comments             (string, optional)
daily_ad_delivery_model    (string, optional)   BALANCED | STRICT
traffic_allocation_mode    (string, optional)   OPTIMIZED (default) | EVEN
is_active                  (boolean, optional)  true to launch immediately, false or omit to start paused
```

**`update_campaign`** — Edit scalar fields on an existing campaign. Partial-merge: only supplied fields are updated; omitted fields keep their current value. Same 16 scalars accepted by `create_campaign`, plus `is_active` to pause/activate, all optional. At least one updatable field must be supplied. For non-scalar updates (geo, technology, audiences, schedule, conversion rules, publishers, contextual segments), use the dedicated tools below.

```
account_id           (string, required)   From search_accounts
campaign_id          (string, required)   Campaign to update
name                 (string, optional)
marketing_objective  (string, optional)   BRAND_AWARENESS | DRIVE_WEBSITE_TRAFFIC |
                                          LEADS_GENERATION | ONLINE_PURCHASES | MOBILE_APP_INSTALL
branding_text        (string, optional)
spending_limit_model (string, optional)   NONE | MONTHLY | ENTIRE
spending_limit       (number, optional)   Co-required when supplying spending_limit_model = MONTHLY or ENTIRE
daily_cap            (number, optional)   Co-required when supplying spending_limit_model = NONE
cpc                  (number, optional)
bid_strategy         (string, optional)   SMART | FIXED | TARGET_CPA | MAX_CONVERSIONS | MAX_VALUE
cpa_goal             (number, optional)   Co-required when supplying bid_strategy = TARGET_CPA
start_date, end_date (string, optional)   YYYY-MM-DD; if both supplied, end_date >= start_date
tracking_code        (string, optional)
cpc_cap              (number, optional)
comments             (string, optional)
daily_ad_delivery_model    (string, optional)   BALANCED | STRICT
traffic_allocation_mode    (string, optional)   OPTIMIZED (default) | EVEN
is_active                  (boolean, optional)  true to activate, false to pause
```

**`update_campaign_geo_classic`** — Update one classic geo dimension on a campaign. Use when `get_campaign` shows no `geo_targeting` field. Sub-dimension mutex: at most one of `region | dma | city | postal_code` may be set at a time — clear the current dim with `type=ALL` before setting a new one.

```
account_id  (string, required)
campaign_id (string, required)
dimension   (string, required)   country | region | dma | city | postal_code
targeting   (object, required)   {type: INCLUDE | EXCLUDE | ALL, value: [string]}
                                 value=[] required when type=ALL
```

**`update_campaign_geo_advanced`** — Update geo using the advanced (MultiTargeting) shape. Use when `get_campaign` returns a populated `geo_targeting`. Sending advanced on a classic-stored campaign migrates the campaign one-way to advanced storage and clears classic fields.

```
account_id    (string, required)
campaign_id   (string, required)
geo_targeting (object, required)
  state  (string)   ALL | EXISTS                 ALL with value=[] clears all geo
  value  (array)    Rules; each rule:
                    {type: INCLUDE | EXCLUDE,
                     value: [{country, region, dma, city, postal_code}]}
                    A vector may set one dim or mix dims (e.g. country=US AND region=CA → California).
```

**`update_campaign_techno`** — Update one technology targeting dimension on a campaign: device platform, operating system, browser, or network connection type. Outer wrapper is the same `Targeting<T>` shape as classic geo; the `value` items are strings for `platform | browser | connection_type` and `{os_family, sub_categories?}` objects for `os`.

```
account_id  (string, required)
campaign_id (string, required)
dimension   (string, required)   platform | os | browser | connection_type
targeting   (object, required)
  type   (string)   INCLUDE | EXCLUDE | ALL       value=[] required when type=ALL
  value  (array)    Strings for platform|browser|connection_type
                    (e.g. ["DESK","PHON"], ["Chrome"], ["WIFI"]).
                    Objects for os: [{os_family, sub_categories?}]
                    (e.g. [{os_family:"iOS", sub_categories:["iOS_16","iOS_17"]}]).
                    Omit sub_categories to target the entire family.
```

**`update_campaign_my_audiences`** — Update first-party + custom audience targeting on a campaign. Full-replace `{collection: [rules]}`: send the full desired targeting set on each call. Lookalike audiences live in `update_campaign_lookalike_audience`.

```
account_id   (string, required)
campaign_id  (string, required)
my_audiences (object, required)
  collection (array)   Rules; each rule:
                       {collection: [<integer audience_id>, ...],
                        type: INCLUDE | EXCLUDE}
                       Send {collection: []} to clear all audience targeting.
```

**`update_campaign_lookalike_audience`** — Update lookalike audience targeting (CRM and pixel). Full-replace. Only `INCLUDE` is supported (server rejects EXCLUDE/ALL); at most one block. `similarity_level` is a percentage; allowed values depend on subtype (CRM: 5/10/15/20/25; pixel: 5) — the server resolves the subtype from `rule_id` and rejects mismatches. Predictive (PBP) lookalikes are not supported via this MCP server (platform creation-only; no creation-time field exposed). Send `{collection: []}` to clear.

```
account_id          (string, required)
campaign_id         (string, required)
lookalike_audience  (object, required)
  collection (array, max 1 block)   At most one block; each block:
                                    {type: INCLUDE,
                                     collection: [{rule_id: <int>,
                                                   similarity_level: <int>}]}
                                    Send {collection: []} to clear.
```

**`update_campaign_schedule`** — Update a campaign's activity schedule (dayparting). `mode=ALWAYS` runs continuously; `mode=CUSTOM` accepts INCLUDE/EXCLUDE rules per day-of-week + hour range, in the supplied IANA time zone. Server auto-fills missing days as INCLUDE 0–24, so callers do not need to enumerate all seven days.

```
account_id  (string, required)
campaign_id (string, required)
schedule    (object, required)
  mode       (string)   ALWAYS | CUSTOM
  time_zone  (string)   IANA name (e.g. "America/New_York"). Required when mode=CUSTOM.
  rules      (array)    Required when mode=CUSTOM; omit when mode=ALWAYS.
                        Each rule: {type: INCLUDE | EXCLUDE,
                                    day:  MONDAY..SUNDAY,
                                    from_hour:  int 0-23,
                                    until_hour: int 1-24, must be > from_hour}
```

**`update_campaign_conversion_rules`** — Replace the conversion rules attached to a campaign. Full-replace: the supplied list overwrites current attachments wholesale. Send `[]` to detach all. To add or remove a single rule, first read the campaign with `get_campaign`, modify the list locally, then send the merged result. Rule authoring lives in the Realize UI (Conversions section); this tool only attaches existing rule IDs.

```
account_id        (string, required)   From search_accounts
campaign_id       (string, required)
conversion_rules  (array, required)    Full-replace list of rule references.
                                       Each item: {id: <integer_rule_id>}
                                       Send [] to detach all. Wire payload wraps the
                                       list under `rules` to match get_campaign shape.
```

**`update_campaign_publishers`** — Update publisher-level targeting on a campaign: which publishers run (`publisher_targeting`), which publisher groups (`publisher_groups_targeting`), and per-publisher CPC bid modifiers (`publisher_bid_modifier`). Send any subset of the three fields; at least one is required. Targeting blocks use the same `Targeting<String>` shape as classic geo, but values are publisher / group **names** (the server resolves names to IDs). The bid modifier is full-replace: omit a publisher to drop its modifier, send `values: []` to clear all. To incrementally add/remove a single entry, first read the campaign with `get_campaign`, modify locally, then send the merged result.

```
account_id                  (string, required)   From search_accounts
campaign_id                 (string, required)
publisher_targeting         (object, optional)   {type: INCLUDE | EXCLUDE | ALL,
                                                  value: [<publisher_name>, ...]}
                                                  value=[] when type=ALL.
publisher_groups_targeting  (object, optional)   {type: INCLUDE | EXCLUDE | ALL,
                                                  value: [<group_name>, ...]}
                                                  value=[] when type=ALL.
publisher_bid_modifier      (object, optional)   {values: [{target: <publisher_name>,
                                                            cpc_modification: <number>}]}
                                                  Full-replace; values=[] clears all.
                                                  cpc_modification is a CPC multiplier
                                                  (e.g. 1.25 = +25%, 0.8 = -20%).
                                                  Targets must be unique and finite.
```

**`update_campaign_contextual_segments`** — Update contextual segment targeting on a campaign. Full-replace `{collection: [rules]}`: the supplied object overwrites current targeting wholesale. Send `{collection: []}` to clear all contextual targeting. At most one `INCLUDE` block and one `EXCLUDE` block; segment IDs are integers (e.g. `1900004`), authored in the Realize UI or discoverable via `list_account_contextual_segments`.

```
account_id          (string, required)   From search_accounts
campaign_id         (string, required)
contextual_segments (object, required)   {collection: [{type, collection}]}
                                          type: INCLUDE | EXCLUDE
                                          inner collection: [<segment_id_int>, ...]
                                          Send {collection: []} to clear all.
```

### Resource Discovery

These read-only tools surface the valid values that the campaign create/update tools accept (country codes, OS families, audience IDs, conversion rule IDs, etc.) so the LLM can construct correct payloads in-band rather than guessing or asking the operator to look things up.

**`list_realize_resource`** — Look up a global Realize platform vocabulary. Picks from a fixed set of `resource` names; some require a parent argument under `args` (regions/dma/cities/postal_codes need `country_code`; operating_system_versions needs `os_family`). Response is a flat list of valid values.

```
resource (string, required)   countries | regions | dma | cities | postal_codes |
                              platforms | operating_systems | operating_system_versions |
                              browsers | connection_types | marketing_objectives |
                              bid_strategies | spending_limit_models | time_zones
args     (object, optional)   {country_code: "US"} for regions/dma/cities/postal_codes
                              {os_family: "iOS"} for operating_system_versions
```

**`list_account_audiences`** — List first-party + custom + lookalike audiences on an account. Use the IDs as inputs to `update_campaign_my_audiences` (custom IDs) or `update_campaign_lookalike_audience` (lookalike `rule_id`s).

```
account_id (string, required)
```

**`list_account_conversion_rules`** — List conversion rules defined on an account. Use the rule IDs in `update_campaign_conversion_rules`.

```
account_id (string, required)
```

**`list_account_publishers`** — List publishers an account is allowed to target. Optional `search_text` narrows the list (helpful when an account has thousands of publishers). Use the resulting names in `update_campaign_publishers`. Publisher-group names are *not* discoverable in-band.

```
account_id  (string, required)
search_text (string, optional)   Substring filter on publisher name.
```

**`list_account_contextual_segments`** — List contextual segments available on an account. Optional `country_codes` (comma-separated ISO-2) narrows segments to those served in the given markets. Use the segment IDs in `update_campaign_contextual_segments`.

```
account_id    (string, required)
country_codes (string, optional)   e.g. "US,CA"
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

### Authentication (stdio only)

These tools are only available in stdio mode, where the server manages its own client credentials. In Streamable HTTP mode, authentication is handled at the transport layer via OAuth 2.1 so these tools are excluded.

**`get_auth_token`** — Authenticate with Realize API using client credentials (`REALIZE_CLIENT_ID`/`REALIZE_CLIENT_SECRET`).

**`get_token_details`** — Get details about the current authentication token.

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
