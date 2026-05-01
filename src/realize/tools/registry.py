"""Centralized registry for all MCP tools.

================================================================================
TOOL SURFACE — 20 tools across 6 categories
================================================================================

Authentication (stdio transport only; excluded in HTTP/OAuth mode):
  - get_auth_token
  - get_token_details

Accounts:
  - search_accounts                      (entry point — call first; account_id required by every other tool)

Campaigns (read):
  - list_campaigns
  - get_campaign

Campaigns (write — fat tools, all targeting inline, single atomic POST):
  - create_campaign
  - update_campaign

Campaign items (read):
  - list_campaign_items
  - get_campaign_item

Discovery (resources for resolving IDs/names used in campaign payloads):
  - search_geos                          (countries / regions / dma / cities / postal_codes)
  - search_techno                        (browsers, operating_system_versions per family)
  - list_time_zones                      (IANA names for activity_schedule.time_zone)
  - search_audiences                     (first-party + custom audience IDs)
  - search_lookalike_audiences           (CRM/pixel/PBP rule_ids)
  - search_publishers                    (publisher names per account)
  - search_conversion_rules              (conversion rule IDs per account)

Reports (CSV):
  - get_top_campaign_content_report
  - get_campaign_history_report
  - get_campaign_breakdown_report
  - get_campaign_site_day_breakdown_report

================================================================================
FILE SECTIONS (declarations are bottom-up because Python; navigate by section
banner via your editor's outline / Cmd-F):

  1. Shared description fragments
  2. Targeting schema constants
  3. Long-form tool descriptions (create/update_campaign)
  4. Composed property maps + annotations
  5. Tool entries (per-category dicts merged into TOOL_REGISTRY)
  6. Public accessors
================================================================================
"""
import copy


# ============================================================================
# 1. Shared description fragments
# ============================================================================

_TARGETING_BLOCKS_NOTE = (
    "Targeting blocks are FULL-REPLACE: sending `my_audiences` with one audience "
    "wipes the others; sending `geo_targeting` replaces all geo. To edit a single "
    "entry, read with get_campaign, modify locally, send the merged result. "
    "Scalar fields (name, cpc, is_active, …) are partial-merge — omitted scalars keep "
    "their prior value."
)


# ============================================================================
# 2. Targeting schema constants — referenced by create/update_campaign property
#    maps. Each schema's `description` field is what the LLM sees per property.
# ============================================================================

# 2.1 Geo (advanced)
_GEO_ADVANCED_SCHEMA = {
    "type": "object",
    "description": (
        "Advanced (MultiTargeting) geo targeting. {state, value}. state=ALL with "
        "value=[] clears geo. state=EXISTS applies the rules in value. "
        "Each rule: {type: INCLUDE|EXCLUDE, value: [{country, region?, dma?, city?, postal_code?}]}. "
        "Mix dims in one vector to AND them (country=US + region=California targets California). "
        "Note: region values are full names (\"California\", \"New York\") not ISO codes — confirm via search_geos.\n"
        "\n"
        "Discover codes via search_geos:\n"
        "- country: search_geos(dimension=countries)\n"
        "- region: search_geos(dimension=regions, country_code=<ISO-2>)\n"
        "- dma: search_geos(dimension=dma, country_code=US)\n"
        "- city: search_geos(dimension=cities, country_code=<ISO-2>)\n"
        "- postal_code: search_geos(dimension=postal_codes, country_code=<ISO-2>)"
    ),
    "properties": {
        "state": {"type": "string", "enum": ["ALL", "EXISTS"]},
        "value": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["INCLUDE", "EXCLUDE"]},
                    "value": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "country": {"type": ["string", "null"]},
                                "region": {"type": ["string", "null"]},
                                "dma": {"type": ["string", "null"]},
                                "city": {"type": ["string", "null"]},
                                "postal_code": {"type": ["string", "null"]},
                            },
                        },
                    },
                },
                "required": ["type", "value"],
            },
        },
    },
    "required": ["state", "value"],
}


# 2.2 Shared `Targeting<String>` properties block — reused by classic geo + techno schemas
_TARGETING_STRING_SHAPE_PROPERTIES = {
    "type": {"type": "string", "enum": ["INCLUDE", "EXCLUDE", "ALL"]},
    "value": {"type": "array", "items": {"type": "string"}},
}


# 2.3 Classic geo dimension schemas (update_campaign only — create_campaign rejects classic geo)

_COUNTRY_TARGETING_SCHEMA = {
    "type": "object",
    "description": (
        "Classic country targeting (update only). {type: INCLUDE|EXCLUDE|ALL, value: [string]}. "
        "value=[] when type=ALL. "
        "Mutually exclusive with geo_targeting (advanced) in same request. "
        "Discover values via search_geos(dimension=countries)."
    ),
    "properties": _TARGETING_STRING_SHAPE_PROPERTIES,
    "required": ["type", "value"],
}

_REGION_TARGETING_SCHEMA = {
    "type": "object",
    "description": (
        "Classic region targeting (update only). {type: INCLUDE|EXCLUDE|ALL, value: [string]}. "
        "value=[] when type=ALL. "
        "Sub-dimension mutex: at most ONE of region/dma/city/postal_code on a campaign; "
        "requires INCLUDE country already set. "
        "Mutually exclusive with geo_targeting (advanced) in same request. "
        "Discover values via search_geos(dimension=regions, country_code=<ISO-2>)."
    ),
    "properties": _TARGETING_STRING_SHAPE_PROPERTIES,
    "required": ["type", "value"],
}

_DMA_TARGETING_SCHEMA = {
    "type": "object",
    "description": (
        "Classic dma targeting (update only). {type: INCLUDE|EXCLUDE|ALL, value: [string]}. "
        "value=[] when type=ALL. "
        "Sub-dimension mutex: at most ONE of region/dma/city/postal_code on a campaign; "
        "requires INCLUDE country already set. "
        "Mutually exclusive with geo_targeting (advanced) in same request. "
        "Discover values via search_geos(dimension=dma, country_code=US). DMA is US-only."
    ),
    "properties": _TARGETING_STRING_SHAPE_PROPERTIES,
    "required": ["type", "value"],
}

_CITY_TARGETING_SCHEMA = {
    "type": "object",
    "description": (
        "Classic city targeting (update only). {type: INCLUDE|EXCLUDE|ALL, value: [string]}. "
        "value=[] when type=ALL. "
        "Sub-dimension mutex: at most ONE of region/dma/city/postal_code on a campaign; "
        "requires INCLUDE country already set. "
        "Mutually exclusive with geo_targeting (advanced) in same request. "
        "Discover values via search_geos(dimension=cities, country_code=<ISO-2>)."
    ),
    "properties": _TARGETING_STRING_SHAPE_PROPERTIES,
    "required": ["type", "value"],
}

_POSTAL_CODE_TARGETING_SCHEMA = {
    "type": "object",
    "description": (
        "Classic postal_code targeting (update only). {type: INCLUDE|EXCLUDE|ALL, value: [string]}. "
        "value=[] when type=ALL. "
        "Sub-dimension mutex: at most ONE of region/dma/city/postal_code on a campaign; "
        "requires INCLUDE country already set. "
        "Mutually exclusive with geo_targeting (advanced) in same request. "
        "Discover values via search_geos(dimension=postal_codes, country_code=<ISO-2>)."
    ),
    "properties": _TARGETING_STRING_SHAPE_PROPERTIES,
    "required": ["type", "value"],
}


# 2.4 Techno targeting schemas — platform/browser/connection_type use string values;
#     os uses {os_family, sub_categories?} objects.

_PLATFORM_TARGETING_SCHEMA = {
    "type": "object",
    "description": (
        "platform targeting. {type: INCLUDE|EXCLUDE|ALL, value: [...]}. "
        "value=[] when type=ALL. "
        "Values: NA | DESK | PHON | TBLT | TV | OTHR (mobile = PHON; desktop = DESK; tablet = TBLT)."
    ),
    "properties": _TARGETING_STRING_SHAPE_PROPERTIES,
    "required": ["type", "value"],
}

_BROWSER_TARGETING_SCHEMA = {
    "type": "object",
    "description": (
        "browser targeting. {type: INCLUDE|EXCLUDE|ALL, value: [...]}. "
        "value=[] when type=ALL. Browser names are dynamically maintained server-side; "
        "discover the authoritative list via search_techno(dimension=browsers)."
    ),
    "properties": _TARGETING_STRING_SHAPE_PROPERTIES,
    "required": ["type", "value"],
}

_CONNECTION_TYPE_TARGETING_SCHEMA = {
    "type": "object",
    "description": (
        "connection_type targeting. {type: INCLUDE|EXCLUDE|ALL, value: [...]}. "
        "value=[] when type=ALL. Values: WIFI."
    ),
    "properties": _TARGETING_STRING_SHAPE_PROPERTIES,
    "required": ["type", "value"],
}

_OS_TARGETING_SCHEMA = {
    "type": "object",
    "description": (
        "os targeting. {type: INCLUDE|EXCLUDE|ALL, value: [...]}. "
        "value=[] when type=ALL. Items: {os_family, sub_categories?}. "
        "os_family values: Mac OS X | Linux | Windows | iOS | iPadOS | Android. "
        "Discover sub_categories per family via search_techno(dimension=operating_system_versions, os_family=<family>) "
        "(returns wire-usable strings like \"iOS 17\", \"Android 14\")."
    ),
    "properties": {
        "type": {"type": "string", "enum": ["INCLUDE", "EXCLUDE", "ALL"]},
        "value": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "os_family": {"type": "string"},
                    "sub_categories": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["os_family"],
            },
        },
    },
    "required": ["type", "value"],
}


# 2.5 Activity schedule (dayparting)
_ACTIVITY_SCHEDULE_SCHEMA = {
    "type": "object",
    "description": (
        "Activity schedule (dayparting). {mode: ALWAYS|CUSTOM, time_zone?, rules?}. "
        "mode=ALWAYS clears any custom schedule. mode=CUSTOM requires time_zone (IANA name; "
        "discover via list_time_zones) and rules. "
        "Each rule: {type: INCLUDE|EXCLUDE, day: MONDAY..SUNDAY, from_hour: 0-23, until_hour: 1-24}. "
        "Days unmentioned default to INCLUDE 0-24. Same day cannot mix INCLUDE+EXCLUDE; windows cannot overlap."
    ),
    "properties": {
        "mode": {"type": "string", "enum": ["ALWAYS", "CUSTOM"]},
        "time_zone": {"type": "string"},
        "rules": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["INCLUDE", "EXCLUDE"]},
                    "day": {
                        "type": "string",
                        "enum": ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"],
                    },
                    "from_hour": {"type": "integer", "minimum": 0, "maximum": 23},
                    "until_hour": {"type": "integer", "minimum": 1, "maximum": 24},
                },
                "required": ["type", "day", "from_hour", "until_hour"],
            },
        },
    },
    "required": ["mode"],
}


# 2.6 Conversion rules
_CONVERSION_RULES_SCHEMA = {
    "type": "array",
    "description": (
        "Conversion rule attachments. List of {id} objects. Send [] to detach all. "
        "Discover rule IDs via search_conversion_rules. "
        "LEADS_GENERATION / ONLINE_PURCHASES typically require >=1 rule."
    ),
    "items": {
        "type": "object",
        "properties": {"id": {"type": "integer"}},
        "required": ["id"],
    },
}


# 2.7 Publishers (targeting + bid modifier)
_PUBLISHER_TARGETING_SCHEMA = {
    "type": "object",
    "description": (
        "Publisher targeting. {type: INCLUDE|EXCLUDE|ALL, value: [publisher_name]}. "
        "value=[] when type=ALL. Names (not IDs) — server resolves them. "
        "Discover names via search_publishers."
    ),
    "properties": {
        "type": {"type": "string", "enum": ["INCLUDE", "EXCLUDE", "ALL"]},
        "value": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["type", "value"],
}


_PUBLISHER_BID_MODIFIER_SCHEMA = {
    "type": "object",
    "description": (
        "Per-publisher CPC bid modifier. {values: [{target: <publisher_name>, cpc_modification: <number>}]}. "
        "cpc_modification is a multiplier (1.25 = +25%). values=[] clears all modifiers. "
        "Discover publisher names via search_publishers."
    ),
    "properties": {
        "values": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "target": {"type": "string"},
                    "cpc_modification": {"type": "number"},
                },
                "required": ["target", "cpc_modification"],
            },
        },
    },
    "required": ["values"],
}


# 2.8 Contextual segments
_CONTEXTUAL_SEGMENTS_SCHEMA = {
    "type": "object",
    "description": (
        "Contextual segment targeting. {collection: [{type: INCLUDE|EXCLUDE, collection: [int]}]}. "
        "Send {collection: []} to clear. At most one INCLUDE and one EXCLUDE block. "
        "Segment IDs are authored in the Realize UI; not discoverable via this MCP."
    ),
    "properties": {
        "collection": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["INCLUDE", "EXCLUDE"]},
                    "collection": {"type": "array", "items": {"type": "integer"}},
                },
                "required": ["type", "collection"],
            },
        },
    },
    "required": ["collection"],
}


# 2.9 Audiences (first-party / custom + lookalike)
_MY_AUDIENCES_SCHEMA = {
    "type": "object",
    "description": (
        "First-party + custom audience targeting. {collection: [{type: INCLUDE|EXCLUDE, collection: [int]}]}. "
        "Send {collection: []} to clear. Discover audience IDs via search_audiences."
    ),
    "properties": {
        "collection": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "collection": {"type": "array", "items": {"type": "integer"}},
                    "type": {"type": "string", "enum": ["INCLUDE", "EXCLUDE"]},
                },
                "required": ["collection", "type"],
            },
        },
    },
    "required": ["collection"],
}


_LOOKALIKE_AUDIENCE_SCHEMA = {
    "type": "object",
    "description": (
        "Lookalike audience targeting (CRM/pixel/PBP). {collection: [{type: INCLUDE, collection: [{rule_id, similarity_level}]}]}. "
        "Send {collection: []} to clear. INCLUDE-only; at most one block. similarity_level: CRM 5/10/15/20/25, pixel 5, PBP 1/2/3/4/5. "
        "Discover rule_ids via search_lookalike_audiences. PBP lookalike audiences must be created in the Realize UI before they can be targeted."
    ),
    "properties": {
        "collection": {
            "type": "array",
            "maxItems": 1,
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["INCLUDE"]},
                    "collection": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "rule_id": {"type": "integer"},
                                "similarity_level": {
                                    "type": "integer",
                                    "enum": [1, 2, 3, 4, 5, 10, 15, 20, 25],
                                },
                            },
                            "required": ["rule_id", "similarity_level"],
                        },
                    },
                },
                "required": ["type", "collection"],
            },
        },
    },
    "required": ["collection"],
}


# ============================================================================
# 3. Composed property maps + annotations
#    (Defined here because long-form descriptions in section 4 can reference
#    field semantics from these scalars.)
# ============================================================================

_SCALAR_PROPERTIES = {
    "name": {"type": "string", "description": "Campaign name."},
    "marketing_objective": {
        "type": "string",
        "enum": ["BRAND_AWARENESS", "DRIVE_WEBSITE_TRAFFIC", "LEADS_GENERATION", "ONLINE_PURCHASES", "MOBILE_APP_INSTALL"],
        "description": "Business goal. Determines required bidding fields. Discover values via list_realize_resource(resource=marketing_objectives).",
    },
    "branding_text": {"type": "string", "description": "Brand name shown with ads."},
    "spending_limit_model": {
        "type": "string",
        "enum": ["NONE", "MONTHLY", "ENTIRE"],
        "description": "Budget model. NONE = no overall cap (uses daily_cap). MONTHLY = monthly cap. ENTIRE = lifetime cap. Discover values via list_realize_resource(resource=spending_limit_models).",
    },
    "spending_limit": {"type": "number", "description": "Budget amount in account's default currency."},
    "daily_cap": {"type": "number", "description": "Daily spend cap in account's default currency."},
    "cpc": {"type": "number", "description": "Fixed cost per click in account's default currency."},
    "bid_strategy": {
        "type": "string",
        "enum": ["SMART", "FIXED", "TARGET_CPA", "MAX_CONVERSIONS", "MAX_VALUE"],
        "description": "Bidding strategy. Discover values via list_realize_resource(resource=bid_strategies).",
    },
    "cpa_goal": {"type": "number", "description": "Target cost per acquisition in account's default currency."},
    "start_date": {"type": "string", "description": "YYYY-MM-DD. Optional; defaults to immediate."},
    "end_date": {"type": "string", "description": "YYYY-MM-DD. Optional; omit for ongoing."},
    "tracking_code": {"type": "string", "description": "Query string appended to item URLs."},
    "cpc_cap": {"type": "number", "description": "Upper bound on bids in account's default currency."},
    "comments": {"type": "string", "description": "Internal notes."},
    "daily_ad_delivery_model": {
        "type": "string",
        "enum": ["BALANCED", "STRICT"],
        "description": "Pacing model. BALANCED smooths spend; STRICT caps within tighter daily windows. ACCELERATED was deprecated Aug 1.",
    },
    "traffic_allocation_mode": {
        "type": "string",
        "enum": ["OPTIMIZED", "EVEN"],
        "description": "Item traffic split. OPTIMIZED (default) favors higher-engagement items; EVEN gives each item equal opportunity (A/B testing).",
    },
    "is_active": {
        "type": "boolean",
        "description": "true to launch (set ACTIVE), false to pause. Even when true, won't serve until items added and approval_state allows. TERMINATED campaigns cannot be reactivated.",
    },
}


_TARGETING_PROPERTIES_COMMON = {
    "geo_targeting": _GEO_ADVANCED_SCHEMA,
    "platform_targeting": _PLATFORM_TARGETING_SCHEMA,
    "os_targeting": _OS_TARGETING_SCHEMA,
    "browser_targeting": _BROWSER_TARGETING_SCHEMA,
    "connection_type_targeting": _CONNECTION_TYPE_TARGETING_SCHEMA,
    "activity_schedule": _ACTIVITY_SCHEDULE_SCHEMA,
    "conversion_rules": _CONVERSION_RULES_SCHEMA,
    "publisher_targeting": _PUBLISHER_TARGETING_SCHEMA,
    "publisher_bid_modifier": _PUBLISHER_BID_MODIFIER_SCHEMA,
    "contextual_segments": _CONTEXTUAL_SEGMENTS_SCHEMA,
    "my_audiences": _MY_AUDIENCES_SCHEMA,
    "lookalike_audience": _LOOKALIKE_AUDIENCE_SCHEMA,
}


_UPDATE_CLASSIC_GEO_PROPERTIES = {
    "country_targeting": _COUNTRY_TARGETING_SCHEMA,
    "region_targeting": _REGION_TARGETING_SCHEMA,
    "dma_targeting": _DMA_TARGETING_SCHEMA,
    "city_targeting": _CITY_TARGETING_SCHEMA,
    "postal_code_targeting": _POSTAL_CODE_TARGETING_SCHEMA,
}


# ============================================================================
# 4. Long-form tool descriptions for create_campaign / update_campaign
#    Split into PROSE + JSON example so JSON braces don't collide with f-string
#    interpolation. Final description = prose + json example concatenated.
# ============================================================================

_CREATE_CAMPAIGN_PROSE = f"""\
Create a campaign on a Realize account, with full targeting in one call. Returns the created campaign (`id`, `status=PAUSED`); ships paused, won't serve until items are added (set `is_active=true` to launch).

Prerequisite: call search_accounts first to obtain a valid `account_id`. The numeric account ID is rejected.

{_TARGETING_BLOCKS_NOTE}

Geo: accepts `geo_targeting` (advanced/MultiTargeting) only. Classic geo fields rejected on create. Use update_campaign for classic geo edits on existing classic-storage campaigns.

All amounts (spending_limit, daily_cap, cpc, cpa_goal, cpc_cap) are numbers in the account's default currency.

Conditional rules:
- spending_limit_model = MONTHLY|ENTIRE → also send spending_limit. NONE → also send daily_cap.
- marketing_objective = BRAND_AWARENESS|DRIVE_WEBSITE_TRAFFIC → send cpc; bid_strategy SMART (default) or FIXED; omit cpa_goal.
- marketing_objective = LEADS_GENERATION|ONLINE_PURCHASES|MOBILE_APP_INSTALL → bid_strategy = TARGET_CPA|MAX_CONVERSIONS|MAX_VALUE; if TARGET_CPA also send cpa_goal; omit cpc.
- If both start_date and end_date sent: end_date >= start_date.

Discovery (call before constructing the payload to resolve IDs/names):
- search_geos → `geo_targeting` country / region / dma / city / postal_code values.
- search_techno → `os_targeting` sub_categories and `browser_targeting` values. (platform / connection_type / os_family enums are listed inline in their schema descriptions.)
- search_audiences → `my_audiences` audience IDs.
- search_lookalike_audiences → `lookalike_audience` rule_ids.
- search_publishers → `publisher_targeting` and `publisher_bid_modifier.target` names.
- search_conversion_rules → `conversion_rules` IDs.
- list_time_zones → `activity_schedule.time_zone` IANA names.

Read-only — NEVER send: id, advertiser_id, status, approval_state, spent, policy_review, pricing_model, target_cpa, target_cpa_learning_status. (`target_cpa` is server-recommended; user goal is `cpa_goal`.)

All targeting (including audiences, lookalike, contextual segments) goes in one atomic POST to Backstage; either the whole campaign with all targeting commits, or none of it does.

Comprehensive example (every available field set; trim what you don't need — only the five required scalars are mandatory).

Plain English: a Q2 lead-generation campaign for the Acme brand, $10,000 lifetime budget, running May 1 to Jun 30 2026 in TARGET_CPA bid mode aiming for $15 per acquisition. Targets US and Canada (excluding Alaska), desktop and phone, iOS 17 and any Android, Chrome and Safari, Wi-Fi and cellular. Serves Mon–Fri 9 AM–9 PM Eastern (off weekends). Includes audiences 224820 and 25287 (excludes 19884), one CRM lookalike at 10% similarity, contextual segments for the topic, two conversion rules, allowlists publishers `pub_alpha` and `pub_beta` with +25% bid on `pub_alpha` and -20% on `pub_beta`. Ships paused (`is_active=false`).

"""


_CREATE_CAMPAIGN_JSON_EXAMPLE = """\
{
  "account_id": "acme-inc",
  "name": "Q2 Leads — US Mobile",
  "marketing_objective": "LEADS_GENERATION",
  "branding_text": "Acme",
  "spending_limit_model": "ENTIRE",
  "spending_limit": 10000,
  "bid_strategy": "TARGET_CPA",
  "cpa_goal": 15,
  "start_date": "2026-05-01",
  "end_date": "2026-06-30",
  "tracking_code": "utm_source=taboola",
  "comments": "Q2 lead gen — primary",
  "daily_ad_delivery_model": "BALANCED",
  "traffic_allocation_mode": "OPTIMIZED",
  "is_active": false,
  "geo_targeting": {"state": "EXISTS", "value": [
    {"type": "INCLUDE", "value": [{"country": "US"}, {"country": "CA"}]},
    {"type": "EXCLUDE", "value": [{"country": "US", "region": "Alaska"}]}
  ]},
  "platform_targeting": {"type": "INCLUDE", "value": ["DESK", "PHON"]},
  "os_targeting": {"type": "INCLUDE", "value": [
    {"os_family": "iOS", "sub_categories": ["iOS 17"]},
    {"os_family": "Android"}
  ]},
  "browser_targeting": {"type": "INCLUDE", "value": ["Chrome", "Safari"]},
  "connection_type_targeting": {"type": "INCLUDE", "value": ["WIFI", "CELLULAR"]},
  "activity_schedule": {"mode": "CUSTOM", "time_zone": "America/New_York", "rules": [
    {"type": "INCLUDE", "day": "MONDAY",    "from_hour": 9, "until_hour": 21},
    {"type": "INCLUDE", "day": "TUESDAY",   "from_hour": 9, "until_hour": 21},
    {"type": "INCLUDE", "day": "WEDNESDAY", "from_hour": 9, "until_hour": 21},
    {"type": "INCLUDE", "day": "THURSDAY",  "from_hour": 9, "until_hour": 21},
    {"type": "INCLUDE", "day": "FRIDAY",    "from_hour": 9, "until_hour": 21},
    {"type": "EXCLUDE", "day": "SATURDAY",  "from_hour": 0, "until_hour": 24},
    {"type": "EXCLUDE", "day": "SUNDAY",    "from_hour": 0, "until_hour": 24}
  ]},
  "conversion_rules": [{"id": 1234567}, {"id": 7654321}],
  "publisher_targeting": {"type": "INCLUDE", "value": ["pub_alpha", "pub_beta"]},
  "publisher_bid_modifier": {"values": [
    {"target": "pub_alpha", "cpc_modification": 1.25},
    {"target": "pub_beta",  "cpc_modification": 0.80}
  ]},
  "contextual_segments": {"collection": [
    {"type": "INCLUDE", "collection": [1900004, 1900024]}
  ]},
  "my_audiences": {"collection": [
    {"type": "INCLUDE", "collection": [224820, 25287]},
    {"type": "EXCLUDE", "collection": [19884]}
  ]},
  "lookalike_audience": {"collection": [{"type": "INCLUDE", "collection": [
    {"rule_id": 1234567, "similarity_level": 10}
  ]}]}
}"""


_CREATE_CAMPAIGN_DESCRIPTION = _CREATE_CAMPAIGN_PROSE + _CREATE_CAMPAIGN_JSON_EXAMPLE


_UPDATE_CAMPAIGN_PROSE = f"""\
Update an existing campaign: scalars and any targeting block in one call.

Prerequisites: call search_accounts first to obtain `account_id`; call list_campaigns or get_campaign to obtain `campaign_id` (or use the `id` returned by create_campaign). Numeric account IDs are rejected.

{_TARGETING_BLOCKS_NOTE}

Geo: accepts EITHER `geo_targeting` (advanced/MultiTargeting, full-replace) OR classic dimension fields (country_targeting, region_targeting, dma_targeting, city_targeting, postal_code_targeting — each replaces only its dimension). Sending both shapes in one request is rejected. Sending advanced on a classic-storage campaign one-way migrates it to advanced (logged in campaign history).

All amounts are numbers in the account's default currency.

Conditional rules (apply only when the gating field is in this request):
- spending_limit_model = MONTHLY|ENTIRE → also send spending_limit. NONE → also send daily_cap.
- bid_strategy = TARGET_CPA → also send cpa_goal.
- If both start_date and end_date sent: end_date >= start_date.
- Solo updates of a partner field (e.g. only spending_limit, or only cpa_goal) are allowed — stored gating field is reused.

At least one updatable field besides account_id and campaign_id must be sent.

Server-side constraints (returns 4xx if violated):
- Some marketing_objective transitions are rejected mid-flight.
- MOBILE_APP_INSTALL switching requires app fields not exposed here.
- TERMINATED campaigns cannot be reactivated.
- Lookalike: account must have user-segments edit permission and campaign must allow retargeting.

Discovery: same as create_campaign — search_geos, search_techno, search_audiences, search_lookalike_audiences, search_publishers, search_conversion_rules, list_time_zones. Each schema property below names which tool populates it.

Field shapes are identical to create_campaign — see its comprehensive example for every targeting block. Examples below focus on update-only patterns (partial-merge, classic-geo, full-replace within a section).

Read-only — NEVER send: id, advertiser_id, status, approval_state, spent, policy_review, pricing_model, target_cpa, target_cpa_learning_status.

All updates (including audiences, lookalike, contextual segments) go in one atomic POST to Backstage.

"""


_UPDATE_CAMPAIGN_EXAMPLES = """\
Example — activate paused campaign and add publisher bid modifier (partial-merge):
{ "account_id": "acme-inc", "campaign_id": "49184816", "is_active": true,
  "publisher_bid_modifier": {"values": [{"target": "pub_alpha", "cpc_modification": 1.25}]} }

Example — clear audience targeting only (other targeting untouched, full-replace within section):
{ "account_id": "acme-inc", "campaign_id": "49184816", "my_audiences": {"collection": []} }

Example — edit one classic geo dimension on a classic-storage campaign (no migration to advanced):
{ "account_id": "acme-inc", "campaign_id": "49184816",
  "region_targeting": {"type": "INCLUDE", "value": ["California", "New York"]} }"""


_UPDATE_CAMPAIGN_DESCRIPTION = _UPDATE_CAMPAIGN_PROSE + _UPDATE_CAMPAIGN_EXAMPLES


# Destructive-write annotations (signal to MCP hosts that these tools mutate state).
_DESTRUCTIVE_ANNOTATIONS_CREATE = {
    "destructiveHint": True,
    "idempotentHint": False,
    "openWorldHint": True,
}


_DESTRUCTIVE_ANNOTATIONS_UPDATE = {
    "destructiveHint": True,
    "idempotentHint": True,
    "openWorldHint": True,
}


# Final property maps fed into the create/update_campaign tool schemas.
_CREATE_CAMPAIGN_PROPERTIES = {
    "account_id": {"type": "string", "description": "Value from search_accounts.account_id (NOT numeric)."},
    **_SCALAR_PROPERTIES,
    **_TARGETING_PROPERTIES_COMMON,
}


_UPDATE_CAMPAIGN_PROPERTIES = {
    "account_id": {"type": "string", "description": "Value from search_accounts.account_id (NOT numeric)."},
    "campaign_id": {"type": "string", "description": "Value from list_campaigns.id or get_campaign.id (returned by create_campaign as `id`). Numeric ID as a string (e.g. \"49184816\")."},
    **_SCALAR_PROPERTIES,
    **_TARGETING_PROPERTIES_COMMON,
    **_UPDATE_CLASSIC_GEO_PROPERTIES,
}


# ============================================================================
# 5. Tool entries — grouped per-category. TOOL_REGISTRY at the end is just a
#    spread-merge of the per-category dicts. Edit a category in isolation
#    without scrolling past the others.
# ============================================================================

# 5.1 Authentication (stdio transport only)
_AUTH_TOOLS = {
    "get_auth_token": {
        "description": "Authenticate with the Realize API using client credentials (read-only).",
        "schema": {
            "type": "object",
            "properties": {},
            "required": []
        },
        "handler": "auth_handlers.get_auth_token",
        "category": "authentication"
    },

    "get_token_details": {
        "description": "Get details about the current authentication token (read-only).",
        "schema": {
            "type": "object",
            "properties": {},
            "required": []
        },
        "handler": "auth_handlers.get_token_details",
        "category": "authentication"
    },
}


# 5.2 Accounts
_ACCOUNT_TOOLS = {
    "search_accounts": {
        "description": (
            "Search for accounts by numeric ID or text query (read-only). Use this first — "
            "every other tool's `account_id` parameter takes the value from the `account_id` field "
            "returned here. Each result includes the account's `currency`, `country`, and "
            "`time_zone_name` — use these to choose budget amounts in the right currency and to "
            "populate `activity_schedule.time_zone`. Response metadata includes `Total` (full match "
            "count across pages). Keep page_size constant across pages to avoid duplicate or "
            "missing results."
        ),
        "schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Numeric account ID, text search term, or '*' to list all accounts."
                },
                "page": {
                    "type": "integer",
                    "default": 1,
                    "minimum": 1,
                    "description": "Page number (default 1)."
                },
                "page_size": {
                    "type": "integer",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 10,
                    "description": "Records per page (1-10, default 10)."
                }
            },
            "required": ["query"]
        },
        "handler": "account_handlers.search_accounts",
        "category": "accounts"
    },
}


# 5.3 Campaigns (read)
_CAMPAIGN_READ_TOOLS = {
    "list_campaigns": {
        "description": "List all campaigns on a Realize account (read-only).",
        "schema": {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string",
                    "description": "Value from search_accounts.account_id (NOT numeric)."
                }
            },
            "required": ["account_id"]
        },
        "handler": "campaign_handlers.list_campaigns",
        "category": "campaigns"
    },

    "get_campaign": {
        "description": "Get details for one campaign on a Realize account (read-only).",
        "schema": {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string",
                    "description": "Value from search_accounts.account_id (NOT numeric)."
                },
                "campaign_id": {
                    "type": "string",
                    "description": "Value from list_campaigns.id or get_campaign.id. Numeric ID as a string (e.g. \"49184816\")."
                }
            },
            "required": ["account_id", "campaign_id"]
        },
        "handler": "campaign_handlers.get_campaign",
        "category": "campaigns"
    },
}


# 5.4 Campaigns (write — fat tools, all targeting inline)
_CAMPAIGN_WRITE_TOOLS = {
    "create_campaign": {
        "description": _CREATE_CAMPAIGN_DESCRIPTION,
        "schema": {
            "type": "object",
            "properties": _CREATE_CAMPAIGN_PROPERTIES,
            "required": ["account_id", "name", "marketing_objective", "branding_text", "spending_limit_model", "bid_strategy"],
        },
        "handler": "campaign_handlers.create_campaign",
        "category": "campaigns",
        "annotations": _DESTRUCTIVE_ANNOTATIONS_CREATE,
    },

    "update_campaign": {
        "description": _UPDATE_CAMPAIGN_DESCRIPTION,
        "schema": {
            "type": "object",
            "properties": _UPDATE_CAMPAIGN_PROPERTIES,
            "required": ["account_id", "campaign_id"],
        },
        "handler": "campaign_handlers.update_campaign",
        "category": "campaigns",
        "annotations": _DESTRUCTIVE_ANNOTATIONS_UPDATE,
    },
}


# 5.5 Campaign items (read)
_CAMPAIGN_ITEM_TOOLS = {
    "list_campaign_items": {
        "description": "List all items (creatives) on a campaign (read-only).",
        "schema": {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string",
                    "description": "Value from search_accounts.account_id (NOT numeric)."
                },
                "campaign_id": {
                    "type": "string",
                    "description": "Value from list_campaigns.id or get_campaign.id. Numeric ID as a string (e.g. \"49184816\")."
                }
            },
            "required": ["account_id", "campaign_id"]
        },
        "handler": "campaign_handlers.list_campaign_items",
        "category": "campaign_items"
    },

    "get_campaign_item": {
        "description": "Get details for one item (creative) on a campaign (read-only).",
        "schema": {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string",
                    "description": "Value from search_accounts.account_id (NOT numeric)."
                },
                "campaign_id": {
                    "type": "string",
                    "description": "Value from list_campaigns.id or get_campaign.id. Numeric ID as a string (e.g. \"49184816\")."
                },
                "item_id": {
                    "type": "string",
                    "description": "Value from list_campaign_items.id."
                }
            },
            "required": ["account_id", "campaign_id", "item_id"]
        },
        "handler": "campaign_handlers.get_campaign_item",
        "category": "campaign_items"
    },
}


# 5.6 Discovery — resolve IDs/names used in campaign payloads
_DISCOVERY_TOOLS = {
    "search_geos": {
        "description": (
            "Search valid country / region / dma / city / postal_code values for create_campaign and update_campaign geo targeting (read-only).\n"
            "\n"
            "dimension=countries (no country_code) returns ISO-2 country codes. "
            "dimension=regions|dma|cities|postal_codes requires country_code (ISO-2, e.g. \"US\"). "
            "DMA is US-only.\n"
            "\n"
            "Use returned values directly in geo_targeting (advanced) vectors, e.g. "
            "{country: \"US\", region: \"California\"}, or in classic *_targeting blocks on update_campaign. "
            "Region/city values are FULL NAMES (\"California\"), not ISO codes.\n"
            "\n"
            "Example — list US states: { \"dimension\": \"regions\", \"country_code\": \"US\" }"
        ),
        "schema": {
            "type": "object",
            "properties": {
                "dimension": {
                    "type": "string",
                    "enum": ["countries", "regions", "dma", "cities", "postal_codes"],
                    "description": "Geo dimension to look up.",
                },
                "country_code": {
                    "type": "string",
                    "description": "ISO-2 country code (e.g. \"US\").",
                },
            },
            "required": ["dimension"],
        },
        "handler": "resources.search_geos",
        "category": "resources",
    },

    "search_techno": {
        "description": (
            "Search valid technology-targeting values for create_campaign and update_campaign "
            "os_targeting (sub_categories) and browser_targeting (read-only).\n"
            "\n"
            "Other techno enums (platforms, os_family, connection_type) are inlined in their schema descriptions "
            "as small fixed enums and don't require discovery.\n"
            "\n"
            "dimension=browsers takes no extra args. "
            "dimension=operating_system_versions requires os_family (e.g. \"iOS\", \"Android\") and returns "
            "values usable as `sub_categories` on os_targeting items.\n"
            "\n"
            "Example — list iOS versions: { \"dimension\": \"operating_system_versions\", \"os_family\": \"iOS\" }"
        ),
        "schema": {
            "type": "object",
            "properties": {
                "dimension": {
                    "type": "string",
                    "enum": [
                        "operating_system_versions",
                        "browsers",
                    ],
                    "description": "Technology dimension to look up.",
                },
                "os_family": {
                    "type": "string",
                    "description": "OS family name (e.g. \"iOS\", \"Android\").",
                },
            },
            "required": ["dimension"],
        },
        "handler": "resources.search_techno",
        "category": "resources",
    },

    "search_audiences": {
        "description": (
            "Search first-party and custom audiences for an account (read-only). "
            "Audience IDs returned here populate `my_audiences.collection[].collection: [int]` on "
            "create_campaign / update_campaign."
        ),
        "schema": {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string",
                    "description": "Value from search_accounts.account_id (NOT numeric).",
                },
                "country_codes": {
                    "type": "string",
                    "description": "Optional. Comma-separated ISO-2 codes (e.g. \"US,CA\"). Narrows to audiences targeting these countries.",
                },
                "country_targeting_type": {
                    "type": "string",
                    "enum": ["ALL", "INCLUDE", "EXCLUDE"],
                    "description": "Optional. Interprets country_codes. ALL (default) returns audiences regardless of targeting type; INCLUDE/EXCLUDE narrow further.",
                },
            },
            "required": ["account_id"],
        },
        "handler": "discovery_handlers.search_audiences",
        "category": "resources",
    },

    "search_lookalike_audiences": {
        "description": (
            "Search lookalike audiences (CRM / pixel / PBP) available for targeting on an account "
            "(read-only). rule_ids returned here populate "
            "`lookalike_audience.collection[].collection[].rule_id` on create_campaign / update_campaign. "
            "Optional country_code (ISO-2) narrows to audiences targeting one country."
        ),
        "schema": {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string",
                    "description": "Value from search_accounts.account_id (NOT numeric).",
                },
                "country_code": {
                    "type": "string",
                    "description": "Optional. ISO-2 country code (e.g. \"US\").",
                },
            },
            "required": ["account_id"],
        },
        "handler": "discovery_handlers.search_lookalike_audiences",
        "category": "resources",
    },

    "search_publishers": {
        "description": (
            "Search publishers an account is allowed to target (read-only). "
            "Publisher names returned here populate `publisher_targeting.value` on "
            "create_campaign / update_campaign."
        ),
        "schema": {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string",
                    "description": "Value from search_accounts.account_id (NOT numeric).",
                },
            },
            "required": ["account_id"],
        },
        "handler": "discovery_handlers.search_publishers",
        "category": "resources",
    },

    "search_conversion_rules": {
        "description": (
            "Search conversion rules attached to an account (read-only). "
            "Rule IDs returned here populate `conversion_rules: [{id}]` on "
            "create_campaign / update_campaign. LEADS_GENERATION and ONLINE_PURCHASES "
            "campaigns typically require at least one conversion rule attached."
        ),
        "schema": {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string",
                    "description": "Value from search_accounts.account_id (NOT numeric).",
                },
            },
            "required": ["account_id"],
        },
        "handler": "discovery_handlers.search_conversion_rules",
        "category": "resources",
    },

    "list_time_zones": {
        "description": (
            "List valid IANA time zone names for `activity_schedule.time_zone` on create_campaign / update_campaign "
            "(CUSTOM mode). Output values are directly usable on the wire (e.g. \"America/New_York\", \"US/Eastern\", "
            "\"Europe/London\")."
        ),
        "schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
        "handler": "resources.list_time_zones",
        "category": "resources",
    },
}


# 5.7 Reports (CSV)
_REPORT_TOOLS = {
    "get_top_campaign_content_report": {
        "description": "Get the top-performing campaign content report for an account (read-only). Returns CSV with a summary header. One call per page returns complete data — do not retry unless an error is returned.\n\nCheck `Total` in the response header for the full record count across all pages.",
        "schema": {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string",
                    "description": "Value from search_accounts.account_id (NOT numeric)."
                },
                "start_date": {
                    "type": "string",
                    "description": "YYYY-MM-DD."
                },
                "end_date": {
                    "type": "string",
                    "description": "YYYY-MM-DD."
                },
                "page": {
                    "type": "integer",
                    "default": 1,
                    "minimum": 1,
                    "description": "Page number (default 1)."
                },
                "page_size": {
                    "type": "integer",
                    "default": 20,
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Records per page (1-100, default 20)."
                },
                "sort_field": {
                    "type": "string",
                    "enum": ["clicks", "spent", "impressions"],
                    "description": "Optional sort field. Defaults to no sort."
                },
                "sort_direction": {
                    "type": "string",
                    "enum": ["ASC", "DESC"],
                    "default": "DESC",
                    "description": "ASC or DESC (default DESC)."
                }
            },
            "required": ["account_id", "start_date", "end_date"]
        },
        "handler": "report_handlers.get_top_campaign_content_report",
        "category": "reports"
    },

    "get_campaign_history_report": {
        "description": "Get the campaign history report for an account (read-only). Returns CSV with historical metrics. One call per page returns complete data — do not retry unless an error is returned.\n\nCheck `Total` in the response header for the full record count across all pages.",
        "schema": {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string",
                    "description": "Value from search_accounts.account_id (NOT numeric)."
                },
                "start_date": {
                    "type": "string",
                    "description": "YYYY-MM-DD."
                },
                "end_date": {
                    "type": "string",
                    "description": "YYYY-MM-DD."
                },
                "page": {
                    "type": "integer",
                    "default": 1,
                    "minimum": 1,
                    "description": "Page number (default 1)."
                },
                "page_size": {
                    "type": "integer",
                    "default": 20,
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Records per page (1-100, default 20)."
                }
            },
            "required": ["account_id", "start_date", "end_date"]
        },
        "handler": "report_handlers.get_campaign_history_report",
        "category": "reports"
    },

    "get_campaign_breakdown_report": {
        "description": "Get the campaign breakdown report for an account (read-only). Returns CSV with per-campaign metrics. One call per page returns complete data — do not retry unless an error is returned.\n\nCheck `Total` in the response header for the full record count across all pages.",
        "schema": {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string",
                    "description": "Value from search_accounts.account_id (NOT numeric)."
                },
                "start_date": {
                    "type": "string",
                    "description": "YYYY-MM-DD."
                },
                "end_date": {
                    "type": "string",
                    "description": "YYYY-MM-DD."
                },
                "filters": {
                    "type": "object",
                    "description": "Optional flat object of filter key/value pairs.",
                    "additionalProperties": {"type": "string"}
                },
                "page": {
                    "type": "integer",
                    "default": 1,
                    "minimum": 1,
                    "description": "Page number (default 1)."
                },
                "page_size": {
                    "type": "integer",
                    "default": 20,
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Records per page (1-100, default 20)."
                },
                "sort_field": {
                    "type": "string",
                    "enum": ["clicks", "spent", "impressions"],
                    "description": "Optional sort field. Defaults to no sort."
                },
                "sort_direction": {
                    "type": "string",
                    "enum": ["ASC", "DESC"],
                    "default": "DESC",
                    "description": "ASC or DESC (default DESC)."
                }
            },
            "required": ["account_id", "start_date", "end_date"]
        },
        "handler": "report_handlers.get_campaign_breakdown_report",
        "category": "reports"
    },

    "get_campaign_site_day_breakdown_report": {
        "description": "Get the campaign site/day breakdown report for an account (read-only). Returns CSV with per-site, per-day metrics. One call per page returns complete data — do not retry unless an error is returned.\n\nCheck `Total` in the response header for the full record count across all pages.",
        "schema": {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string",
                    "description": "Value from search_accounts.account_id (NOT numeric)."
                },
                "start_date": {
                    "type": "string",
                    "description": "YYYY-MM-DD."
                },
                "end_date": {
                    "type": "string",
                    "description": "YYYY-MM-DD."
                },
                "filters": {
                    "type": "object",
                    "description": "Optional flat object of filter key/value pairs.",
                    "additionalProperties": {"type": "string"}
                },
                "page": {
                    "type": "integer",
                    "default": 1,
                    "minimum": 1,
                    "description": "Page number (default 1)."
                },
                "page_size": {
                    "type": "integer",
                    "default": 20,
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Records per page (1-100, default 20)."
                },
                "sort_field": {
                    "type": "string",
                    "enum": ["clicks", "spent", "impressions"],
                    "description": "Optional sort field. Defaults to no sort."
                },
                "sort_direction": {
                    "type": "string",
                    "enum": ["ASC", "DESC"],
                    "default": "DESC",
                    "description": "ASC or DESC (default DESC)."
                }
            },
            "required": ["account_id", "start_date", "end_date"]
        },
        "handler": "report_handlers.get_campaign_site_day_breakdown_report",
        "category": "reports"
    },
}


# Merged registry — single source of truth for `tools/list`. Order preserved
# (matters for some MCP clients that show tools in declaration order).
TOOL_REGISTRY = {
    **_AUTH_TOOLS,
    **_ACCOUNT_TOOLS,
    **_CAMPAIGN_READ_TOOLS,
    **_CAMPAIGN_WRITE_TOOLS,
    **_CAMPAIGN_ITEM_TOOLS,
    **_DISCOVERY_TOOLS,
    **_REPORT_TOOLS,
}


# ============================================================================
# 6. Public accessors
# ============================================================================

def get_all_tools():
    """Get all registered tools, filtered by transport mode."""
    from realize.config import config

    tools = TOOL_REGISTRY
    if config.mcp_transport != "stdio":
        tools = {name: tool for name, tool in tools.items()
                 if tool.get("category") != "authentication"}
    return copy.deepcopy(tools)


def get_tools_by_category(category: str):
    """Get tools filtered by category."""
    return {name: copy.deepcopy(tool) for name, tool in TOOL_REGISTRY.items()
            if tool.get("category") == category}


def get_tool_categories():
    """Get list of all available categories."""
    return list(set(tool.get("category", "uncategorized")
                   for tool in TOOL_REGISTRY.values()))
