# Realize MCP Server

A Model Context Protocol (MCP) server providing read and write access to Taboola's Realize API. Enables AI assistants to analyze campaigns, retrieve performance data, generate reports, and manage campaigns and items through natural language. Runs as a Streamable HTTP server with OAuth 2.1 — connect to the hosted server, no local install required.

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0) [![Python](https://img.shields.io/badge/Python-3.10+-green.svg)](https://python.org) [![MCP](https://img.shields.io/badge/MCP-Compatible-orange.svg)](https://modelcontextprotocol.io/)

---

## Quick Start

Connect to the hosted Realize MCP server using [Streamable HTTP](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports#streamable-http) transport with OAuth 2.1. Multi-user, stateless, no local install required.

Every client below connects to the same URL, `https://mcp.realize.com/mcp`, and authenticates
the same way: on first use it opens a browser to Taboola SSO, and the resulting bearer token is
what the Realize tools run as.

Pick the section for your client:

### Claude Desktop and claude.ai

Realize is listed in Claude's connector directory, so you can add it without typing a URL.

**Option 1 — from the connector directory (recommended):**

1. Go to Settings → Connectors and browse the available connectors
2. Find **Realize** and select **Connect**
3. A browser window will open to Taboola SSO—enter your credentials to obtain a bearer token used by Realize tools

**Option 2 — as a custom connector:**

Use this if you need to point Claude at a different Realize MCP endpoint.

1. Go to Settings → Connectors → Add Custom Connector
2. Enter the MCP Server name and URL: `https://mcp.realize.com/mcp`
3. Select **Connect** to initiate the OAuth 2.1 flow
4. A browser window will open to Taboola SSO—enter your credentials to obtain a bearer token used by Realize tools

### Claude Code (CLI)

```bash
claude mcp add --transport http realize-mcp https://mcp.realize.com/mcp
```

Then run `/mcp` inside Claude Code to trigger the OAuth flow.

### Codex

```bash
codex mcp add realize-mcp --url https://mcp.realize.com/mcp
```

Codex detects that the server requires OAuth and starts the flow for you. To re-authenticate
later, run `codex mcp login realize-mcp`.

`codex mcp add` writes the entry to `~/.codex/config.toml`, so Codex Desktop picks it up as
well — restart it after adding. To write the entry by hand instead:

```toml
[mcp_servers.realize-mcp]
url = "https://mcp.realize.com/mcp"
```

### Cursor

Add the server to `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "realize-mcp": {
      "url": "https://mcp.realize.com/mcp"
    }
  }
}
```

Cursor's cloud/web agents are supported too — they complete the same OAuth flow through
Cursor's own hosted callback, with nothing to register in advance.

### Other MCP clients

Any client that speaks Streamable HTTP can connect with the server URL alone:

```json
{
  "mcpServers": {
    "realize-mcp": {
      "type": "http",
      "url": "https://mcp.realize.com/mcp"
    }
  }
}
```

Your client registers itself automatically on first connect, so there is nothing to set up
beforehand — no client ID to request from Taboola, no callback port to pin, and no bridge
process such as `mcp-remote`. Whichever callback your client uses, a local port or its own
hosted URL, is accepted as-is.

---

## Tools Reference

### Account Management

**`search_accounts`** — Search accounts by numeric ID or text query. **Call this first** to get `account_id` values needed by all other tools. Results include `currency`, `country`, and `time_zone_name` so the LLM can pick the right budget amounts and timezone.

```
query        (string, optional)            Digit-only = exact ID lookup; text = fuzzy name lookup; leave empty to list all accounts
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
conversion_rules               Conversion rule attachments (rules via get_conversion_rules)
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

**`list_time_zones`** — IANA time-zone names for `activity_schedule.time_zone`. No parameters.

**`list_cta_types`** — `cta.cta_type` values for `create_native_item` / `update_native_item`. No parameters.

### Conversion Rules

Conversion rules define how the universal pixel attributes conversions for an account, and their IDs populate `conversion_rules` on create/update campaign. There is no delete — retire a rule by setting `status` to `DISABLED` / `ARCHIVED`.

**`get_conversion_rules`** — List an account's ACTION rules (paginated), or fetch one by `rule_id`. On a NETWORK/parent account the listing spans child accounts; each rule's `advertiser_id` names its owner.

```
account_id   (string, required)
rule_id      (string)                      Omit to list; set (numeric id as a string) to fetch one. Empty string is rejected
page         (integer, default: 1)         Ignored when rule_id is set
page_size    (integer, default: 25)        min: 1, max: 50. Ignored when rule_id is set
status       (string enum)                 ACTIVE | DISABLED | ARCHIVED (ARCHIVED also selects disabled rules)
search_text  (string)                      Case-insensitive substring match on display_name
```

**`create_conversion_rule`** — Create a conversion rule. `display_name` is unique per account, and an event can hold only one ACTIVE rule. Returns the created rule with its server-assigned `id`.

```
account_id                     (string, required)
display_name                   (string, required)       Unique per account
event_name                     (string, required)       'page_view' for BASIC; any custom event for EVENT_BASED
type                           (string enum, required)  BASIC | EVENT_BASED
category                       (string enum, required)  VIEW_CONTENT | SEARCH | ADD_TO_CART | ... | MAKE_PURCHASE | LEAD | ... | OTHER
condition                      (object, required)       Recursive match tree; leaf = property + predicate, branch = AND/OR/NOT + children[]
look_back_window               (integer, required)      Click-through attribution window in DAYS (1-30)
include_in_total_conversions   (boolean, required)      Count toward account Total Conversions
status                         (string enum, required)  ACTIVE | DISABLED | ARCHIVED
effects                        (array, required)        Revenue effects: [{type: REVENUE, data: "<numeric string>"}]; [] for none
view_through_look_back_window  (integer)                View-through window in MINUTES (1-10080)
include_in_total_value         (boolean)                Defaults to include_in_total_conversions
aggregation_type               (string enum)            AGGREGATED | LAST_VALUE (default AGGREGATED)
description                    (string)
```

**`update_conversion_rule`** — Update a conversion rule. Send only the fields you are changing; omitted fields keep their stored value. Do not echo back a `get_conversion_rules` object — its nulls and read-only fields are rejected. `type` / `category` / `event_name` are immutable.

```
account_id  (string, required)
rule_id     (string, required)
...         Any writable field from create_conversion_rule (send only the ones you are changing)
```

### Reporting (CSV Format)

Report tools return CSV: a summary banner (record count, row grain, pagination) followed by the rows themselves. There are two reporting surfaces:

- **Dynamic reports** — `get_dynamic_report_settings`, then `get_dynamic_report_data`. You choose the dimensions, metrics, filters and sort, so campaign, site, day and content breakdowns and top-N lists are all built here.
- **`get_campaign_history_report`** — a fixed change/audit log for campaigns.

#### Dynamic reports

**`get_dynamic_report_settings`** — **Required first step.** Returns the account's metamodel: every available dimension, metric and filter, and the operators each filter accepts. `get_dynamic_report_data` rejects names that aren't in it, so take them from here rather than guessing.

```
account_id   (string, required)              From search_accounts
report_type  (string, default: PERFORMANCE)  PERFORMANCE is currently the only supported value
name_filter  (string)                        Case-insensitive substring; narrows columns, filters and the conversion-rule list
```

**`get_dynamic_report_data`** — Run a query built from those names and return the rows as CSV.

```
account_id   (string, required)              From search_accounts
columns      (array, required)               Fully qualified dimension/metric names from the metamodel
date_preset  (string enum)                   YESTERDAY | LAST_7_DAYS | LAST_14_DAYS | LAST_30_DAYS | LAST_90_DAYS |
                                             THIS_MONTH | LAST_MONTH | THIS_QUARTER | LAST_QUARTER | THIS_YEAR | LAST_12_MONTHS
date_from    (string)                        Custom range start, yyyy-MM-dd
date_to      (string)                        Custom range end, yyyy-MM-dd, on or after date_from
filters      (array)                         [{name, operator, values}] — EQUALS | NOT_EQUALS | IN | NOT_IN |
                                             GREATER_THAN | LESS_THAN | BETWEEN | LIKE. Account and date filters are added for you
sort         (array)                         [{column, direction}], applied in list order; each column must also appear in `columns`
page         (integer, default: 1)           min: 1
page_size    (integer, default: 20)          min: 1, max: 100
report_type  (string, default: PERFORMANCE)  PERFORMANCE is currently the only supported value
```

Pass **either** `date_preset` **or** `date_from` + `date_to`, never both; a custom range may span at most 12 months. For top N by a metric, sort on it `DESC` and set `page_size` to N. There is no grand total — a full page means more rows remain.

#### `get_campaign_history_report`

A change/audit log rather than a performance report: one row per change event (`change_type`, `old_value` → `new_value`, `performer`), with no impression, click, spend or rate metrics.

```
account_id  (string, required)            From search_accounts
start_date  (string, required)            Format: YYYY-MM-DD
end_date    (string, required)            Format: YYYY-MM-DD
page        (integer, default: 1)         min: 1
page_size   (integer, default: 20)        min: 1, max: 100
```

#### Data grain & interpretation

Reports return flattened rows. Each report has a **row grain** — the composite key that makes a row unique. The same `site_id` can appear under several campaigns, so rows must be read at their grain, not merged by a single id.

```
get_dynamic_report_data       the dimension columns you requested   # metrics-only query = one aggregate row, no grain
get_campaign_history_report   (campaign_id, change_time, id)        # audit log, not metrics
```

Each response names its grain explicitly in the banner — that, not column order, is the authoritative key. Grain and key columns aren't guaranteed to lead or be adjacent, and column names are the metamodel labels, so don't rely on position.

**Metrics are computed server-side.** `ctr`, `cpc`, `cpm`, `cpa`, `cvr`, `roas` are pre-computed per row — read them as-is. Do not recompute or average them across rows. To aggregate volume, sum only the raw counters (`clicks`, `impressions`, `spent`).

**Cross-account:** reports are scoped to the single `account_id` queried and do not roll up child accounts; query each child account separately. Campaign/site/item ids are globally unique, so no account column is needed in the grain.

**Rules for correct numbers:**
- Where the banner reports a `Total`, it is authoritative — do not sum rows across pages to derive totals or rates.

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
  Step 2: list_campaigns(account_id="advertiser_12345_prod")
  Result: List of campaigns with details
```

### Get Performance Report

```
User: "Get campaign performance for Marketing Corp last month"
AI Process:
  Step 1: search_accounts("Marketing Corp") → account_id: "mktg_corp_001"
  Step 2: get_dynamic_report_settings(account_id="mktg_corp_001")
          → the exact column names to use, e.g. PERFORMANCE_REPORT.CAMPAIGN.CAMPAIGN_NAME,
            PERFORMANCE_REPORT.METRICS.CLICKS, PERFORMANCE_REPORT.METRICS.SPENT
  Step 3: get_dynamic_report_data(
    account_id="mktg_corp_001",
    columns=[
      "PERFORMANCE_REPORT.CAMPAIGN.CAMPAIGN_NAME",
      "PERFORMANCE_REPORT.METRICS.CLICKS",
      "PERFORMANCE_REPORT.METRICS.SPENT"
    ],
    date_preset="LAST_MONTH"
  )
  Result: CSV report with one row per campaign
```

### Top Performing Content

```
User: "Show top 20 performing content items"
AI Process:
  Step 1: search_accounts(...) → account_id: "mktg_corp_001"
  Step 2: get_dynamic_report_settings(account_id="mktg_corp_001", name_filter="item")
          → the item/content dimension and metric names available to this account
  Step 3: get_dynamic_report_data(
    account_id="mktg_corp_001",
    columns=["<item dimension>", "PERFORMANCE_REPORT.METRICS.SPENT"],
    date_preset="LAST_30_DAYS",
    sort=[{"column": "PERFORMANCE_REPORT.METRICS.SPENT", "direction": "DESC"}],
    page_size=20
  )
  Result: Top 20 content items by spend
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

- **CSV Format**: Reports return efficient CSV data with a summary banner (records, row grain, pagination) above the rows
- **Pagination**: Default page_size=20, max=100 to prevent overwhelming responses
- **Sorting**: Dynamic reports sort on any column you requested, in either direction; combine a `DESC` sort with `page_size=N` for a top-N list
- **Size Optimization**: Automatic truncation for large datasets

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
