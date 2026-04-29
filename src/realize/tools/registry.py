"""Centralized registry for all MCP tools."""
import copy

# Tool Registry - Add new tools here
TOOL_REGISTRY = {
    # Authentication & Token Tools
    "get_auth_token": {
        "description": "Authenticate with Realize API using client credentials (read-only)",
        "schema": {
            "type": "object",
            "properties": {},
            "required": []
        },
        "handler": "auth_handlers.get_auth_token",
        "category": "authentication"
    },
    
    "get_token_details": {
        "description": "Get details about current authentication token (read-only)",
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
        "description": "Search for accounts by numeric ID or text query to get account_id values needed for other tools (read-only). Returns account data including 'account_id' field (camelCase string) required for campaign and report operations. WORKFLOW: Use this tool FIRST to get account_id values, then use those values with other tools. PAGINATION: page_size (1-10, default: 10) and page (default: 1). Keep page_size the same across all pages to avoid duplicate/missing results. Check 'Total' in response metadata for full match count.",
        "schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Account ID (numeric), search term (text), or '*' to list all accounts. Use the returned 'account_id' field for other tool operations."
                },
                "page": {
                    "type": "integer",
                    "default": 1,
                    "minimum": 1,
                    "description": "Page number for pagination (default: 1)"
                },
                "page_size": {
                    "type": "integer",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 10,
                    "description": "Records per page (default: 10, max: 10)"
                }
            },
            "required": ["query"]
        },
        "handler": "account_handlers.search_accounts",
        "category": "accounts"
    },
    
    # Campaign Management Tools (READ-ONLY)
    "get_all_campaigns": {
        "description": "Get all campaigns for an account (read-only). WORKFLOW REQUIRED: First use search_accounts to get account_id, then use that value here. Example: 1) search_accounts('company_name') 2) Extract 'account_id' from results 3) Use account_id parameter here",
        "schema": {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string",
                    "description": "Account ID (string from search_accounts response 'account_id' field - NOT numeric ID). Workflow: 1) search_accounts('query') 2) Use 'account_id' from results"
                }
            },
            "required": ["account_id"]
        },
        "handler": "campaign_handlers.get_all_campaigns",
        "category": "campaigns"
    },

    "get_campaign": {
        "description": "Get specific campaign details (read-only). WORKFLOW REQUIRED: First use search_accounts to get account_id, then use that value here. Example: 1) search_accounts('company_name') 2) Extract 'account_id' from results 3) Use account_id parameter here",
        "schema": {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string",
                    "description": "Account ID (string from search_accounts response 'account_id' field - NOT numeric ID). Workflow: 1) search_accounts('query') 2) Use 'account_id' from results"
                },
                "campaign_id": {
                    "type": "string",
                    "description": "Campaign ID to get details for"
                }
            },
            "required": ["account_id", "campaign_id"]
        },
        "handler": "campaign_handlers.get_campaign",
        "category": "campaigns"
    },

    "create_campaign": {
        "description": (
            "Create a campaign. Returns the created campaign object including `id` and `status=PAUSED`. Campaign will not serve until items are added and the campaign is activated.\n"
            "\n"
            "All amounts (spending_limit, daily_cap, cpc, cpa_goal, cpc_cap) are numbers in the account's default currency. Do not include a currency symbol or code.\n"
            "\n"
            "Required (always):\n"
            "- account_id (string): value from `account_id` field of search_accounts response (NOT numeric)\n"
            "- name (string)\n"
            "- marketing_objective (string enum): BRAND_AWARENESS | DRIVE_WEBSITE_TRAFFIC | WEBSITE_ENGAGEMENT | LEADS_GENERATION | ONLINE_PURCHASES | MOBILE_APP_INSTALL\n"
            "- branding_text (string): brand name shown with ads\n"
            "- spending_limit_model (string enum): NONE | MONTHLY | ENTIRE\n"
            "\n"
            "Required by spending_limit_model:\n"
            "- MONTHLY or ENTIRE -> set spending_limit (number)\n"
            "- NONE -> set daily_cap (number)\n"
            "\n"
            "Required by marketing_objective + bid_strategy:\n"
            "- BRAND_AWARENESS | DRIVE_WEBSITE_TRAFFIC | WEBSITE_ENGAGEMENT\n"
            "    -> set cpc (number). bid_strategy (string enum) optional (SMART default, or FIXED). Omit cpa_goal.\n"
            "- LEADS_GENERATION | ONLINE_PURCHASES | MOBILE_APP_INSTALL\n"
            "    -> set bid_strategy (string enum) = TARGET_CPA | MAX_CONVERSIONS | MAX_VALUE.\n"
            "       If bid_strategy = TARGET_CPA, set cpa_goal (number). Omit cpc.\n"
            "\n"
            "Optional scalars: start_date (string, YYYY-MM-DD), end_date (string, YYYY-MM-DD), tracking_code (string), cpc_cap (number), comments (string), daily_ad_delivery_model (string enum: BALANCED | STRICT), traffic_allocation_mode (string enum: OPTIMIZED | EVEN, default OPTIMIZED), is_active (boolean: true to launch immediately, false or omit to start paused). If both dates set: end_date >= start_date.\n"
            "\n"
            "Read-only - NEVER send: id, advertiser_id, status, approval_state, spent, policy_review, pricing_model, target_cpa, target_cpa_learning_status. (target_cpa is server-recommended CPA range, not the user goal — set cpa_goal instead.)\n"
            "\n"
            "Not supported here. After creation, use these update tools to set them:\n"
            "- geo targeting: update_campaign_geo_classic | update_campaign_geo_advanced\n"
            "- technology targeting (platform / os / browser / connection_type): update_campaign_techno\n"
            "- publisher / publisher-group targeting + per-publisher CPC bid modifiers: update_campaign_publishers\n"
            "- first-party + custom audience targeting: update_campaign_my_audiences\n"
            "- activity schedule (dayparting): update_campaign_schedule\n"
            "- conversion rule attachments: update_campaign_conversion_rules\n"
            "\n"
            "Examples:\n"
            "\n"
            "Brand awareness, monthly budget:\n"
            "{ \"account_id\": \"acme-inc\", \"name\": \"Q2 Awareness\", \"marketing_objective\": \"BRAND_AWARENESS\",\n"
            "  \"branding_text\": \"Acme\", \"spending_limit_model\": \"MONTHLY\", \"spending_limit\": 5000, \"cpc\": 0.30 }\n"
            "\n"
            "Lead gen, target CPA:\n"
            "{ \"account_id\": \"acme-inc\", \"name\": \"Q2 Leads\", \"marketing_objective\": \"LEADS_GENERATION\",\n"
            "  \"branding_text\": \"Acme\", \"spending_limit_model\": \"ENTIRE\", \"spending_limit\": 10000,\n"
            "  \"bid_strategy\": \"TARGET_CPA\", \"cpa_goal\": 15 }"
        ),
        "schema": {
            "type": "object",
            "properties": {
                "account_id": {"type": "string", "description": "Value from `account_id` field of search_accounts response. NOT the numeric ID."},
                "name": {"type": "string", "description": "Campaign name."},
                "marketing_objective": {
                    "type": "string",
                    "enum": ["BRAND_AWARENESS", "DRIVE_WEBSITE_TRAFFIC", "WEBSITE_ENGAGEMENT", "LEADS_GENERATION", "ONLINE_PURCHASES", "MOBILE_APP_INSTALL"],
                    "description": "Business goal. See tool description for bidding rules per value.",
                },
                "branding_text": {"type": "string", "description": "Brand name shown with ads."},
                "spending_limit_model": {
                    "type": "string",
                    "enum": ["NONE", "MONTHLY", "ENTIRE"],
                    "description": "Budget model.",
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
            "Edit scalar fields on an existing campaign. Partial-merge: only supplied fields are updated; "
            "fields you omit keep their current value. Re-sending the same value is a no-op.\n"
            "\n"
            "All amounts (spending_limit, daily_cap, cpc, cpa_goal, cpc_cap) are numbers in the account's default currency. Do not include a currency symbol or code.\n"
            "\n"
            "Required (always):\n"
            "- account_id (string): value from `account_id` field of search_accounts response (NOT numeric)\n"
            "- campaign_id (string): campaign to update\n"
            "- at least one updatable field below\n"
            "\n"
            "Updatable scalars (all optional):\n"
            "- name (string)\n"
            "- marketing_objective (string enum): BRAND_AWARENESS | DRIVE_WEBSITE_TRAFFIC | WEBSITE_ENGAGEMENT | LEADS_GENERATION | ONLINE_PURCHASES | MOBILE_APP_INSTALL\n"
            "- branding_text (string)\n"
            "- spending_limit_model (string enum): NONE | MONTHLY | ENTIRE\n"
            "- spending_limit (number)\n"
            "- daily_cap (number)\n"
            "- cpc (number)\n"
            "- bid_strategy (string enum): SMART | FIXED | TARGET_CPA | MAX_CONVERSIONS | MAX_VALUE\n"
            "- cpa_goal (number)\n"
            "- start_date (string, YYYY-MM-DD)\n"
            "- end_date (string, YYYY-MM-DD)\n"
            "- tracking_code (string)\n"
            "- cpc_cap (number)\n"
            "- comments (string)\n"
            "- daily_ad_delivery_model (string enum): BALANCED | STRICT (ACCELERATED deprecated, no longer accepted)\n"
            "- traffic_allocation_mode (string enum): OPTIMIZED (default) | EVEN\n"
            "- is_active (boolean): true to activate the campaign, false to pause. After create_campaign, campaigns ship paused; set is_active=true to launch.\n"
            "\n"
            "Conditional rules (apply when the gating field is in this request):\n"
            "- If you supply spending_limit_model = MONTHLY or ENTIRE, also supply spending_limit.\n"
            "- If you supply spending_limit_model = NONE, also supply daily_cap.\n"
            "- If you supply bid_strategy = TARGET_CPA, also supply cpa_goal.\n"
            "- If you supply BOTH start_date and end_date: end_date >= start_date.\n"
            "- Solo updates of partner fields (e.g., changing only spending_limit, or only cpa_goal) are allowed; the campaign's stored gating field is reused.\n"
            "\n"
            "Server-side constraints (will return 4xx if violated):\n"
            "- Some marketing_objective transitions are rejected mid-flight.\n"
            "- MOBILE_APP_INSTALL requires app fields (app_url, app_type, app_store) not yet supported here; switching to MOBILE_APP_INSTALL via this tool will likely 4xx.\n"
            "- Objective + bid_strategy combos must remain compatible.\n"
            "- Account permissions and policy review state may forbid certain edits.\n"
            "- TERMINATED campaigns cannot be reactivated; approval_state separately gates whether is_active=true actually serves ads.\n"
            "\n"
            "Read-only - NEVER send: id, advertiser_id, status, approval_state, spent, policy_review, pricing_model, target_cpa, target_cpa_learning_status. (target_cpa is server-recommended CPA range, not the user goal — set cpa_goal instead.)\n"
            "\n"
            "Not supported here. Use these dedicated tools for non-scalar updates:\n"
            "- geo targeting: update_campaign_geo_classic | update_campaign_geo_advanced\n"
            "- technology targeting (platform / os / browser / connection_type): update_campaign_techno\n"
            "- publisher / publisher-group targeting + per-publisher CPC bid modifiers: update_campaign_publishers\n"
            "- first-party + custom audience targeting: update_campaign_my_audiences\n"
            "- contextual segment targeting: update_campaign_contextual_segments\n"
            "- activity schedule (dayparting): update_campaign_schedule\n"
            "- conversion rule attachments: update_campaign_conversion_rules\n"
            "\n"
            "Examples:\n"
            "\n"
            "Rename and extend end date:\n"
            "{ \"account_id\": \"acme-inc\", \"campaign_id\": \"c-123\",\n"
            "  \"name\": \"Q2 Awareness v2\", \"end_date\": \"2026-09-30\" }\n"
            "\n"
            "Tighten target CPA:\n"
            "{ \"account_id\": \"acme-inc\", \"campaign_id\": \"c-123\", \"cpa_goal\": 12.5 }\n"
            "\n"
            "Switch budget model to monthly:\n"
            "{ \"account_id\": \"acme-inc\", \"campaign_id\": \"c-123\",\n"
            "  \"spending_limit_model\": \"MONTHLY\", \"spending_limit\": 5000 }\n"
            "\n"
            "Activate a paused campaign:\n"
            "{ \"account_id\": \"acme-inc\", \"campaign_id\": \"c-123\", \"is_active\": true }\n"
            "\n"
            "Pause a running campaign:\n"
            "{ \"account_id\": \"acme-inc\", \"campaign_id\": \"c-123\", \"is_active\": false }"
        ),
        "schema": {
            "type": "object",
            "properties": {
                "account_id": {"type": "string", "description": "Value from `account_id` field of search_accounts response. NOT the numeric ID."},
                "campaign_id": {"type": "string", "description": "Campaign ID to update."},
                "name": {"type": "string", "description": "Campaign name."},
                "marketing_objective": {
                    "type": "string",
                    "enum": ["BRAND_AWARENESS", "DRIVE_WEBSITE_TRAFFIC", "WEBSITE_ENGAGEMENT", "LEADS_GENERATION", "ONLINE_PURCHASES", "MOBILE_APP_INSTALL"],
                    "description": "Business goal. See tool description for bidding rules per value.",
                },
                "branding_text": {"type": "string", "description": "Brand name shown with ads."},
                "spending_limit_model": {
                    "type": "string",
                    "enum": ["NONE", "MONTHLY", "ENTIRE"],
                    "description": "Budget model.",
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
            "Update one classic geo targeting dimension on a campaign. Use this for campaigns that store "
            "geo in the classic shape. Call get_campaign first to detect which shape is in use: "
            "if the response has `geoTargeting`, use update_campaign_geo_advanced instead.\n"
            "\n"
            "Required:\n"
            "- account_id (string): from search_accounts.account_id (NOT numeric)\n"
            "- campaign_id (string)\n"
            "- dimension (enum): country | region | dma | city | postal_code\n"
            "- targeting (object): {type: INCLUDE | EXCLUDE | ALL, value: [string]}\n"
            "\n"
            "Semantics:\n"
            "- type=INCLUDE: only matched values are targeted.\n"
            "- type=EXCLUDE: matched values are excluded; everything else included.\n"
            "- type=ALL: clear this dimension. Send value: []. (type=ALL with non-empty value is rejected.)\n"
            "\n"
            "Server-side constraints (will return 4xx if violated):\n"
            "- Sub-dimension mutex. At most ONE of {region, dma, city, postal_code} may be set on a campaign at a time. "
            "To switch from one to another, FIRST clear the current dim with type=ALL, THEN set the new dim in a second call.\n"
            "- DMA only valid when country = INCLUDE [US].\n"
            "- Sub-dimension write requires exactly one INCLUDE country to already be set.\n"
            "- Region values are short-form (e.g., \"CA\"), NOT prefixed with country.\n"
            "- Country=ALL with empty value clears all sub-location restrictions on the campaign in one call.\n"
            "- The campaign's allowGeoTargeting flag may forbid geo updates entirely.\n"
            "- The campaign must currently use classic storage (no `geoTargeting` field set). "
            "Setting classic on an advanced-stored campaign returns 4xx.\n"
            "\n"
            "Examples:\n"
            "\n"
            "Target US and Canada by country:\n"
            "{ \"account_id\": \"acme-inc\", \"campaign_id\": \"c-123\", \"dimension\": \"country\",\n"
            "  \"targeting\": {\"type\": \"INCLUDE\", \"value\": [\"US\", \"CA\"]} }\n"
            "\n"
            "Switch from city to region targeting (TWO calls):\n"
            "1) {\"account_id\": \"acme-inc\", \"campaign_id\": \"c-123\", \"dimension\": \"city\", \"targeting\": {\"type\": \"ALL\", \"value\": []}}\n"
            "2) {\"account_id\": \"acme-inc\", \"campaign_id\": \"c-123\", \"dimension\": \"region\", \"targeting\": {\"type\": \"INCLUDE\", \"value\": [\"CA\", \"NY\"]}}\n"
            "\n"
            "Clear all geo restrictions in one call:\n"
            "{ \"account_id\": \"acme-inc\", \"campaign_id\": \"c-123\", \"dimension\": \"country\",\n"
            "  \"targeting\": {\"type\": \"ALL\", \"value\": []} }"
        ),
        "schema": {
            "type": "object",
            "properties": {
                "account_id": {"type": "string", "description": "Value from search_accounts.account_id (NOT numeric)."},
                "campaign_id": {"type": "string", "description": "Campaign ID to update."},
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
                    "description": "Targeting block. value=[] when type=ALL.",
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
            "Update a campaign's geo targeting using the advanced (MultiTargeting) shape. "
            "Requires the campaign to currently use advanced storage, OR the caller is intentionally "
            "migrating it from classic — sending advanced on a classic-storage campaign will clear classic "
            "fields and migrate the campaign one-way to advanced storage. Migration is logged in campaign history.\n"
            "\n"
            "Required:\n"
            "- account_id (string): from search_accounts.account_id (NOT numeric)\n"
            "- campaign_id (string)\n"
            "- geo_targeting (object): MultiTargeting wrapper\n"
            "\n"
            "geo_targeting shape:\n"
            "{\n"
            "  \"state\": \"ALL\" | \"EXISTS\",\n"
            "  \"value\": [\n"
            "    { \"type\": \"INCLUDE\" | \"EXCLUDE\",\n"
            "      \"value\": [\n"
            "        { \"country\": \"US\", \"region\": null, \"dma\": null, \"city\": null, \"postal_code\": null }\n"
            "      ]\n"
            "    }\n"
            "  ]\n"
            "}\n"
            "\n"
            "Semantics:\n"
            "- state=ALL clears all geo restrictions; send value: [].\n"
            "- state=EXISTS applies the rules in value (must be non-empty).\n"
            "- Each rule groups vectors of one type (INCLUDE or EXCLUDE).\n"
            "- A vector may set one geo dimension or mix dimensions (country=US AND region=CA targets California specifically).\n"
            "- Country: ISO-2 (e.g., \"US\").\n"
            "- DMA codes are US-only.\n"
            "- Server rejects: more than 200 exclude countries; sanctioned regions; invalid vector codes. The 4xx body is surfaced.\n"
            "\n"
            "Read-only fields are managed by the server. Do not include id, advertiser_id, status, etc.\n"
            "\n"
            "Examples:\n"
            "\n"
            "Target US and Canada, exclude Texas:\n"
            "{ \"account_id\": \"acme-inc\", \"campaign_id\": \"c-123\",\n"
            "  \"geo_targeting\": { \"state\": \"EXISTS\", \"value\": [\n"
            "    {\"type\": \"INCLUDE\", \"value\": [{\"country\": \"US\"}, {\"country\": \"CA\"}]},\n"
            "    {\"type\": \"EXCLUDE\", \"value\": [{\"country\": \"US\", \"region\": \"TX\"}]}\n"
            "  ]}}\n"
            "\n"
            "Clear all geo (target worldwide):\n"
            "{ \"account_id\": \"acme-inc\", \"campaign_id\": \"c-123\",\n"
            "  \"geo_targeting\": {\"state\": \"ALL\", \"value\": []} }"
        ),
        "schema": {
            "type": "object",
            "properties": {
                "account_id": {"type": "string", "description": "Value from search_accounts.account_id (NOT numeric)."},
                "campaign_id": {"type": "string", "description": "Campaign ID to update."},
                "geo_targeting": {
                    "type": "object",
                    "description": "Advanced (MultiTargeting) geo wrapper. state=ALL with value=[] clears geo; state=EXISTS applies the rules in value.",
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
            "Update one technology targeting dimension on a campaign: "
            "platform (device type), os (operating system), browser, or connection_type (network).\n"
            "\n"
            "Required:\n"
            "- account_id (string): from search_accounts.account_id (NOT numeric)\n"
            "- campaign_id (string)\n"
            "- dimension (enum): platform | os | browser | connection_type\n"
            "- targeting (object): {type: INCLUDE | EXCLUDE | ALL, value: [...]}\n"
            "\n"
            "Value shape depends on dimension:\n"
            "- platform | browser | connection_type: array of strings.\n"
            "- os: array of objects {os_family: string, sub_categories?: array of strings}. "
            "Omit sub_categories to target the entire family.\n"
            "\n"
            "Semantics:\n"
            "- type=INCLUDE: only matched values are targeted.\n"
            "- type=EXCLUDE: matched values are excluded; everything else included.\n"
            "- type=ALL: clear this dimension. Send value: []. (type=ALL with non-empty value is rejected.)\n"
            "\n"
            "Vocabulary (resolve via Realize UI or these upstream GET endpoints):\n"
            "- platform: /resources/platforms (e.g. DESK | PHON | TBLT). Documented as INCLUDE-only in some references; "
            "if the server rejects EXCLUDE/ALL on platform, the 4xx is surfaced unchanged.\n"
            "- os: /resources/campaigns_properties/operating_systems (families) and "
            "/resources/campaigns_properties/operating_systems/{osFamily} (sub-categories). "
            "Examples: os_family in {Android, iOS, Windows, Mac OS X, Linux}; sub_categories example: [\"iOS_8.4\", \"iOS_9\"].\n"
            "- browser: /resources/campaigns_properties/browsers (e.g. Chrome | Firefox | Safari | Edge).\n"
            "- connection_type: /resources/campaigns_properties/connection_types (e.g. WIFI | CELLULAR | OTHER).\n"
            "\n"
            "Read-only fields are managed by the server. Do not include id, advertiser_id, status, etc.\n"
            "\n"
            "Examples:\n"
            "\n"
            "Exclude desktop:\n"
            "{ \"account_id\": \"acme-inc\", \"campaign_id\": \"c-123\", \"dimension\": \"platform\",\n"
            "  \"targeting\": {\"type\": \"EXCLUDE\", \"value\": [\"DESK\"]} }\n"
            "\n"
            "Target Android entirely + iOS only on versions 16/17:\n"
            "{ \"account_id\": \"acme-inc\", \"campaign_id\": \"c-123\", \"dimension\": \"os\",\n"
            "  \"targeting\": {\"type\": \"INCLUDE\", \"value\": [\n"
            "    {\"os_family\": \"Android\"},\n"
            "    {\"os_family\": \"iOS\", \"sub_categories\": [\"iOS_16\", \"iOS_17\"]}\n"
            "  ]} }\n"
            "\n"
            "Clear browser targeting:\n"
            "{ \"account_id\": \"acme-inc\", \"campaign_id\": \"c-123\", \"dimension\": \"browser\",\n"
            "  \"targeting\": {\"type\": \"ALL\", \"value\": []} }"
        ),
        "schema": {
            "type": "object",
            "properties": {
                "account_id": {"type": "string", "description": "Value from search_accounts.account_id (NOT numeric)."},
                "campaign_id": {"type": "string", "description": "Campaign ID to update."},
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
                    "description": "Targeting block. value=[] when type=ALL.",
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
            "Update first-party + custom audience targeting on a campaign. Posts to the dedicated "
            "my_audiences sub-endpoint, replacing the campaign's current audience targeting "
            "collection with the supplied rules.\n"
            "\n"
            "Required:\n"
            "- account_id (string): from search_accounts.account_id (NOT numeric)\n"
            "- campaign_id (string)\n"
            "- targeting (object): {collection: [rules]}\n"
            "\n"
            "Each rule:\n"
            "  {collection: [audience_id, ...], type: \"INCLUDE\" | \"EXCLUDE\"}\n"
            "\n"
            "audience_id values are numeric audience IDs (integers). Source via Realize UI or the "
            "GET /backstage/api/1.0/{account_id}/my_audiences/{audience_id} reference endpoint.\n"
            "\n"
            "Semantics:\n"
            "- Each rule groups audience IDs of one targeting type (INCLUDE or EXCLUDE).\n"
            "- INCLUDE rules add the listed audiences; EXCLUDE rules suppress them.\n"
            "- This endpoint REPLACES the entire audience targeting collection on each call. "
            "Send the full desired set, not a delta.\n"
            "- To clear audience targeting, send {\"collection\": []}.\n"
            "- ALL is not part of this endpoint's vocab; only INCLUDE and EXCLUDE.\n"
            "\n"
            "NOT supported here:\n"
            "- Lookalike audience targeting. Different shape (ruleId, similarityLevel) and endpoint; "
            "separate tool forthcoming.\n"
            "- Reading current audience targeting. Use get_campaign or a future read tool.\n"
            "\n"
            "Read-only fields are managed by the server. Do not include audience names, descriptions, etc.\n"
            "\n"
            "Examples:\n"
            "\n"
            "Include two audiences, exclude two:\n"
            "{ \"account_id\": \"acme-inc\", \"campaign_id\": \"c-123\",\n"
            "  \"targeting\": {\n"
            "    \"collection\": [\n"
            "      {\"collection\": [224820, 25287], \"type\": \"INCLUDE\"},\n"
            "      {\"collection\": [19884, 29870], \"type\": \"EXCLUDE\"}\n"
            "    ]\n"
            "  } }\n"
            "\n"
            "Clear all audience targeting:\n"
            "{ \"account_id\": \"acme-inc\", \"campaign_id\": \"c-123\",\n"
            "  \"targeting\": {\"collection\": []} }"
        ),
        "schema": {
            "type": "object",
            "properties": {
                "account_id": {"type": "string", "description": "Value from search_accounts.account_id (NOT numeric)."},
                "campaign_id": {"type": "string", "description": "Campaign ID to update."},
                "targeting": {
                    "type": "object",
                    "description": "Audience targeting wrapper. Send {collection: []} to clear.",
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
            "required": ["account_id", "campaign_id", "targeting"],
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
            "Update lookalike audience targeting on a campaign. Posts to the dedicated "
            "targeting/lookalike_audience sub-endpoint, replacing the campaign's current "
            "lookalike audience targeting wholesale.\n"
            "\n"
            "Required:\n"
            "- account_id (string): from search_accounts.account_id (NOT numeric)\n"
            "- campaign_id (string)\n"
            "- targeting (object): {collection: [block]}, where block is INCLUDE-only\n"
            "\n"
            "Block shape:\n"
            "  {type: \"INCLUDE\", collection: [{rule_id, similarity_level}, ...]}\n"
            "\n"
            "Inner item:\n"
            "- rule_id (integer): unip rule ID for a lookalike audience. Source via the Realize "
            "UI or the GET /backstage/api/1.0/{account_id}/lookalike_audiences endpoint.\n"
            "- similarity_level (integer): allowed values depend on the audience subtype: "
            "CRM lookalike accepts 5/10/15/20/25; pixel lookalike accepts 5; predictive (PBP) "
            "accepts 1/2/3/4/5. The server resolves the subtype from rule_id and rejects mismatches.\n"
            "\n"
            "Semantics:\n"
            "- At most one block in the outer collection (server constraint).\n"
            "- Only INCLUDE is supported (EXCLUDE/ALL are rejected by the server).\n"
            "- Replace-style: send the full desired set on each call.\n"
            "- To clear lookalike targeting, send {\"collection\": []}.\n"
            "- Predictive (PBP) lookalikes can only be added at campaign creation time, not on "
            "existing campaigns; the server rejects them via this update tool.\n"
            "\n"
            "Server-side preconditions (will return 4xx if violated):\n"
            "- Account must have user-segments edit permission.\n"
            "- Campaign must allow retargeting.\n"
            "- All rule_ids must resolve to lookalike-class audiences with valid CRM segments.\n"
            "\n"
            "NOT supported here:\n"
            "- First-party + custom audience targeting. Use update_campaign_my_audiences.\n"
            "- Reading current lookalike targeting. The lookalike block is filtered out of "
            "get_campaign; use the dedicated GET sub-endpoint if needed.\n"
            "\n"
            "Examples:\n"
            "\n"
            "Add two CRM lookalikes at 10% similarity:\n"
            "{ \"account_id\": \"acme-inc\", \"campaign_id\": \"c-123\",\n"
            "  \"targeting\": {\n"
            "    \"collection\": [\n"
            "      {\"type\": \"INCLUDE\", \"collection\": [\n"
            "        {\"rule_id\": 1234567, \"similarity_level\": 10},\n"
            "        {\"rule_id\": 7654321, \"similarity_level\": 5}\n"
            "      ]}\n"
            "    ]\n"
            "  } }\n"
            "\n"
            "Clear lookalike targeting:\n"
            "{ \"account_id\": \"acme-inc\", \"campaign_id\": \"c-123\",\n"
            "  \"targeting\": {\"collection\": []} }"
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
                    "description": "Campaign ID to update.",
                },
                "targeting": {
                    "type": "object",
                    "description": "Lookalike audience targeting wrapper. Send {collection: []} to clear.",
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
                                                    "description": "Unip rule ID for the lookalike audience.",
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
            "required": ["account_id", "campaign_id", "targeting"],
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
            "Update a campaign's activity schedule (dayparting). Sets when the campaign is allowed "
            "to serve, by day-of-week + hour ranges, in the campaign's specified time zone.\n"
            "\n"
            "Required:\n"
            "- account_id (string): from search_accounts.account_id (NOT numeric)\n"
            "- campaign_id (string)\n"
            "- schedule (object): {mode, time_zone?, rules?}\n"
            "\n"
            "Schedule shape:\n"
            "- mode (string, required): \"ALWAYS\" | \"CUSTOM\"\n"
            "- time_zone (string): IANA name (e.g. \"America/New_York\"). Required when mode=CUSTOM.\n"
            "- rules (array): required when mode=CUSTOM, must be omitted (or []) when mode=ALWAYS.\n"
            "\n"
            "Each rule:\n"
            "{\n"
            "  type:       \"INCLUDE\" | \"EXCLUDE\",\n"
            "  day:        \"MONDAY\" | \"TUESDAY\" | \"WEDNESDAY\" | \"THURSDAY\" | \"FRIDAY\" | \"SATURDAY\" | \"SUNDAY\",\n"
            "  from_hour:  integer in [0, 23],\n"
            "  until_hour: integer in [1, 24]   (must be > from_hour)\n"
            "}\n"
            "\n"
            "Semantics:\n"
            "- mode=ALWAYS: campaign serves every day, all hours; clears any prior CUSTOM schedule.\n"
            "- mode=CUSTOM: rules array defines INCLUDE windows (when serving is allowed) and EXCLUDE windows "
            "(when serving is suppressed). Days not mentioned default to INCLUDE 0-24 (server auto-fills); "
            "you do not need to enumerate all seven days.\n"
            "\n"
            "Server-side constraints (will return 4xx if violated):\n"
            "- Same day cannot have both INCLUDE and EXCLUDE rules. Pick one type per day.\n"
            "- Time windows on the same day cannot overlap.\n"
            "- The campaign's account must have the schedule permission enabled (else 403).\n"
            "- Per-publisher minimum-window duration may apply (some publishers require windows of at least N consecutive hours).\n"
            "- time_zone must be a supported IANA name.\n"
            "\n"
            "Read-only fields are managed by the server. Do not include id, advertiser_id, status, etc.\n"
            "\n"
            "Examples:\n"
            "\n"
            "Mon-Fri 9am-9pm Eastern, no weekends:\n"
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
            "Always-on (clear schedule):\n"
            "{ \"account_id\": \"acme-inc\", \"campaign_id\": \"c-123\",\n"
            "  \"schedule\": {\"mode\": \"ALWAYS\"} }"
        ),
        "schema": {
            "type": "object",
            "properties": {
                "account_id": {"type": "string", "description": "Value from search_accounts.account_id (NOT numeric)."},
                "campaign_id": {"type": "string", "description": "Campaign ID to update."},
                "schedule": {
                    "type": "object",
                    "description": "Activity schedule (dayparting). mode=ALWAYS runs continuously; mode=CUSTOM applies the rules array in the supplied time_zone.",
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
            "Replace the conversion rules attached to a campaign. Conversion rules tell Realize "
            "which on-site events count as conversions (purchase, lead, signup, etc.) for this "
            "campaign's optimization and reporting.\n"
            "\n"
            "Required:\n"
            "- account_id (string): from search_accounts.account_id (NOT numeric)\n"
            "- campaign_id (string)\n"
            "- conversion_rules (array): list of rule references in the form {\"id\": \"<rule_id>\"}\n"
            "\n"
            "Semantics:\n"
            "- Full-replace: the supplied list replaces the campaign's current attachments wholesale.\n"
            "- To detach all rules, send conversion_rules: [].\n"
            "- To add or remove a single rule, first read the campaign with get_campaign, modify the "
            "list locally, then send the merged result. There is no incremental ADD/REMOVE operation.\n"
            "\n"
            "Discovery:\n"
            "- This tool does not list available rule ids. Rule ids are authored in the Realize UI "
            "(Conversions section) or can be read off an existing campaign via get_campaign.\n"
            "\n"
            "Server-side constraints (will return 4xx if violated):\n"
            "- Each rule id must already exist under the account.\n"
            "- Campaigns with marketing_objective LEADS_GENERATION or ONLINE_PURCHASES typically "
            "require at least one conversion rule; sending [] on those will be rejected.\n"
            "- Some rule types are incompatible with some campaign configurations.\n"
            "\n"
            "Read-only fields are managed by the server. Do not include id, advertiser_id, status, etc.\n"
            "\n"
            "Examples:\n"
            "\n"
            "Attach two rules:\n"
            "{ \"account_id\": \"acme-inc\", \"campaign_id\": \"c-123\",\n"
            "  \"conversion_rules\": [\n"
            "    {\"id\": \"rule_purchase_main\"},\n"
            "    {\"id\": \"rule_addtocart_main\"}\n"
            "  ] }\n"
            "\n"
            "Detach all rules:\n"
            "{ \"account_id\": \"acme-inc\", \"campaign_id\": \"c-123\",\n"
            "  \"conversion_rules\": [] }"
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
                    "description": "Campaign ID to update.",
                },
                "conversion_rules": {
                    "type": "array",
                    "description": "Full-replace list of rule references. Send [] to detach all.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {
                                "type": "string",
                                "description": "Conversion rule ID (from the Realize UI Conversions section, or get_campaign).",
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
            "Update publisher-level targeting on a campaign: which publishers run, which "
            "publisher groups, and per-publisher CPC bid modifiers. Send any subset of the "
            "three fields; at least one is required.\n"
            "\n"
            "Required:\n"
            "- account_id (string): from search_accounts.account_id (NOT numeric)\n"
            "- campaign_id (string)\n"
            "- at least one of: publisher_targeting, publisher_groups_targeting, publisher_bid_modifier\n"
            "\n"
            "publisher_targeting (object, optional):\n"
            "- {type: INCLUDE | EXCLUDE | ALL, value: [<publisher_name>, ...]}\n"
            "- type=INCLUDE: only listed publishers run.\n"
            "- type=EXCLUDE: listed publishers blocked, all others allowed.\n"
            "- type=ALL: clear publisher targeting (send value=[]).\n"
            "- Values are publisher NAMES (strings), not numeric IDs; the server resolves names.\n"
            "\n"
            "publisher_groups_targeting (object, optional):\n"
            "- {type: INCLUDE | EXCLUDE | ALL, value: [<group_name>, ...]}\n"
            "- Same INCLUDE / EXCLUDE / ALL semantics as publisher_targeting.\n"
            "- Values are publisher-group NAMES (strings), not IDs.\n"
            "- Account-level publisher-group restrictions can override campaign-level "
            "INCLUDE/EXCLUDE; server may 4xx if a blocked group is targeted.\n"
            "\n"
            "publisher_bid_modifier (object, optional):\n"
            "- {values: [{target: <publisher_name>, cpc_modification: <number>}]}\n"
            "- FULL REPLACE: the supplied values replace the campaign's current per-publisher "
            "modifiers wholesale. Omit a publisher to drop its modifier; send values=[] to clear all.\n"
            "- cpc_modification is a multiplier on the campaign CPC (e.g. 1.25 = +25%, 0.8 = -20%).\n"
            "- Each target must be unique; cpc_modification must be a finite number.\n"
            "- To incrementally add/remove a single entry, first read the campaign with "
            "get_campaign, modify the list locally, then send the merged result.\n"
            "\n"
            "Read-only fields are managed by the server. Do not include id, advertiser_id, status, etc.\n"
            "\n"
            "Examples:\n"
            "\n"
            "Block two publishers:\n"
            "{ \"account_id\": \"acme-inc\", \"campaign_id\": \"c-123\",\n"
            "  \"publisher_targeting\": {\"type\": \"EXCLUDE\", \"value\": [\"pub_alpha\", \"pub_beta\"]} }\n"
            "\n"
            "Restrict to a single publisher group:\n"
            "{ \"account_id\": \"acme-inc\", \"campaign_id\": \"c-123\",\n"
            "  \"publisher_groups_targeting\": {\"type\": \"INCLUDE\", \"value\": [\"premium_news\"]} }\n"
            "\n"
            "Set per-publisher CPC modifiers (full replace):\n"
            "{ \"account_id\": \"acme-inc\", \"campaign_id\": \"c-123\",\n"
            "  \"publisher_bid_modifier\": {\"values\": [\n"
            "    {\"target\": \"pub_alpha\", \"cpc_modification\": 1.25},\n"
            "    {\"target\": \"pub_gamma\", \"cpc_modification\": 0.8}\n"
            "  ]} }\n"
            "\n"
            "Clear publisher targeting and all per-publisher CPC modifiers in one call:\n"
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
                    "description": "Campaign ID to update.",
                },
                "publisher_targeting": {
                    "type": "object",
                    "description": "Optional. {type, value} block. value=[] when type=ALL. Values are publisher names.",
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
                    "description": "Optional. {type, value} block. value=[] when type=ALL. Values are publisher-group names.",
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
                    "description": "Optional. Full-replace list of per-publisher CPC modifiers. values=[] clears all.",
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
            "Replace the contextual segment targeting attached to a campaign. Contextual "
            "segments narrow delivery to pages whose content matches a Realize-curated topic "
            "(e.g. automotive, finance) using INCLUDE/EXCLUDE rules over integer segment IDs.\n"
            "\n"
            "Required:\n"
            "- account_id (string): from search_accounts.account_id (NOT numeric)\n"
            "- campaign_id (string)\n"
            "- contextual_segments (object): {\"collection\": [...]} where each entry is "
            "{\"type\": INCLUDE | EXCLUDE, \"collection\": [<segment_id>, ...]}\n"
            "\n"
            "Semantics:\n"
            "- Full-replace: the supplied object replaces the campaign's current contextual "
            "targeting wholesale.\n"
            "- To clear all contextual targeting, send contextual_segments: {\"collection\": []}.\n"
            "- At most one INCLUDE block and one EXCLUDE block; duplicate types are rejected.\n"
            "- Segment IDs are integers (e.g. 1900004), not names. They are not discoverable via "
            "this MCP server — author them in the Realize UI or read them off an existing "
            "campaign with get_campaign.\n"
            "- To incrementally add or remove a single segment, first read the campaign with "
            "get_campaign, modify the lists locally, then send the merged result. There is no "
            "incremental ADD/REMOVE operation.\n"
            "\n"
            "Server-side constraints (will return 4xx if violated):\n"
            "- Each segment ID must exist and be of contextual data type (not third-party).\n"
            "- Campaign must support contextual targeting (account/campaign type dependent).\n"
            "\n"
            "Examples:\n"
            "\n"
            "Target three contextual segments:\n"
            "{ \"account_id\": \"acme-inc\", \"campaign_id\": \"c-123\",\n"
            "  \"contextual_segments\": {\"collection\": [\n"
            "    {\"type\": \"INCLUDE\", \"collection\": [1900004, 1900024, 1900037]}\n"
            "  ]} }\n"
            "\n"
            "Combine an include and exclude block:\n"
            "{ \"account_id\": \"acme-inc\", \"campaign_id\": \"c-123\",\n"
            "  \"contextual_segments\": {\"collection\": [\n"
            "    {\"type\": \"INCLUDE\", \"collection\": [1900004, 1900024]},\n"
            "    {\"type\": \"EXCLUDE\", \"collection\": [1900100]}\n"
            "  ]} }\n"
            "\n"
            "Clear all contextual segment targeting:\n"
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
                    "description": "Campaign ID to update.",
                },
                "contextual_segments": {
                    "type": "object",
                    "description": (
                        "Full-replace contextual targeting. Send {\"collection\": []} to clear all."
                    ),
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
        "description": "Get all items for a campaign (read-only). WORKFLOW REQUIRED: First use search_accounts to get account_id, then use that value here. Example: 1) search_accounts('company_name') 2) Extract 'account_id' from results 3) Use account_id parameter here",
        "schema": {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string", 
                    "description": "Account ID (string from search_accounts response 'account_id' field - NOT numeric ID). Workflow: 1) search_accounts('query') 2) Use 'account_id' from results"
                },
                "campaign_id": {
                    "type": "string", 
                    "description": "Campaign ID"
                }
            },
            "required": ["account_id", "campaign_id"]
        },
        "handler": "campaign_handlers.get_campaign_items",
        "category": "campaign_items"
    },

    "get_campaign_item": {
        "description": "Get specific campaign item details (read-only). WORKFLOW REQUIRED: First use search_accounts to get account_id, then use that value here. Example: 1) search_accounts('company_name') 2) Extract 'account_id' from results 3) Use account_id parameter here",
        "schema": {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string", 
                    "description": "Account ID (string from search_accounts response 'account_id' field - NOT numeric ID). Workflow: 1) search_accounts('query') 2) Use 'account_id' from results"
                },
                "campaign_id": {
                    "type": "string", 
                    "description": "Campaign ID"
                },
                "item_id": {
                    "type": "string", 
                    "description": "Item ID to get details for"
                }
            },
            "required": ["account_id", "campaign_id", "item_id"]
        },
        "handler": "campaign_handlers.get_campaign_item",
        "category": "campaign_items"
    },

    # Reporting Tools (READ-ONLY)

    "get_top_campaign_content_report": {
        "description": "Get top performing campaign content report in CSV format (read-only). Returns compact CSV data with summary header for maximum efficiency. IMPORTANT: Each call provides complete, actionable data - do NOT retry unless there's an explicit error. WORKFLOW: 1) search_accounts('company_name') 2) Extract 'account_id' from results 3) Use account_id parameter here. Response includes CSV format with clear headers and pagination info. PAGINATION: Results are paginated with two controls: page_size (1-100, default: 20) and page (page number, default: 1). Check 'Total' in response header for full record count.",
        "schema": {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string", 
                    "description": "Account ID (string from search_accounts response 'account_id' field - NOT numeric ID). Workflow: 1) search_accounts('query') 2) Use 'account_id' from results"
                },
                "start_date": {
                    "type": "string", 
                    "description": "Start date (YYYY-MM-DD)"
                },
                "end_date": {
                    "type": "string", 
                    "description": "End date (YYYY-MM-DD)"
                },
                "page": {
                    "type": "integer",
                    "default": 1,
                    "minimum": 1,
                    "description": "Page number for pagination (default: 1)"
                },
                "page_size": {
                    "type": "integer",
                    "default": 20,
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Records per page (default: 20, max: 100)"
                },
                "sort_field": {
                    "type": "string",
                    "enum": ["clicks", "spent", "impressions"],
                    "description": "Optional sort field name. Available fields: clicks, spent, impressions. When specified, sorts by this field."
                },
                "sort_direction": {
                    "type": "string",
                    "enum": ["ASC", "DESC"],
                    "default": "DESC",
                    "description": "Sort direction: ASC (ascending) or DESC (descending). Default: DESC"
                }
            },
            "required": ["account_id", "start_date", "end_date"]
        },
        "handler": "report_handlers.get_top_campaign_content_report",
        "category": "reports"
    },

    "get_campaign_history_report": {
        "description": "Get campaign history report in CSV format (read-only). Returns compact CSV data with historical metrics for maximum efficiency. IMPORTANT: Each call provides complete, actionable data - do NOT retry unless there's an explicit error. WORKFLOW: 1) search_accounts('company_name') 2) Extract 'account_id' from results 3) Use account_id parameter here. Response includes CSV format with clear headers and pagination info. PAGINATION: Results are paginated with two controls: page_size (1-100, default: 20) and page (page number, default: 1). Check 'Total' in response header for full record count.",
        "schema": {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string", 
                    "description": "Account ID (string from search_accounts response 'account_id' field - NOT numeric ID). Workflow: 1) search_accounts('query') 2) Use 'account_id' from results"
                },
                "start_date": {
                    "type": "string", 
                    "description": "Start date (YYYY-MM-DD)"
                },
                "end_date": {
                    "type": "string", 
                    "description": "End date (YYYY-MM-DD)"
                },
                "page": {
                    "type": "integer",
                    "default": 1,
                    "minimum": 1,
                    "description": "Page number for pagination (default: 1)"
                },
                "page_size": {
                    "type": "integer",
                    "default": 20,
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Records per page (default: 20, max: 100)"
                }
            },
            "required": ["account_id", "start_date", "end_date"]
        },
        "handler": "report_handlers.get_campaign_history_report",
        "category": "reports"
    },

    "get_campaign_breakdown_report": {
        "description": "Get campaign breakdown report in CSV format (read-only). Returns compact CSV data with campaign metrics for maximum efficiency. IMPORTANT: Each call provides complete, actionable data - do NOT retry unless there's an explicit error. WORKFLOW: 1) search_accounts('company_name') 2) Extract 'account_id' from results 3) Use account_id parameter here. Response includes CSV format with clear headers and pagination info. PAGINATION: Results are paginated with two controls: page_size (1-100, default: 20) and page (page number, default: 1). Check 'Total' in response header for full record count.",
        "schema": {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string", 
                    "description": "Account ID (string from search_accounts response 'account_id' field - NOT numeric ID). Workflow: 1) search_accounts('query') 2) Use 'account_id' from results"
                },
                "start_date": {
                    "type": "string", 
                    "description": "Start date (YYYY-MM-DD)"
                },
                "end_date": {
                    "type": "string", 
                    "description": "End date (YYYY-MM-DD)"
                },
                "filters": {
                    "type": "object", 
                    "description": "Optional filters (flexible JSON object)",
                    "additionalProperties": {"type": "string"}
                },
                "page": {
                    "type": "integer",
                    "default": 1,
                    "minimum": 1,
                    "description": "Page number for pagination (default: 1)"
                },
                "page_size": {
                    "type": "integer",
                    "default": 20,
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Records per page (default: 20, max: 100)"
                },
                "sort_field": {
                    "type": "string",
                    "enum": ["clicks", "spent", "impressions"],
                    "description": "Optional sort field name. Available fields: clicks, spent, impressions. When specified, sorts by this field."
                },
                "sort_direction": {
                    "type": "string",
                    "enum": ["ASC", "DESC"],
                    "default": "DESC",
                    "description": "Sort direction: ASC (ascending) or DESC (descending). Default: DESC"
                }
            },
            "required": ["account_id", "start_date", "end_date"]
        },
        "handler": "report_handlers.get_campaign_breakdown_report",
        "category": "reports"
    },

    "get_campaign_site_day_breakdown_report": {
        "description": "Get campaign site day breakdown report in CSV format (read-only). Returns compact CSV data with site/day metrics for maximum efficiency. IMPORTANT: Each call provides complete, actionable data - do NOT retry unless there's an explicit error. WORKFLOW: 1) search_accounts('company_name') 2) Extract 'account_id' from results 3) Use account_id parameter here. Response includes CSV format with clear headers and pagination info. PAGINATION: Results are paginated with two controls: page_size (1-100, default: 20) and page (page number, default: 1). Check 'Total' in response header for full record count.",
        "schema": {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string", 
                    "description": "Account ID (string from search_accounts response 'account_id' field - NOT numeric ID). Workflow: 1) search_accounts('query') 2) Use 'account_id' from results"
                },
                "start_date": {
                    "type": "string", 
                    "description": "Start date (YYYY-MM-DD)"
                },
                "end_date": {
                    "type": "string", 
                    "description": "End date (YYYY-MM-DD)"
                },
                "filters": {
                    "type": "object", 
                    "description": "Optional filters (flexible JSON object)",
                    "additionalProperties": {"type": "string"}
                },
                "page": {
                    "type": "integer",
                    "default": 1,
                    "minimum": 1,
                    "description": "Page number for pagination (default: 1)"
                },
                "page_size": {
                    "type": "integer",
                    "default": 20,
                    "minimum": 1,
                    "maximum": 100,
                    "description": "Records per page (default: 20, max: 100)"
                },
                "sort_field": {
                    "type": "string",
                    "enum": ["clicks", "spent", "impressions"],
                    "description": "Optional sort field name. Available fields: clicks, spent, impressions. When specified, sorts by this field."
                },
                "sort_direction": {
                    "type": "string",
                    "enum": ["ASC", "DESC"],
                    "default": "DESC",
                    "description": "Sort direction: ASC (ascending) or DESC (descending). Default: DESC"
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