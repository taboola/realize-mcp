"""Centralized registry for all MCP tools."""
import copy

# Tool Registry - Add new tools here
TOOL_REGISTRY = {
    # Authentication & Token Tools
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
    
    # Account Management Tools
    "search_accounts": {
        "description": "Search for accounts by numeric ID or text query (read-only). Use this first — every other tool's account_id parameter takes the value from the `account_id` field returned here. Response metadata includes `Total` (full match count across all pages) so the caller knows whether more pages remain.\n\nPagination: page (default 1), page_size (1-10, default 10). Keep page_size constant across pages to avoid duplicate or missing results.",
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
    
    # Campaign Management Tools (READ-ONLY)
    "get_all_campaigns": {
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
        "handler": "campaign_handlers.get_all_campaigns",
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
                    "description": "Campaign ID."
                }
            },
            "required": ["account_id", "campaign_id"]
        },
        "handler": "campaign_handlers.get_campaign",
        "category": "campaigns"
    },

    "create_campaign": {
        "description": (
            "Create a campaign on a Realize account. Returns the created campaign including `id` and `status=PAUSED`; campaigns ship paused and do not serve until items are added (set `is_active=true` to launch on creation).\n"
            "\n"
            "All amounts (spending_limit, daily_cap, cpc, cpa_goal, cpc_cap) are numbers in the account's default currency — no currency symbol or code.\n"
            "\n"
            "Conditional rules (schema enforces required fields; these add cross-field rules the schema can't):\n"
            "- spending_limit_model = MONTHLY or ENTIRE → also send spending_limit. NONE → also send daily_cap.\n"
            "- marketing_objective = BRAND_AWARENESS or DRIVE_WEBSITE_TRAFFIC → send cpc; bid_strategy optional (SMART default, or FIXED); omit cpa_goal.\n"
            "- marketing_objective = LEADS_GENERATION, ONLINE_PURCHASES, or MOBILE_APP_INSTALL → send bid_strategy = TARGET_CPA | MAX_CONVERSIONS | MAX_VALUE; if TARGET_CPA, also send cpa_goal; omit cpc.\n"
            "- If both start_date and end_date are sent: end_date >= start_date.\n"
            "\n"
            "Authoritative enum values can be discovered via list_realize_resource: resource=\"marketing_objectives\" | \"bid_strategies\" | \"spending_limit_models\".\n"
            "\n"
            "Read-only — NEVER send: id, advertiser_id, status, approval_state, spent, policy_review, pricing_model, target_cpa, target_cpa_learning_status. (`target_cpa` is the server-recommended CPA range; the user goal is `cpa_goal`.)\n"
            "\n"
            "Non-scalar setup is not supported here. After creation, use:\n"
            "- update_campaign_geo_classic | update_campaign_geo_advanced — geo targeting\n"
            "- update_campaign_techno — platform / os / browser / connection_type\n"
            "- update_campaign_publishers — publisher + group targeting + per-publisher CPC modifiers\n"
            "- update_campaign_my_audiences — first-party + custom audience targeting\n"
            "- update_campaign_lookalike_audience — CRM/pixel lookalike targeting\n"
            "- update_campaign_contextual_segments — contextual segment targeting\n"
            "- update_campaign_schedule — activity schedule (dayparting)\n"
            "- update_campaign_conversion_rules — conversion rule attachments\n"
            "\n"
            "Example — lead gen with target CPA:\n"
            "{ \"account_id\": \"acme-inc\", \"name\": \"Q2 Leads\", \"marketing_objective\": \"LEADS_GENERATION\",\n"
            "  \"branding_text\": \"Acme\", \"spending_limit_model\": \"ENTIRE\", \"spending_limit\": 10000,\n"
            "  \"bid_strategy\": \"TARGET_CPA\", \"cpa_goal\": 15 }"
        ),
        "schema": {
            "type": "object",
            "properties": {
                "account_id": {"type": "string", "description": "Value from search_accounts.account_id (NOT numeric)."},
                "name": {"type": "string", "description": "Campaign name."},
                "marketing_objective": {
                    "type": "string",
                    "enum": ["BRAND_AWARENESS", "DRIVE_WEBSITE_TRAFFIC", "LEADS_GENERATION", "ONLINE_PURCHASES", "MOBILE_APP_INSTALL"],
                    "description": "Business goal. See tool description for bidding rules per value.",
                },
                "branding_text": {"type": "string", "description": "Brand name shown with ads."},
                "spending_limit_model": {
                    "type": "string",
                    "enum": ["NONE", "MONTHLY", "ENTIRE"],
                    "description": "Budget model. NONE = no overall cap (uses daily_cap). MONTHLY = monthly cap. ENTIRE = lifetime cap.",
                },
                "spending_limit": {"type": "number", "description": "Budget amount in account's default currency (e.g. 5000). Required when spending_limit_model is MONTHLY or ENTIRE."},
                "daily_cap": {"type": "number", "description": "Daily spend cap in account's default currency (e.g. 50). Required when spending_limit_model=NONE; otherwise omit (backend computes)."},
                "cpc": {"type": "number", "description": "Fixed cost per click in account's default currency (e.g. 0.25). Use with SMART/FIXED bid_strategy on awareness/traffic objectives."},
                "bid_strategy": {
                    "type": "string",
                    "enum": ["SMART", "FIXED", "TARGET_CPA", "MAX_CONVERSIONS", "MAX_VALUE"],
                    "description": "Bidding strategy. See tool description.",
                },
                "cpa_goal": {"type": "number", "description": "Target cost per acquisition in account's default currency (e.g. 15). Required when bid_strategy=TARGET_CPA."},
                "start_date": {"type": "string", "description": "YYYY-MM-DD. Optional; defaults to immediate."},
                "end_date": {"type": "string", "description": "YYYY-MM-DD. Optional; omit for ongoing."},
                "tracking_code": {"type": "string", "description": "Query string appended to item URLs."},
                "cpc_cap": {"type": "number", "description": "Upper bound on bids in account's default currency (e.g. 1.50)."},
                "comments": {"type": "string", "description": "Internal notes."},
                "daily_ad_delivery_model": {
                    "type": "string",
                    "enum": ["BALANCED", "STRICT"],
                    "description": (
                        "Pacing model for how the daily budget is spent. "
                        "BALANCED smooths spend across the day; STRICT caps spend within tighter daily windows. "
                        "BALANCED typically pairs with MONTHLY/ENTIRE budgets; STRICT typically pairs with daily-cap setups. "
                        "ACCELERATED was deprecated Aug 1 and is no longer accepted. Server determines default."
                    ),
                },
                "traffic_allocation_mode": {
                    "type": "string",
                    "enum": ["OPTIMIZED", "EVEN"],
                    "description": (
                        "How traffic is split across the campaign's items. "
                        "OPTIMIZED (default) lets the algorithm serve higher-engagement items more often. "
                        "EVEN gives each item equal opportunity to compete (used for A/B-testing creatives during the exploratory phase)."
                    ),
                },
                "is_active": {
                    "type": "boolean",
                    "description": (
                        "true to launch the campaign immediately on creation; false or omitted to start paused. "
                        "Even when is_active=true, the campaign will not serve until items are added and approval_state allows."
                    ),
                }
            },
            "required": ["account_id", "name", "marketing_objective", "branding_text", "spending_limit_model"]
        },
        "handler": "campaign_handlers.create_campaign",
        "category": "campaigns",
        "annotations": {
            "destructiveHint": True,
            "idempotentHint": False,
            "openWorldHint": True,
        },
    },

    "update_campaign": {
        "description": (
            "Update scalar fields on an existing campaign.\n"
            "\n"
            "Partial-merge: only supplied fields update; omitted fields keep their current value. Re-sending the same value is a no-op. Send at least one updatable field besides account_id and campaign_id.\n"
            "\n"
            "All amounts (spending_limit, daily_cap, cpc, cpa_goal, cpc_cap) are numbers in the account's default currency — no currency symbol or code.\n"
            "\n"
            "Conditional rules (apply only when the gating field is in this request):\n"
            "- spending_limit_model = MONTHLY or ENTIRE → also send spending_limit. NONE → also send daily_cap.\n"
            "- bid_strategy = TARGET_CPA → also send cpa_goal.\n"
            "- If both start_date and end_date are sent: end_date >= start_date.\n"
            "- Solo updates of a partner field (e.g. only spending_limit, or only cpa_goal) are allowed — the stored gating field is reused.\n"
            "\n"
            "Authoritative enum values can be discovered via list_realize_resource: resource=\"marketing_objectives\" | \"bid_strategies\" | \"spending_limit_models\".\n"
            "\n"
            "Server-side constraints (returns 4xx if violated):\n"
            "- Some marketing_objective transitions are rejected mid-flight; objective + bid_strategy must remain compatible.\n"
            "- MOBILE_APP_INSTALL requires app fields (app_url, app_type, app_store) not exposed here; switching into it via this tool will 4xx.\n"
            "- TERMINATED campaigns cannot be reactivated. approval_state separately gates whether is_active=true actually serves ads.\n"
            "- Account permissions and policy review state may forbid certain edits.\n"
            "\n"
            "Read-only — NEVER send: id, advertiser_id, status, approval_state, spent, policy_review, pricing_model, target_cpa, target_cpa_learning_status. (`target_cpa` is the server-recommended CPA range; the user goal is `cpa_goal`.)\n"
            "\n"
            "Non-scalar updates are not supported here. Use:\n"
            "- update_campaign_geo_classic | update_campaign_geo_advanced — geo targeting\n"
            "- update_campaign_techno — platform / os / browser / connection_type\n"
            "- update_campaign_publishers — publisher + group targeting + per-publisher CPC modifiers\n"
            "- update_campaign_my_audiences — first-party + custom audience targeting\n"
            "- update_campaign_lookalike_audience — CRM/pixel lookalike targeting\n"
            "- update_campaign_contextual_segments — contextual segment targeting\n"
            "- update_campaign_schedule — activity schedule (dayparting)\n"
            "- update_campaign_conversion_rules — conversion rule attachments\n"
            "\n"
            "Example — activate a paused campaign:\n"
            "{ \"account_id\": \"acme-inc\", \"campaign_id\": \"c-123\", \"is_active\": true }"
        ),
        "schema": {
            "type": "object",
            "properties": {
                "account_id": {"type": "string", "description": "Value from search_accounts.account_id (NOT numeric)."},
                "campaign_id": {"type": "string", "description": "Campaign ID."},
                "name": {"type": "string", "description": "Campaign name."},
                "marketing_objective": {
                    "type": "string",
                    "enum": ["BRAND_AWARENESS", "DRIVE_WEBSITE_TRAFFIC", "LEADS_GENERATION", "ONLINE_PURCHASES", "MOBILE_APP_INSTALL"],
                    "description": "Business goal. See tool description for bidding rules per value.",
                },
                "branding_text": {"type": "string", "description": "Brand name shown with ads."},
                "spending_limit_model": {
                    "type": "string",
                    "enum": ["NONE", "MONTHLY", "ENTIRE"],
                    "description": "Budget model. NONE = no overall cap (uses daily_cap). MONTHLY = monthly cap. ENTIRE = lifetime cap.",
                },
                "spending_limit": {"type": "number", "description": "Budget amount in account's default currency (e.g. 5000). Required when spending_limit_model is MONTHLY or ENTIRE."},
                "daily_cap": {"type": "number", "description": "Daily spend cap in account's default currency (e.g. 50). Required when spending_limit_model=NONE; otherwise omit (backend computes)."},
                "cpc": {"type": "number", "description": "Fixed cost per click in account's default currency (e.g. 0.25). Use with SMART/FIXED bid_strategy on awareness/traffic objectives."},
                "bid_strategy": {
                    "type": "string",
                    "enum": ["SMART", "FIXED", "TARGET_CPA", "MAX_CONVERSIONS", "MAX_VALUE"],
                    "description": "Bidding strategy. See tool description.",
                },
                "cpa_goal": {"type": "number", "description": "Target cost per acquisition in account's default currency (e.g. 15). Required when bid_strategy=TARGET_CPA."},
                "start_date": {"type": "string", "description": "YYYY-MM-DD. Optional; defaults to immediate."},
                "end_date": {"type": "string", "description": "YYYY-MM-DD. Optional; omit for ongoing."},
                "tracking_code": {"type": "string", "description": "Query string appended to item URLs."},
                "cpc_cap": {"type": "number", "description": "Upper bound on bids in account's default currency (e.g. 1.50)."},
                "comments": {"type": "string", "description": "Internal notes."},
                "daily_ad_delivery_model": {
                    "type": "string",
                    "enum": ["BALANCED", "STRICT"],
                    "description": (
                        "Pacing model for how the daily budget is spent. "
                        "BALANCED smooths spend across the day; STRICT caps spend within tighter daily windows. "
                        "BALANCED typically pairs with MONTHLY/ENTIRE budgets; STRICT typically pairs with daily-cap setups. "
                        "ACCELERATED was deprecated Aug 1 and is no longer accepted. Server determines default."
                    ),
                },
                "traffic_allocation_mode": {
                    "type": "string",
                    "enum": ["OPTIMIZED", "EVEN"],
                    "description": (
                        "How traffic is split across the campaign's items. "
                        "OPTIMIZED (default) lets the algorithm serve higher-engagement items more often. "
                        "EVEN gives each item equal opportunity to compete (used for A/B-testing creatives during the exploratory phase)."
                    ),
                },
                "is_active": {
                    "type": "boolean",
                    "description": (
                        "true to activate the campaign (set state to ACTIVE), false to pause. "
                        "Re-sending the same value is a no-op. After create_campaign, "
                        "campaigns are paused; set is_active=true to launch. "
                        "TERMINATED campaigns cannot be reactivated; approval_state separately "
                        "gates whether an active campaign actually serves ads."
                    ),
                }
            },
            "required": ["account_id", "campaign_id"]
        },
        "handler": "campaign_handlers.update_campaign",
        "category": "campaigns",
        "annotations": {
            "destructiveHint": True,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    },

    "update_campaign_geo_classic": {
        "description": (
            "Update one classic geo targeting dimension on a campaign (country, region, dma, city, or postal_code).\n"
            "\n"
            "Dimension-scoped: replaces only the supplied dimension; other dimensions are untouched. type=INCLUDE targets only matched values, type=EXCLUDE blocks them, type=ALL clears the dimension (send value=[]).\n"
            "\n"
            "Use this only for campaigns stored in the classic shape. Call get_campaign first; if the response carries `geo_targeting`, use update_campaign_geo_advanced instead — sending classic on an advanced-stored campaign returns 4xx.\n"
            "\n"
            "Discover valid codes via list_realize_resource: resource=\"countries\" for country codes; resource=\"regions\"|\"dma\"|\"cities\"|\"postal_codes\" with args.country_code for sub-dimension codes.\n"
            "\n"
            "Server-side constraints (returns 4xx if violated):\n"
            "- Sub-dimension mutex: at most ONE of {region, dma, city, postal_code} on a campaign. To switch, first clear the current sub-dimension with type=ALL, then set the new one in a second call.\n"
            "- Sub-dimension write requires exactly one INCLUDE country already set. Region values are short-form (\"CA\"), not country-prefixed.\n"
            "- DMA is US-only — valid only when country = INCLUDE [US].\n"
            "- country with type=ALL value=[] clears all sub-location restrictions in one call.\n"
            "- The campaign's allowGeoTargeting flag may forbid geo updates entirely.\n"
            "\n"
            "Example — target US and Canada:\n"
            "{ \"account_id\": \"acme-inc\", \"campaign_id\": \"c-123\", \"dimension\": \"country\",\n"
            "  \"targeting\": {\"type\": \"INCLUDE\", \"value\": [\"US\", \"CA\"]} }\n"
            "\n"
            "Example — switch from city to region (TWO calls):\n"
            "1) {\"account_id\": \"acme-inc\", \"campaign_id\": \"c-123\", \"dimension\": \"city\", \"targeting\": {\"type\": \"ALL\", \"value\": []}}\n"
            "2) {\"account_id\": \"acme-inc\", \"campaign_id\": \"c-123\", \"dimension\": \"region\", \"targeting\": {\"type\": \"INCLUDE\", \"value\": [\"CA\", \"NY\"]}}"
        ),
        "schema": {
            "type": "object",
            "properties": {
                "account_id": {"type": "string", "description": "Value from search_accounts.account_id (NOT numeric)."},
                "campaign_id": {"type": "string", "description": "Campaign ID."},
                "dimension": {
                    "type": "string",
                    "enum": ["country", "region", "dma", "city", "postal_code"],
                    "description": "Which classic geo dimension to update.",
                },
                "targeting": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string", "enum": ["INCLUDE", "EXCLUDE", "ALL"]},
                        "value": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["type", "value"],
                    "description": "Targeting block: {type, value}. value=[] when type=ALL.",
                },
            },
            "required": ["account_id", "campaign_id", "dimension", "targeting"],
        },
        "handler": "campaign_handlers.update_campaign_geo_classic",
        "category": "campaigns",
        "annotations": {
            "destructiveHint": True,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    },

    "update_campaign_geo_advanced": {
        "description": (
            "Update a campaign's geo targeting using the advanced (MultiTargeting) shape, supporting mixed-dimension vectors (e.g. country+region together).\n"
            "\n"
            "Full-replace: the supplied geo_targeting replaces the campaign's current geo wholesale. state=ALL with value=[] clears all geo restrictions; state=EXISTS applies the rules in value (must be non-empty).\n"
            "\n"
            "Each rule groups vectors of one type (INCLUDE or EXCLUDE). A vector may target one dimension or mix several — country=US AND region=CA targets California specifically.\n"
            "\n"
            "Use this when the campaign already stores geo in the advanced shape (get_campaign returns `geo_targeting`). Sending advanced on a classic-storage campaign migrates it one-way to advanced storage, clearing classic fields; the migration is logged in campaign history.\n"
            "\n"
            "Discover valid codes via list_realize_resource: resource=\"countries\" for country codes; resource=\"regions\"|\"dma\"|\"cities\"|\"postal_codes\" with args.country_code for sub-dimension codes.\n"
            "\n"
            "Server-side constraints (returns 4xx if violated):\n"
            "- Country uses ISO-2 codes (e.g. \"US\"). DMA codes are US-only.\n"
            "- More than 200 exclude countries, sanctioned regions, or invalid vector codes are rejected.\n"
            "\n"
            "Example — target US and Canada, exclude Texas:\n"
            "{ \"account_id\": \"acme-inc\", \"campaign_id\": \"c-123\",\n"
            "  \"geo_targeting\": { \"state\": \"EXISTS\", \"value\": [\n"
            "    {\"type\": \"INCLUDE\", \"value\": [{\"country\": \"US\"}, {\"country\": \"CA\"}]},\n"
            "    {\"type\": \"EXCLUDE\", \"value\": [{\"country\": \"US\", \"region\": \"TX\"}]}\n"
            "  ]}}\n"
            "\n"
            "Example — clear all geo (target worldwide):\n"
            "{ \"account_id\": \"acme-inc\", \"campaign_id\": \"c-123\",\n"
            "  \"geo_targeting\": {\"state\": \"ALL\", \"value\": []} }"
        ),
        "schema": {
            "type": "object",
            "properties": {
                "account_id": {"type": "string", "description": "Value from search_accounts.account_id (NOT numeric)."},
                "campaign_id": {"type": "string", "description": "Campaign ID."},
                "geo_targeting": {
                    "type": "object",
                    "description": "MultiTargeting wrapper: {state, value}. state=ALL with value=[] clears geo.",
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
                },
            },
            "required": ["account_id", "campaign_id", "geo_targeting"],
        },
        "handler": "campaign_handlers.update_campaign_geo_advanced",
        "category": "campaigns",
        "annotations": {
            "destructiveHint": True,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    },

    "update_campaign_techno": {
        "description": (
            "Update one technology targeting dimension on a campaign: platform (device type), os (operating system), browser, or connection_type (network).\n"
            "\n"
            "Dimension-scoped: replaces only the supplied dimension; other dimensions are untouched. type=INCLUDE targets only matched values, type=EXCLUDE blocks them, type=ALL clears the dimension (send value=[]).\n"
            "\n"
            "Value shape varies by dimension:\n"
            "- platform | browser | connection_type — array of strings.\n"
            "- os — array of {os_family, sub_categories?}. Omit sub_categories to target the full family.\n"
            "\n"
            "Discover valid values via list_realize_resource: resource=\"platforms\" | \"operating_systems\" | \"browsers\" | \"connection_types\" for top-level lists; resource=\"operating_system_versions\" with args.os_family for OS sub_categories.\n"
            "\n"
            "Common values (source authoritatively via the discovery tool above):\n"
            "- platform: DESK | PHON | TBLT. May be INCLUDE-only on some accounts; the server's 4xx is surfaced unchanged.\n"
            "- os: os_family in {Android, iOS, Windows, Mac OS X, Linux}; sub_categories like [\"iOS_16\", \"iOS_17\"].\n"
            "- browser: Chrome | Firefox | Safari | Edge.\n"
            "- connection_type: WIFI | CELLULAR | OTHER.\n"
            "\n"
            "Example — target Android entirely + iOS 16/17 only:\n"
            "{ \"account_id\": \"acme-inc\", \"campaign_id\": \"c-123\", \"dimension\": \"os\",\n"
            "  \"targeting\": {\"type\": \"INCLUDE\", \"value\": [\n"
            "    {\"os_family\": \"Android\"},\n"
            "    {\"os_family\": \"iOS\", \"sub_categories\": [\"iOS_16\", \"iOS_17\"]}\n"
            "  ]} }\n"
            "\n"
            "Example — clear browser targeting:\n"
            "{ \"account_id\": \"acme-inc\", \"campaign_id\": \"c-123\", \"dimension\": \"browser\",\n"
            "  \"targeting\": {\"type\": \"ALL\", \"value\": []} }"
        ),
        "schema": {
            "type": "object",
            "properties": {
                "account_id": {"type": "string", "description": "Value from search_accounts.account_id (NOT numeric)."},
                "campaign_id": {"type": "string", "description": "Campaign ID."},
                "dimension": {
                    "type": "string",
                    "enum": ["platform", "os", "browser", "connection_type"],
                    "description": "Which technology targeting dimension to update.",
                },
                "targeting": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string", "enum": ["INCLUDE", "EXCLUDE", "ALL"]},
                        "value": {
                            "type": "array",
                            "description": "Strings for platform|browser|connection_type. Objects {os_family, sub_categories?} for os.",
                            "items": {
                                "oneOf": [
                                    {"type": "string"},
                                    {
                                        "type": "object",
                                        "properties": {
                                            "os_family": {"type": "string"},
                                            "sub_categories": {"type": "array", "items": {"type": "string"}},
                                        },
                                        "required": ["os_family"],
                                    },
                                ]
                            },
                        },
                    },
                    "required": ["type", "value"],
                    "description": "Targeting block: {type, value}. value=[] when type=ALL.",
                },
            },
            "required": ["account_id", "campaign_id", "dimension", "targeting"],
        },
        "handler": "campaign_handlers.update_campaign_techno",
        "category": "campaigns",
        "annotations": {
            "destructiveHint": True,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    },

    "update_campaign_my_audiences": {
        "description": (
            "Update first-party + custom audience targeting on a campaign.\n"
            "\n"
            "Full-replace: the supplied my_audiences replaces the campaign's current audience targeting wholesale; send {\"collection\": []} to clear. Only INCLUDE and EXCLUDE are supported on this endpoint (no ALL).\n"
            "\n"
            "Each rule groups audience IDs of one type: INCLUDE adds them as targets, EXCLUDE suppresses them. audience_id values are integer IDs sourced from the Realize UI (Audiences section).\n"
            "\n"
            "For lookalike audiences, use update_campaign_lookalike_audience instead. To read current targeting, use get_campaign.\n"
            "\n"
            "Example — include two audiences, exclude two:\n"
            "{ \"account_id\": \"acme-inc\", \"campaign_id\": \"c-123\",\n"
            "  \"my_audiences\": {\n"
            "    \"collection\": [\n"
            "      {\"collection\": [224820, 25287], \"type\": \"INCLUDE\"},\n"
            "      {\"collection\": [19884, 29870], \"type\": \"EXCLUDE\"}\n"
            "    ]\n"
            "  } }\n"
            "\n"
            "Example — clear all audience targeting:\n"
            "{ \"account_id\": \"acme-inc\", \"campaign_id\": \"c-123\", \"my_audiences\": {\"collection\": []} }"
        ),
        "schema": {
            "type": "object",
            "properties": {
                "account_id": {"type": "string", "description": "Value from search_accounts.account_id (NOT numeric)."},
                "campaign_id": {"type": "string", "description": "Campaign ID."},
                "my_audiences": {
                    "type": "object",
                    "description": "First-party + custom audience targeting. Send {collection: []} to clear.",
                    "properties": {
                        "collection": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "collection": {
                                        "type": "array",
                                        "items": {"type": "integer"},
                                        "description": "Audience IDs to apply this rule to.",
                                    },
                                    "type": {"type": "string", "enum": ["INCLUDE", "EXCLUDE"]},
                                },
                                "required": ["collection", "type"],
                            },
                        },
                    },
                    "required": ["collection"],
                },
            },
            "required": ["account_id", "campaign_id", "my_audiences"],
        },
        "handler": "campaign_handlers.update_campaign_my_audiences",
        "category": "campaigns",
        "annotations": {
            "destructiveHint": True,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    },

    "update_campaign_lookalike_audience": {
        "description": (
            "Update lookalike audience targeting on a campaign (CRM and pixel lookalikes).\n"
            "\n"
            "Full-replace: the supplied lookalike_audience replaces the campaign's current lookalike targeting wholesale; send {\"collection\": []} to clear. Only INCLUDE is supported (server rejects EXCLUDE/ALL); the outer collection holds at most one block.\n"
            "\n"
            "Each item is {rule_id, similarity_level}. rule_id is the integer rule ID for a lookalike audience (from the Realize UI, Audiences > Lookalike). similarity_level (%) depends on the audience subtype — CRM accepts 5/10/15/20/25; pixel accepts 5. The server resolves the subtype from rule_id and rejects mismatches.\n"
            "\n"
            "Predictive (PBP) lookalikes are not supported via this MCP server (the platform only allows them at creation time, and create_campaign exposes no field for them). CRM and pixel lookalikes work normally.\n"
            "\n"
            "Server-side preconditions (returns 4xx if violated):\n"
            "- Account must have user-segments edit permission.\n"
            "- Campaign must allow retargeting.\n"
            "- All rule_ids must resolve to lookalike-class audiences with valid CRM segments.\n"
            "\n"
            "Reading current lookalike targeting is not supported — the lookalike block is filtered out of get_campaign; inspect via the Realize UI. For first-party + custom audiences, use update_campaign_my_audiences.\n"
            "\n"
            "Example — add two CRM lookalikes:\n"
            "{ \"account_id\": \"acme-inc\", \"campaign_id\": \"c-123\",\n"
            "  \"lookalike_audience\": {\n"
            "    \"collection\": [\n"
            "      {\"type\": \"INCLUDE\", \"collection\": [\n"
            "        {\"rule_id\": 1234567, \"similarity_level\": 10},\n"
            "        {\"rule_id\": 7654321, \"similarity_level\": 5}\n"
            "      ]}\n"
            "    ]\n"
            "  } }\n"
            "\n"
            "Example — clear lookalike targeting:\n"
            "{ \"account_id\": \"acme-inc\", \"campaign_id\": \"c-123\", \"lookalike_audience\": {\"collection\": []} }"
        ),
        "schema": {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string",
                    "description": "Value from search_accounts.account_id (NOT numeric).",
                },
                "campaign_id": {
                    "type": "string",
                    "description": "Campaign ID.",
                },
                "lookalike_audience": {
                    "type": "object",
                    "description": "Lookalike audience targeting. Send {collection: []} to clear.",
                    "properties": {
                        "collection": {
                            "type": "array",
                            "maxItems": 1,
                            "description": "At most one INCLUDE block. Empty list clears targeting.",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "type": {"type": "string", "enum": ["INCLUDE"]},
                                    "collection": {
                                        "type": "array",
                                        "description": "List of {rule_id, similarity_level} objects.",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "rule_id": {
                                                    "type": "integer",
                                                    "description": "Rule ID for the lookalike audience (from the Realize UI).",
                                                },
                                                "similarity_level": {
                                                    "type": "integer",
                                                    "enum": [1, 2, 3, 4, 5, 10, 15, 20, 25],
                                                    "description": "Similarity %. Server validates the subset allowed for this audience's subtype.",
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
                },
            },
            "required": ["account_id", "campaign_id", "lookalike_audience"],
        },
        "handler": "campaign_handlers.update_campaign_lookalike_audience",
        "category": "campaigns",
        "annotations": {
            "destructiveHint": True,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    },

    "update_campaign_schedule": {
        "description": (
            "Update a campaign's activity schedule (dayparting) — when the campaign is allowed to serve, by day-of-week + hour ranges in the campaign's time zone.\n"
            "\n"
            "Full-replace: the supplied schedule replaces the campaign's current schedule wholesale. mode=ALWAYS serves every day, all hours (clears any prior CUSTOM schedule). mode=CUSTOM applies the rules array in time_zone.\n"
            "\n"
            "Each rule has type (INCLUDE or EXCLUDE), day (MONDAY..SUNDAY), from_hour (0-23), and until_hour (1-24, > from_hour). Days not mentioned default to INCLUDE 0-24 — you do not need to enumerate all seven.\n"
            "\n"
            "Server-side constraints (returns 4xx if violated):\n"
            "- A given day cannot have both INCLUDE and EXCLUDE rules. Pick one type per day.\n"
            "- Time windows on the same day cannot overlap.\n"
            "- time_zone must be a supported IANA name (required when mode=CUSTOM). Discover supported names via list_realize_resource(resource=\"time_zones\").\n"
            "- Account must have the schedule permission enabled (else 403).\n"
            "- Some publishers require minimum window durations.\n"
            "\n"
            "Example — Mon–Fri 9am–9pm Eastern, no weekends:\n"
            "{ \"account_id\": \"acme-inc\", \"campaign_id\": \"c-123\",\n"
            "  \"schedule\": {\n"
            "    \"mode\": \"CUSTOM\",\n"
            "    \"time_zone\": \"America/New_York\",\n"
            "    \"rules\": [\n"
            "      {\"type\": \"INCLUDE\", \"day\": \"MONDAY\",    \"from_hour\": 9, \"until_hour\": 21},\n"
            "      {\"type\": \"INCLUDE\", \"day\": \"TUESDAY\",   \"from_hour\": 9, \"until_hour\": 21},\n"
            "      {\"type\": \"INCLUDE\", \"day\": \"WEDNESDAY\", \"from_hour\": 9, \"until_hour\": 21},\n"
            "      {\"type\": \"INCLUDE\", \"day\": \"THURSDAY\",  \"from_hour\": 9, \"until_hour\": 21},\n"
            "      {\"type\": \"INCLUDE\", \"day\": \"FRIDAY\",    \"from_hour\": 9, \"until_hour\": 21},\n"
            "      {\"type\": \"EXCLUDE\", \"day\": \"SATURDAY\",  \"from_hour\": 0, \"until_hour\": 24},\n"
            "      {\"type\": \"EXCLUDE\", \"day\": \"SUNDAY\",    \"from_hour\": 0, \"until_hour\": 24}\n"
            "    ]\n"
            "  } }\n"
            "\n"
            "Example — always-on (clear schedule):\n"
            "{ \"account_id\": \"acme-inc\", \"campaign_id\": \"c-123\", \"schedule\": {\"mode\": \"ALWAYS\"} }"
        ),
        "schema": {
            "type": "object",
            "properties": {
                "account_id": {"type": "string", "description": "Value from search_accounts.account_id (NOT numeric)."},
                "campaign_id": {"type": "string", "description": "Campaign ID."},
                "schedule": {
                    "type": "object",
                    "description": "Activity schedule (dayparting): {mode, time_zone?, rules?}. mode=ALWAYS clears any custom schedule.",
                    "properties": {
                        "mode": {"type": "string", "enum": ["ALWAYS", "CUSTOM"]},
                        "time_zone": {"type": "string", "description": "IANA timezone name. Required when mode=CUSTOM."},
                        "rules": {
                            "type": "array",
                            "description": "Required when mode=CUSTOM. Omit or set [] when mode=ALWAYS.",
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
                },
            },
            "required": ["account_id", "campaign_id", "schedule"],
        },
        "handler": "campaign_handlers.update_campaign_schedule",
        "category": "campaigns",
        "annotations": {
            "destructiveHint": True,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    },

    "update_campaign_conversion_rules": {
        "description": (
            "Update the conversion rules attached to a campaign. Conversion rules tell Realize which on-site events count as conversions (purchase, lead, signup, …) for this campaign's optimization and reporting.\n"
            "\n"
            "Full-replace: the supplied conversion_rules list replaces the campaign's current attachments wholesale; send [] to detach all. There is no incremental ADD/REMOVE — to change one rule, read the campaign with get_campaign, edit the list locally, send the merged result.\n"
            "\n"
            "Discovery: this tool does not list available rule ids. Rule ids are authored in the Realize UI (Conversions section) or can be read off an existing campaign via get_campaign (conversion_rules.rules[].id).\n"
            "\n"
            "Server-side constraints (returns 4xx if violated):\n"
            "- Each rule id must exist under the account.\n"
            "- Campaigns with marketing_objective LEADS_GENERATION or ONLINE_PURCHASES typically require at least one conversion rule; [] is rejected on those.\n"
            "- Some rule types are incompatible with some campaign configurations.\n"
            "\n"
            "Example — attach two rules:\n"
            "{ \"account_id\": \"acme-inc\", \"campaign_id\": \"c-123\",\n"
            "  \"conversion_rules\": [{\"id\": 1234567}, {\"id\": 7654321}] }\n"
            "\n"
            "Example — detach all rules:\n"
            "{ \"account_id\": \"acme-inc\", \"campaign_id\": \"c-123\", \"conversion_rules\": [] }"
        ),
        "schema": {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string",
                    "description": "Value from search_accounts.account_id (NOT numeric).",
                },
                "campaign_id": {
                    "type": "string",
                    "description": "Campaign ID.",
                },
                "conversion_rules": {
                    "type": "array",
                    "description": "List of {id} rule references. Send [] to detach all.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {
                                "type": "integer",
                                "description": "Conversion rule ID (numeric, from the Realize UI Conversions section or get_campaign.conversion_rules.rules[].id).",
                            },
                        },
                        "required": ["id"],
                    },
                },
            },
            "required": ["account_id", "campaign_id", "conversion_rules"],
        },
        "handler": "campaign_handlers.update_campaign_conversion_rules",
        "category": "campaigns",
        "annotations": {
            "destructiveHint": True,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    },

    "update_campaign_publishers": {
        "description": (
            "Update publisher-level targeting on a campaign: which publishers run, which publisher groups, and per-publisher CPC bid modifiers. Send any subset of the three fields; at least one is required.\n"
            "\n"
            "Full-replace, per field: each supplied field replaces the campaign's current value for that field wholesale; omitted fields are untouched.\n"
            "\n"
            "publisher_targeting and publisher_groups_targeting use {type: INCLUDE | EXCLUDE | ALL, value: [<name>, ...]}. INCLUDE restricts to listed names; EXCLUDE blocks them; ALL clears the dimension (send value=[]). Values are NAMES (strings), not IDs — server resolves them. Account-level group restrictions may override campaign-level INCLUDE/EXCLUDE and produce a 4xx.\n"
            "\n"
            "publisher_bid_modifier uses {values: [{target: <publisher_name>, cpc_modification: <number>}]}. cpc_modification is a multiplier on the campaign CPC (1.25 = +25%, 0.8 = -20%). Each target must be unique. Send values=[] to clear all modifiers; omit a target to drop its modifier in this update.\n"
            "\n"
            "There is no incremental ADD/REMOVE on any field — to change one entry, read the campaign with get_campaign, edit locally, send the merged result.\n"
            "\n"
            "Example — block two publishers:\n"
            "{ \"account_id\": \"acme-inc\", \"campaign_id\": \"c-123\",\n"
            "  \"publisher_targeting\": {\"type\": \"EXCLUDE\", \"value\": [\"pub_alpha\", \"pub_beta\"]} }\n"
            "\n"
            "Example — set per-publisher CPC modifiers (full replace):\n"
            "{ \"account_id\": \"acme-inc\", \"campaign_id\": \"c-123\",\n"
            "  \"publisher_bid_modifier\": {\"values\": [\n"
            "    {\"target\": \"pub_alpha\", \"cpc_modification\": 1.25},\n"
            "    {\"target\": \"pub_gamma\", \"cpc_modification\": 0.8}\n"
            "  ]} }\n"
            "\n"
            "Example — clear publisher targeting and all CPC modifiers in one call:\n"
            "{ \"account_id\": \"acme-inc\", \"campaign_id\": \"c-123\",\n"
            "  \"publisher_targeting\": {\"type\": \"ALL\", \"value\": []},\n"
            "  \"publisher_bid_modifier\": {\"values\": []} }"
        ),
        "schema": {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string",
                    "description": "Value from search_accounts.account_id (NOT numeric).",
                },
                "campaign_id": {
                    "type": "string",
                    "description": "Campaign ID.",
                },
                "publisher_targeting": {
                    "type": "object",
                    "description": "{type, value}. value=[] when type=ALL. Values are publisher names (not IDs).",
                    "properties": {
                        "type": {"type": "string", "enum": ["INCLUDE", "EXCLUDE", "ALL"]},
                        "value": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Publisher names (resolved server-side).",
                        },
                    },
                    "required": ["type", "value"],
                },
                "publisher_groups_targeting": {
                    "type": "object",
                    "description": "{type, value}. value=[] when type=ALL. Values are publisher-group names (not IDs).",
                    "properties": {
                        "type": {"type": "string", "enum": ["INCLUDE", "EXCLUDE", "ALL"]},
                        "value": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Publisher-group names (resolved server-side).",
                        },
                    },
                    "required": ["type", "value"],
                },
                "publisher_bid_modifier": {
                    "type": "object",
                    "description": "{values: [{target, cpc_modification}]}. values=[] clears all.",
                    "properties": {
                        "values": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "target": {
                                        "type": "string",
                                        "description": "Publisher name.",
                                    },
                                    "cpc_modification": {
                                        "type": "number",
                                        "description": "CPC multiplier (e.g. 1.25 = +25%).",
                                    },
                                },
                                "required": ["target", "cpc_modification"],
                            },
                        },
                    },
                    "required": ["values"],
                },
            },
            "required": ["account_id", "campaign_id"],
        },
        "handler": "campaign_handlers.update_campaign_publishers",
        "category": "campaigns",
        "annotations": {
            "destructiveHint": True,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    },

    "update_campaign_contextual_segments": {
        "description": (
            "Update contextual segment targeting on a campaign. Contextual segments narrow delivery to pages whose content matches a Realize-curated topic (e.g. automotive, finance) using INCLUDE/EXCLUDE rules over integer segment IDs.\n"
            "\n"
            "Full-replace: the supplied contextual_segments replaces the campaign's current contextual targeting wholesale; send {\"collection\": []} to clear all. There is no incremental ADD/REMOVE — to change one segment, read the campaign with get_campaign, edit the lists locally, send the merged result.\n"
            "\n"
            "At most one INCLUDE block and one EXCLUDE block per request — duplicate types are rejected.\n"
            "\n"
            "Discovery: segment IDs are integers (e.g. 1900004), not names. They are not discoverable via this MCP server — author them in the Realize UI or read them off an existing campaign with get_campaign.\n"
            "\n"
            "Server-side constraints (returns 4xx if violated):\n"
            "- Each segment ID must exist and be of contextual data type (not third-party).\n"
            "- Campaign must support contextual targeting (account/campaign type dependent).\n"
            "\n"
            "Example — combine an include and exclude block:\n"
            "{ \"account_id\": \"acme-inc\", \"campaign_id\": \"c-123\",\n"
            "  \"contextual_segments\": {\"collection\": [\n"
            "    {\"type\": \"INCLUDE\", \"collection\": [1900004, 1900024]},\n"
            "    {\"type\": \"EXCLUDE\", \"collection\": [1900100]}\n"
            "  ]} }\n"
            "\n"
            "Example — clear all contextual targeting:\n"
            "{ \"account_id\": \"acme-inc\", \"campaign_id\": \"c-123\",\n"
            "  \"contextual_segments\": {\"collection\": []} }"
        ),
        "schema": {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string",
                    "description": "Value from search_accounts.account_id (NOT numeric).",
                },
                "campaign_id": {
                    "type": "string",
                    "description": "Campaign ID.",
                },
                "contextual_segments": {
                    "type": "object",
                    "description": "Contextual segment targeting: {collection}. Send {collection: []} to clear.",
                    "properties": {
                        "collection": {
                            "type": "array",
                            "description": (
                                "List of rule blocks. At most one INCLUDE and one EXCLUDE."
                            ),
                            "items": {
                                "type": "object",
                                "properties": {
                                    "type": {
                                        "type": "string",
                                        "enum": ["INCLUDE", "EXCLUDE"],
                                    },
                                    "collection": {
                                        "type": "array",
                                        "description": "Integer contextual segment IDs.",
                                        "items": {"type": "integer"},
                                    },
                                },
                                "required": ["type", "collection"],
                            },
                        },
                    },
                    "required": ["collection"],
                },
            },
            "required": ["account_id", "campaign_id", "contextual_segments"],
        },
        "handler": "campaign_handlers.update_campaign_contextual_segments",
        "category": "campaigns",
        "annotations": {
            "destructiveHint": True,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    },

    # Campaign Items Tools (READ-ONLY)
    "get_campaign_items": {
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
                    "description": "Campaign ID."
                }
            },
            "required": ["account_id", "campaign_id"]
        },
        "handler": "campaign_handlers.get_campaign_items",
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
                    "description": "Campaign ID."
                },
                "item_id": {
                    "type": "string",
                    "description": "Item ID."
                }
            },
            "required": ["account_id", "campaign_id", "item_id"]
        },
        "handler": "campaign_handlers.get_campaign_item",
        "category": "campaign_items"
    },

    # Resource Discovery Tools (READ-ONLY) — surface valid values for campaign tool inputs.

    "list_realize_resource": {
        "description": (
            "List valid values for a Realize platform vocabulary used by create_campaign and update_campaign_* targeting tools (countries, regions, OS families, browsers, time zones, etc.).\n"
            "\n"
            "Pick `resource` from the supported list. Some resources need an additional argument under `args`:\n"
            "- `regions`, `dma`, `cities`, `postal_codes` need `args.country_code` (ISO-2, e.g. \"US\").\n"
            "- `operating_system_versions` needs `args.os_family` (e.g. \"iOS\", \"Android\").\n"
            "All other resources take no `args`.\n"
            "\n"
            "Returns a flat list of valid values. Use the values directly as inputs to the relevant write tool — for example, codes from resource=\"countries\" go into update_campaign_geo_classic / update_campaign_geo_advanced; values from resource=\"browsers\" go into update_campaign_techno; values from resource=\"time_zones\" go into update_campaign_schedule.\n"
            "\n"
            "Example — list US regions:\n"
            "{ \"resource\": \"regions\", \"args\": {\"country_code\": \"US\"} }"
        ),
        "schema": {
            "type": "object",
            "properties": {
                "resource": {
                    "type": "string",
                    "enum": [
                        "countries",
                        "regions",
                        "dma",
                        "cities",
                        "postal_codes",
                        "platforms",
                        "operating_systems",
                        "operating_system_versions",
                        "browsers",
                        "connection_types",
                        "marketing_objectives",
                        "bid_strategies",
                        "spending_limit_models",
                        "time_zones",
                    ],
                    "description": "Which Realize platform vocabulary to fetch.",
                },
                "args": {
                    "type": "object",
                    "description": "Required only for parametrised resources. See tool description.",
                    "properties": {
                        "country_code": {
                            "type": "string",
                            "description": "ISO-2 country code. Required for resource=regions|dma|cities|postal_codes.",
                        },
                        "os_family": {
                            "type": "string",
                            "description": "Required for resource=operating_system_versions (e.g. \"iOS\", \"Android\").",
                        },
                    },
                },
            },
            "required": ["resource"],
        },
        "handler": "resources.list_realize_resource",
        "category": "resources",
    },

    # Reporting Tools (READ-ONLY)

    "get_top_campaign_content_report": {
        "description": "Get the top-performing campaign content report for an account (read-only). Returns CSV with a summary header. One call per page returns complete data — do not retry unless an error is returned.\n\nPagination: page (default 1), page_size (1-100, default 20). Check `Total` in the response header for the full record count.",
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
        "description": "Get the campaign history report for an account (read-only). Returns CSV with historical metrics. One call per page returns complete data — do not retry unless an error is returned.\n\nPagination: page (default 1), page_size (1-100, default 20). Check `Total` in the response header for the full record count.",
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
        "description": "Get the campaign breakdown report for an account (read-only). Returns CSV with per-campaign metrics. One call per page returns complete data — do not retry unless an error is returned.\n\nPagination: page (default 1), page_size (1-100, default 20). Check `Total` in the response header for the full record count.",
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
        "description": "Get the campaign site/day breakdown report for an account (read-only). Returns CSV with per-site, per-day metrics. One call per page returns complete data — do not retry unless an error is returned.\n\nPagination: page (default 1), page_size (1-100, default 20). Check `Total` in the response header for the full record count.",
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