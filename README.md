# Realize MCP Server

A Model Context Protocol (MCP) server providing read and write access to Taboola's Realize API. Enables AI assistants to analyze campaigns, retrieve performance data, generate reports, and manage campaigns and items through natural language. Runs as a Streamable HTTP server with OAuth 2.1 — use the hosted server, or run it yourself via Docker.

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0) [![Python](https://img.shields.io/badge/Python-3.10+-green.svg)](https://python.org) [![MCP](https://img.shields.io/badge/MCP-Compatible-orange.svg)](https://modelcontextprotocol.io/)

---

## Quick Start (Remote MCP)

Connect to the hosted Realize MCP server using [Streamable HTTP](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports#streamable-http) transport with OAuth 2.1. Multi-user, stateless, no local install required.

Pick the section for your client:

### Claude Desktop

Two options — use the UI for the simplest setup, or the config file if you prefer to manage MCP servers as code.

**Option 1 — UI (recommended):**

1. Go to Settings → Connectors → Add Custom Connector
2. Enter the MCP Server name and URL: `https://mcp.realize.com/mcp`
3. Select **Connect** to initiate the OAuth 2.1 flow
4. A browser window will open to Taboola SSO—enter your credentials to obtain a bearer token used by Realize tools

**Option 2 — config file:**

Prerequisite: Node.js 18+ (provides `npx`). Install from [nodejs.org](https://nodejs.org) or run `brew install node`.

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "realize-mcp": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://mcp.realize.com/mcp", "3000"]
    }
  }
}
```

### Claude Code (CLI)

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

**`list_campaigns`** — List campaigns for an account (one page per call).

```
account_id   (string, required)
page         (integer, default: 1)         min: 1
page_size    (integer, default: 10)        min: 1, max: 10 (hard cap)
```

**`get_campaign`** — Get specific campaign details.

```
account_id   (string, required)
campaign_id  (string, required)
```

**`get_campaign_reach_estimate`** — Estimate reach for a hypothetical campaign configuration before launch. Forecast from targeting + optional bid/budget, not from historical performance. Returns lower/upper bounds for impressions and/or monthly unique users.

```
account_id        (string, required)
campaign          (object, required)              Same targeting blocks as create_campaign / update_campaign below. Reach narrows as more inputs are added: targeting only → audience reach; + cpc (pricing_model=CPC) → narrowed by bid competitiveness; + spending_limit or daily_cap → additionally capped by impressions the budget can afford.
estimation_types  (array of string, optional)     IMPRESSIONS | MONTHLY_USERS — omit for both
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
pricing_model            (string enum)        CPC | VCPM   (default CPC; VCPM requires bid_strategy=FIXED)
bid_strategy             (string enum)        SMART | FIXED | TARGET_CPA | MAX_CONVERSIONS | MAX_VALUE
cpc                      (number)             Bid amount in account's default currency (per-click for CPC; per-1000-viewable-impressions for VCPM)
cpa_goal                 (number)             Target cost per acquisition (TARGET_CPA only)
cpc_cap                  (number)             Upper bound on bids
start_date               (string)             YYYY-MM-DD
end_date                 (string)             YYYY-MM-DD
tracking_code            (string)             Query string appended to item URLs
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

### Items

An item is a creative served under a campaign. Two types are supported: native (URL-crawled or manual headline/image/URL) and display (3P ad tag or 1P Realize-hosted asset).

**`list_items`** — List items for a campaign.

```
account_id   (string, required)
campaign_id  (string, required)
```

**`get_item`** — Get a specific item.

```
account_id   (string, required)
campaign_id  (string, required)
item_id      (string, required)
```

**`create_native_item`** — Create a native item on a campaign.

```
account_id     (string, required)
campaign_id    (string, required)
url            (string, required)            Landing URL
title          (string, required)            Headline
description    (string, required)            Body
thumbnail_url  (string, required)            Image URL
branding_text  (string)
creative_name  (string)                      Human-readable creative label shown in the Realize UI
cta            (object)                      {cta_type} — values from list_cta_types
```

**`update_native_item`** — Update specific fields on a native item. Send `[]` for `verification_pixel` / `viewability_tag` to clear.

```
account_id          (string, required)
campaign_id         (string, required)
item_id             (string, required)
url                 (string)
title               (string)
description         (string)
thumbnail_url       (string)
branding_text       (string)
creative_name       (string)                 Human-readable creative label shown in the Realize UI
is_active           (boolean)                Pause/resume
cta                 (object)                 {cta_type}
verification_pixel  (object)                 Tracking pixels (full-replace within block)
viewability_tag     (object)                 Viewability tag (full-replace within block)
```

Editability: items in PENDING_APPROVAL accept full edits; RUNNING / PAUSED accept only `is_active` toggles plus minor metadata; REJECTED items cannot be edited (recreate).

**`create_display_item`** — Create a display item on a campaign. Send exactly one of `ad_tag` (3P third-party tag) or `asset_url` (1P Realize-hosted asset).

```
account_id     (string, required)
campaign_id    (string, required)
url            (string, required)            Landing URL
creative_name  (string, required)            Human-readable creative label shown in the Realize UI
ad_tag         (string)                      3P tag (raw HTML/JS). Pair with `dimensions`.
dimensions     (array of {width,height})     Required with `ad_tag`; rejected with `asset_url`.
asset_url      (string)                      1P hosted asset URL (image/video/HTML5 zip). Realize ingests by file extension.
```

**`update_display_item`** — Update fields on a display item. Send `[]` for `verification_pixel` / `viewability_tag` to clear.

```
account_id          (string, required)
campaign_id         (string, required)
item_id             (string, required)
url                 (string)
creative_name       (string)
is_active           (boolean)                Pause/resume
ad_tag              (string)                 Swap 3P tag; requires `dimensions`.
dimensions          (array of {width,height})
asset_url           (string)                 Swap 1P hosted asset (re-ingest by file extension).
verification_pixel  (object)                 Tracking pixels (full-replace within block)
viewability_tag     (object)                 Viewability tag (full-replace within block)
```

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

**`list_cta_types`** — `cta.cta_type` values for `create_native_item` / `update_native_item`. No parameters.

### Reporting (CSV Format)

All report tools return CSV with a summary header. Every report requires these parameters:

```
account_id  (string, required)            From search_accounts
start_date  (string, required)            Format: YYYY-MM-DD
end_date    (string, required)            Format: YYYY-MM-DD
```

Paginated reports also accept:

```
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
Supports: shared params only. Not paginated and not sortable — returns the full result set in a single call, fixed-sorted by revenue DESC (the `spent` column), capped at top 1000 server-side.

**`get_campaign_breakdown_report`** — Campaign performance breakdown.
Supports: shared params + pagination + sort + filters.

**`get_campaign_history_report`** — Historical campaign data.
Supports: shared params + pagination (no sort, no filters).

**`get_campaign_site_day_breakdown_report`** — Site/day performance breakdown.
Supports: shared params + pagination + sort + filters.

#### Data grain & interpretation

Reports return flattened rows. Each report has a fixed **row grain** (the composite key that makes a row unique). The same `site_id` can appear under several campaigns, so rows must be read at their grain — not merged by a single id. Column names below are the literal CSV headers (note: campaign id is `campaign` in the performance reports but `campaign_id` in the history report).

```
get_campaign_breakdown_report             campaign
get_campaign_site_day_breakdown_report    (campaign, site_id, date)
get_top_campaign_content_report           (campaign, item)
get_campaign_history_report               (campaign_id, change_time, id)   # audit log, not metrics
```

Don't rely on column position — grain/key columns aren't guaranteed to lead or be adjacent. Each response names the row key explicitly on a `Row key:` line, the authoritative set of columns that makes a row unique.

**Metrics are computed server-side** (performance reports only). `ctr`, `cpc`, `cpm`, `cpa`, `cvr`, `roas` are pre-computed per row — read them as-is. Do not recompute or average them across rows. To aggregate volume, sum only the raw counters (`clicks`, `impressions`, `spent`).

**`get_campaign_history_report` is a change/audit log**, not a performance report — one row per change event (`change_type`, `old_value`→`new_value`, `performer`). It has no impression/click/spend or rate metrics.

**Cross-account:** reports are scoped to the single `account_id` queried and do not roll up child accounts; query each child account separately. Campaign/site/item ids are globally unique, so no account column is needed in the grain.

**Rules for correct numbers:**
- The `Total` in the summary line is authoritative — do not sum rows across pages to derive totals or rates.

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

### Estimate Reach Before Launch

```
User: "How many people could we reach on desktop in the US for Marketing Corp?"
AI Process:
  Step 1: search_accounts("Marketing Corp") → account_id: "mktg_corp_001"
  Step 2: get_campaign_reach_estimate(
    account_id="mktg_corp_001",
    campaign={
      "country_targeting": {"type": "INCLUDE", "value": ["US"]},
      "platform_targeting": {"type": "INCLUDE", "value": ["DESK"]}
    },
    estimation_types=["IMPRESSIONS", "MONTHLY_USERS"]
  )
  Result: Lower/upper bound estimates for impressions and monthly unique users
```

### Create a Native Item

```
User: "Add a new ad to campaign 12345678 pointing at example.com/landing — headline 'Save 20% This Spring', body 'Limited-time offer on all spring collection items.', thumbnail https://cdn.example.com/spring.jpg, Shop Now CTA"
AI Process:
  Step 1: search_accounts(...) → account_id: "mktg_corp_001"
  Step 2: list_cta_types() → confirm "SHOP_NOW" is a valid cta_type
  Step 3: create_native_item(
    account_id="mktg_corp_001",
    campaign_id="12345678",
    url="https://example.com/landing",
    title="Save 20% This Spring",
    description="Limited-time offer on all spring collection items.",
    thumbnail_url="https://cdn.example.com/spring.jpg",
    cta={"cta_type": "SHOP_NOW"}
  )
  Result: Native item created
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

## Local Setup (Docker)

Run the server yourself as a Docker container, in one of two modes:

- **Mode 1 — Production:** pointed at Taboola's production authentication, for real use.
- **Mode 2 — On-demand:** pointed at an ephemeral Taboola on-demand (OD) env, for internal development/QA.

Both use Streamable HTTP transport with OAuth 2.1 and listen on port `8000`.

### Prerequisites

- Docker
- An MCP-compatible client (Claude Desktop, Claude Code, Cursor, VS Code, etc.)

### The image

Published per build to Taboola's internal registry (`master` → `docker-releases.taboolasyndication.com`,
branches → `docker-snapshots.taboolasyndication.com`; tags are `YYYYMMDD.N`). Pull a published image:

```bash
docker pull docker-releases.taboolasyndication.com/taboola/realize-mcp:<version>
```

…or build it from the repo:

```bash
docker build -t realize-mcp .
```

The image runs as a non-root user; Prometheus metrics are on port `8092` (map `-p 8092:8092` to expose them).

### Mode 1: Production

Set your OAuth client id in `.env`, then start the `production` profile:

```bash
cp env.template .env
# edit .env →  OAUTH_DCR_CLIENT_ID=your_dcr_client_id
docker compose --profile production up --build
```

`OAUTH_SERVER_URL` defaults to `https://authentication.taboola.com/authentication`; set it in
`.env` to point elsewhere. Then [connect a client](#connect-a-client).

### Mode 2: On-demand env (docker compose)

> **Internal development/QA only — this is not how you normally use the Realize MCP.**
> Mode 1 (and the hosted server in Quick Start) connect to a server meant for real use. This
> mode instead runs the server **locally, pointed at an ephemeral Taboola on-demand (OD) env**,
> to develop or test the server against that env. It uses a shared, hard-coded public OAuth
> client and in-cluster URLs. To keep it separate from any general `realize-mcp` you've added,
> register it under a **distinct name, `realize-mcp-local`** (as the commands below do).

`docker-compose.yml` runs the server in Streamable HTTP mode wired to the env's in-cluster
`authentication` and `backstage` services, using the hard-coded public OAuth client
`realize-mcp-local`.

**1. One-time — configure the env's authentication DB.** New on-demand envs ship with
this `realize-mcp-local` OAuth config already baked in, so you can normally skip this step.
Only run the SQL below if your env predates the baking or otherwise lacks the config (e.g.
the OAuth flow fails with `invalid_target` or an unapproved-redirect error). Connect to the
env's MySQL (`<env>-mysql.on-demand.svc.kube.taboolasyndication.com:3306`, user `root` /
password `taboola`) and run (`performer` is just an audit label):

```sql
-- RFC 8707 resource allowlist (performer is NOT NULL; cache rebuild ~10 min, or restart the auth pod)
INSERT INTO common.config (name, env, service, setting, performer)
VALUES ('oauth21:resource:allowlist', 'ALL', 'ALL',
        '[{"code":"rzmcp","uri":"http://localhost:8000/mcp"}]', 'realize-mcp')
ON DUPLICATE KEY UPDATE setting = VALUES(setting);

-- Public PKCE client (both secret columns NULL -> public); api_key is the client id
INSERT INTO apps_config.pc_auth_tokens (user_id, api_key, secret_key, hashed_secret_key, auto_approve)
VALUES (1, 'realize-mcp-local', NULL, NULL, 1);

-- Exact-match approved redirect, linked by the token's id
INSERT INTO apps_config.pc_auth_approved_redirects (auth_token_id, redirect_uri, is_active)
SELECT id, 'http://localhost:3000/callback', 1
FROM apps_config.pc_auth_tokens WHERE api_key = 'realize-mcp-local';
```

**2. Start the server** (set `ENV_NAME` in `.env`, or inline as below):

```bash
ENV_NAME=<on-demand-env-name> docker compose --profile on-demand up --build
```

Runs on `localhost:8000`, pointed at the env's `authentication` service (default port `10290`)
and `backstage` (via its nginx sidecar, default port `80`). Override if your env differs:
`ENV_NAME=… AUTH_PORT=… BACKSTAGE_PORT=… docker compose --profile on-demand up`
(the per-container ports are in `kubectl get pod <pod> -o jsonpath='{.spec.containers[*].ports[*]}'`).
Then [connect a client](#connect-a-client).

**Notes:**
- The compose file uses `network_mode: host` so the container can use your machine's cluster
  DNS/routing to reach `*.on-demand.svc.kube.taboolasyndication.com`. Your host must already
  be able to reach the env (VPN/cluster routing) — a port-forward won't work, because the auth
  metadata advertises the in-cluster issuer URL.
- The `localhost:8000/mcp` resource and `localhost:3000/callback` redirect in the SQL must
  match how you run and connect.

### Connect a client

Both modes serve the MCP at `http://localhost:8000/mcp`. Connect for a **single session
only** — the locally run server is ephemeral, so it must never be persisted to your client
config (use `--mcp-config`, not `claude mcp add`):

```bash
claude --mcp-config '{"mcpServers":{"realize-mcp-local":{"type":"http","url":"http://localhost:8000/mcp","oauth":{"callbackPort":3000}}}}'
```

The callback port (`3000`) must match the approved redirect (`http://localhost:3000/callback`)
registered for the OAuth client. The client id is supplied by Dynamic Client Registration —
your `OAUTH_DCR_CLIENT_ID` in production, `realize-mcp-local` on-demand — so it doesn't need to
be set here.

### Endpoints

Both modes expose the same HTTP endpoints:

- `GET /.well-known/oauth-protected-resource` - RFC 9728 Protected Resource Metadata (supports path-based discovery)
- `GET /.well-known/oauth-authorization-server` - RFC 8414 metadata (registration_endpoint rewritten)
- `POST /register` - RFC 7591 Dynamic Client Registration (public PKCE clients only; confidential clients provisioned directly by Taboola)
- `POST|DELETE /mcp` - MCP Streamable HTTP endpoint (requires Bearer token)
- `GET /health` - Health check endpoint for Kubernetes probes
- `GET /` on port 8092 - Prometheus metrics endpoint (separate port)

### Traffic attribution

To distinguish traffic that comes through the realize-claude-plugin from raw/direct
MCP clients, the server tags every outbound Backstage call's `User-Agent` with the
calling client. Backstage attributes traffic by `User-Agent`.

The header follows RFC 9110 §10.1.5:

```
realize-mcp/<version> [<caller-product>]
```

- `realize-mcp/<version>` - this server.
- `<caller-product>` - the value of the inbound `X-Realize-Client` request header,
  if present (e.g. `example-client/<version>`). Client-controlled, so it
  is validated against the RFC product grammar and dropped if it does not conform.

Example for a request that sets the header: `realize-mcp/1.0.43 example-client/1.0`;
for a raw client: `realize-mcp/1.0.43`.

This is an attribution heuristic, not an authentication control: any client can set the
header.

### Troubleshooting

Check the container started cleanly:

```bash
docker compose logs          # Mode 2  (or: docker logs <container> for Mode 1)
```

You should see: `INFO:realize.realize_server:Starting Realize MCP Server...`

---

## Detailed Documentation

For comprehensive information, see [design.md](design.md):

- **Recent Fixes & Version History** - Detailed release notes and upgrade instructions
- **Deployment & Installation** - Docker and source installation with troubleshooting
- **Architecture & Design Principles** - Technical implementation details
- **Advanced Features** - CSV format, pagination, sorting, and optimization
- **Development Guide & Testing** - Setup, testing, and contribution guidelines
- **Comprehensive Troubleshooting** - Detailed solutions for common issues
- **Security Best Practices** - Credential management and operational security
- **Complete API Reference** - Full technical API documentation
- **Technology Stack Details** - Dependencies and system requirements

---

## Support

For product or security concerns, bug reports, and feature requests, open an issue at
[github.com/taboola/realize-mcp/issues](https://github.com/taboola/realize-mcp/issues).

---

## Privacy & Data Handling

Realize MCP accesses the Realize API using your OAuth credentials and returns data only to your connected MCP client. Information processed in connection with your use of Realize MCP is handled in accordance with the [Taboola Privacy Policy](https://policies.taboola.com/privacy-policy/).

---

## License

Licensed under the Apache License 2.0. See [LICENSE](LICENSE) for details.

---

**Realize MCP Server** - Safe, efficient, access to Taboola's advertising platform through natural language.
