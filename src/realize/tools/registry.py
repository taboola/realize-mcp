"""Centralized registry for all MCP tools."""
import copy


_TARGETING_BLOCKS_NOTE = (
    "Targeting blocks are FULL-REPLACE: sending `my_audiences` with one audience "
    "wipes the others; sending `geo_targeting` replaces all geo. To edit a single "
    "entry, read with get_campaign, modify locally, send the merged result. "
    "Scalar fields (name, cpc, is_active, …) are partial-merge — omitted scalars keep "
    "their prior value."
)


_GEO_ADVANCED_SCHEMA = {
    "type": "object",
    "description": (
        "Advanced (MultiTargeting) geo targeting. {state, value}. state=ALL with "
        "value=[] clears geo. state=EXISTS applies the rules in value. "
        "Each rule: {type: INCLUDE|EXCLUDE, value: [{country, region?, dma?, city?, postal_code?}]}. "
        "Mix dims in one vector to AND them (country=US + region=CA = California). "
        "Discover codes via search_geos."
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


def _classic_geo_schema(dim: str, *, sub_dim: bool) -> dict:
    note = (
        f"Classic {dim} targeting (update only). {{type: INCLUDE|EXCLUDE|ALL, value: [string]}}. "
        f"value=[] when type=ALL. "
    )
    if sub_dim:
        note += (
            f"Sub-dimension mutex: at most ONE of region/dma/city/postal_code on a campaign; "
            f"requires INCLUDE country already set. "
        )
    note += "Mutually exclusive with geo_targeting (advanced) in same request."
    return {
        "type": "object",
        "description": note,
        "properties": {
            "type": {"type": "string", "enum": ["INCLUDE", "EXCLUDE", "ALL"]},
            "value": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["type", "value"],
    }


def _techno_schema(dim: str, value_doc: str) -> dict:
    return {
        "type": "object",
        "description": (
            f"{dim} targeting. {{type: INCLUDE|EXCLUDE|ALL, value: [...]}}. "
            f"value=[] when type=ALL. {value_doc} Discover values via search_techno."
        ),
        "properties": {
            "type": {"type": "string", "enum": ["INCLUDE", "EXCLUDE", "ALL"]},
            "value": {
                "type": "array",
                "items": (
                    {"type": "string"} if dim != "os"
                    else {
                        "type": "object",
                        "properties": {
                            "os_family": {"type": "string"},
                            "sub_categories": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["os_family"],
                    }
                ),
            },
        },
        "required": ["type", "value"],
    }


_ACTIVITY_SCHEDULE_SCHEMA = {
    "type": "object",
    "description": (
        "Activity schedule (dayparting). {mode: ALWAYS|CUSTOM, time_zone?, rules?}. "
        "mode=ALWAYS clears any custom schedule. mode=CUSTOM requires time_zone (IANA name; "
        "discover via list_realize_resource resource=time_zones) and rules. "
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


_CONVERSION_RULES_SCHEMA = {
    "type": "array",
    "description": (
        "Conversion rule attachments. List of {id} objects. Send [] to detach all. "
        "Rule IDs are authored in the Realize UI (Conversions section); not discoverable here. "
        "LEADS_GENERATION / ONLINE_PURCHASES typically require >=1 rule."
    ),
    "items": {
        "type": "object",
        "properties": {"id": {"type": "integer"}},
        "required": ["id"],
    },
}


_PUBLISHER_TARGETING_SCHEMA = {
    "type": "object",
    "description": (
        "Publisher targeting. {type: INCLUDE|EXCLUDE|ALL, value: [publisher_name]}. "
        "value=[] when type=ALL. Names (not IDs) — server resolves them."
    ),
    "properties": {
        "type": {"type": "string", "enum": ["INCLUDE", "EXCLUDE", "ALL"]},
        "value": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["type", "value"],
}


_PUBLISHER_GROUPS_TARGETING_SCHEMA = {
    "type": "object",
    "description": (
        "Publisher-groups targeting. Same shape as publisher_targeting but values are group names."
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
        "cpc_modification is a multiplier (1.25 = +25%). values=[] clears all modifiers."
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


_MY_AUDIENCES_SCHEMA = {
    "type": "object",
    "description": (
        "First-party + custom audience targeting. {collection: [{type: INCLUDE|EXCLUDE, collection: [int]}]}. "
        "Send {collection: []} to clear. Audience IDs sourced from the Realize UI (Audiences section)."
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
        "rule_id from the Realize UI (Audiences > Lookalike). PBP audiences must be created in the UI."
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


_SCALAR_PROPERTIES = {
    "name": {"type": "string", "description": "Campaign name."},
    "marketing_objective": {
        "type": "string",
        "enum": ["BRAND_AWARENESS", "DRIVE_WEBSITE_TRAFFIC", "LEADS_GENERATION", "ONLINE_PURCHASES", "MOBILE_APP_INSTALL"],
        "description": "Business goal. Determines required bidding fields.",
    },
    "branding_text": {"type": "string", "description": "Brand name shown with ads."},
    "spending_limit_model": {
        "type": "string",
        "enum": ["NONE", "MONTHLY", "ENTIRE"],
        "description": "Budget model. NONE = no overall cap (uses daily_cap). MONTHLY = monthly cap. ENTIRE = lifetime cap.",
    },
    "spending_limit": {"type": "number", "description": "Budget amount in account's default currency."},
    "daily_cap": {"type": "number", "description": "Daily spend cap in account's default currency."},
    "cpc": {"type": "number", "description": "Fixed cost per click in account's default currency."},
    "bid_strategy": {
        "type": "string",
        "enum": ["SMART", "FIXED", "TARGET_CPA", "MAX_CONVERSIONS", "MAX_VALUE"],
        "description": "Bidding strategy.",
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
    "platform_targeting": _techno_schema("platform", "Common values: DESK | PHON | TBLT."),
    "os_targeting": _techno_schema("os", "Items: {os_family, sub_categories?}. os_family in {Android, iOS, Windows, Mac OS X, Linux}."),
    "browser_targeting": _techno_schema("browser", "Common values: Chrome | Firefox | Safari | Edge."),
    "connection_type_targeting": _techno_schema("connection_type", "Common values: WIFI | CELLULAR | OTHER."),
    "activity_schedule": _ACTIVITY_SCHEDULE_SCHEMA,
    "conversion_rules": _CONVERSION_RULES_SCHEMA,
    "publisher_targeting": _PUBLISHER_TARGETING_SCHEMA,
    "publisher_groups_targeting": _PUBLISHER_GROUPS_TARGETING_SCHEMA,
    "publisher_bid_modifier": _PUBLISHER_BID_MODIFIER_SCHEMA,
    "contextual_segments": _CONTEXTUAL_SEGMENTS_SCHEMA,
    "my_audiences": _MY_AUDIENCES_SCHEMA,
    "lookalike_audience": _LOOKALIKE_AUDIENCE_SCHEMA,
}


_UPDATE_CLASSIC_GEO_PROPERTIES = {
    "country_targeting": _classic_geo_schema("country", sub_dim=False),
    "region_targeting": _classic_geo_schema("region", sub_dim=True),
    "dma_targeting": _classic_geo_schema("dma", sub_dim=True),
    "city_targeting": _classic_geo_schema("city", sub_dim=True),
    "postal_code_targeting": _classic_geo_schema("postal_code", sub_dim=True),
}


_CREATE_CAMPAIGN_DESCRIPTION = (
    "Create a campaign on a Realize account, with full targeting in one call. Returns the created campaign "
    "(`id`, `status=PAUSED`); ships paused, won't serve until items are added (set `is_active=true` to launch).\n"
    "\n"
    f"{_TARGETING_BLOCKS_NOTE}\n"
    "\n"
    "Geo: accepts `geo_targeting` (advanced/MultiTargeting) only. Classic geo fields rejected on create. "
    "Use update_campaign for classic geo edits on existing classic-storage campaigns.\n"
    "\n"
    "All amounts (spending_limit, daily_cap, cpc, cpa_goal, cpc_cap) are numbers in the account's default currency.\n"
    "\n"
    "Conditional rules:\n"
    "- spending_limit_model = MONTHLY|ENTIRE → also send spending_limit. NONE → also send daily_cap.\n"
    "- marketing_objective = BRAND_AWARENESS|DRIVE_WEBSITE_TRAFFIC → send cpc; bid_strategy SMART (default) or FIXED; omit cpa_goal.\n"
    "- marketing_objective = LEADS_GENERATION|ONLINE_PURCHASES|MOBILE_APP_INSTALL → bid_strategy = TARGET_CPA|MAX_CONVERSIONS|MAX_VALUE; if TARGET_CPA also send cpa_goal; omit cpc.\n"
    "- If both start_date and end_date sent: end_date >= start_date.\n"
    "\n"
    "Discovery:\n"
    "- search_geos — countries, regions, dma, cities, postal_codes (for `geo_targeting`).\n"
    "- search_techno — platforms, OS families/versions, browsers, connection types.\n"
    "- list_realize_resource — marketing_objectives, bid_strategies, spending_limit_models, time_zones.\n"
    "\n"
    "Read-only — NEVER send: id, advertiser_id, status, approval_state, spent, policy_review, pricing_model, "
    "target_cpa, target_cpa_learning_status. (`target_cpa` is server-recommended; user goal is `cpa_goal`.)\n"
    "\n"
    "Behind the scenes the MCP fans out to Backstage: main POST + (optional) my_audiences / lookalike_audience / "
    "contextual_segments sub-resources. If a sub-resource POST fails after the campaign is created, response includes "
    "`partial_failures` so the caller can retry just that section via update_campaign.\n"
    "\n"
    "Example — lead gen with geo + audience targeting:\n"
    "{ \"account_id\": \"acme-inc\", \"name\": \"Q2 Leads\", \"marketing_objective\": \"LEADS_GENERATION\",\n"
    "  \"branding_text\": \"Acme\", \"spending_limit_model\": \"ENTIRE\", \"spending_limit\": 10000,\n"
    "  \"bid_strategy\": \"TARGET_CPA\", \"cpa_goal\": 15,\n"
    "  \"geo_targeting\": {\"state\": \"EXISTS\", \"value\": [{\"type\": \"INCLUDE\", \"value\": [{\"country\": \"US\"}]}]},\n"
    "  \"my_audiences\": {\"collection\": [{\"type\": \"INCLUDE\", \"collection\": [224820]}]} }"
)


_UPDATE_CAMPAIGN_DESCRIPTION = (
    "Update an existing campaign: scalars and any targeting block in one call.\n"
    "\n"
    f"{_TARGETING_BLOCKS_NOTE}\n"
    "\n"
    "Geo: accepts EITHER `geo_targeting` (advanced/MultiTargeting, full-replace) OR classic dimension fields "
    "(country_targeting, region_targeting, dma_targeting, city_targeting, postal_code_targeting — each replaces only its "
    "dimension). Sending both shapes in one request is rejected. Sending advanced on a classic-storage campaign one-way "
    "migrates it to advanced (logged in campaign history).\n"
    "\n"
    "All amounts are numbers in the account's default currency.\n"
    "\n"
    "Conditional rules (apply only when the gating field is in this request):\n"
    "- spending_limit_model = MONTHLY|ENTIRE → also send spending_limit. NONE → also send daily_cap.\n"
    "- bid_strategy = TARGET_CPA → also send cpa_goal.\n"
    "- If both start_date and end_date sent: end_date >= start_date.\n"
    "- Solo updates of a partner field (e.g. only spending_limit, or only cpa_goal) are allowed — stored gating field is reused.\n"
    "\n"
    "At least one updatable field besides account_id and campaign_id must be sent.\n"
    "\n"
    "Server-side constraints (returns 4xx if violated):\n"
    "- Some marketing_objective transitions are rejected mid-flight.\n"
    "- MOBILE_APP_INSTALL switching requires app fields not exposed here.\n"
    "- TERMINATED campaigns cannot be reactivated.\n"
    "- Lookalike: account must have user-segments edit permission and campaign must allow retargeting.\n"
    "\n"
    "Discovery: same as create_campaign — search_geos, search_techno, list_realize_resource.\n"
    "\n"
    "Read-only — NEVER send: id, advertiser_id, status, approval_state, spent, policy_review, pricing_model, "
    "target_cpa, target_cpa_learning_status.\n"
    "\n"
    "Behind the scenes the MCP fans out: main POST + (optional) my_audiences / lookalike_audience / contextual_segments "
    "sub-resources. Sub-resource failures surface as `partial_failures` in the response; main update is reflected in the "
    "returned composed state.\n"
    "\n"
    "Example — activate paused campaign and add publisher bid modifier:\n"
    "{ \"account_id\": \"acme-inc\", \"campaign_id\": \"c-123\", \"is_active\": true,\n"
    "  \"publisher_bid_modifier\": {\"values\": [{\"target\": \"pub_alpha\", \"cpc_modification\": 1.25}]} }\n"
    "\n"
    "Example — clear audience targeting only (other targeting untouched):\n"
    "{ \"account_id\": \"acme-inc\", \"campaign_id\": \"c-123\", \"my_audiences\": {\"collection\": []} }"
)


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


_CREATE_CAMPAIGN_PROPERTIES = {
    "account_id": {"type": "string", "description": "Value from search_accounts.account_id (NOT numeric)."},
    **_SCALAR_PROPERTIES,
    **_TARGETING_PROPERTIES_COMMON,
}


_UPDATE_CAMPAIGN_PROPERTIES = {
    "account_id": {"type": "string", "description": "Value from search_accounts.account_id (NOT numeric)."},
    "campaign_id": {"type": "string", "description": "Campaign ID."},
    **_SCALAR_PROPERTIES,
    **_TARGETING_PROPERTIES_COMMON,
    **_UPDATE_CLASSIC_GEO_PROPERTIES,
}


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
        "description": (
            "Search for accounts by numeric ID or text query (read-only). Use this first — "
            "every other tool's `account_id` parameter takes the value from the `account_id` field "
            "returned here. Response metadata includes `Total` (full match count across pages). "
            "Keep page_size constant across pages to avoid duplicate or missing results."
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

    "get_account": {
        "description": (
            "Get one account's full record (read-only). Returns the validation context an LLM "
            "needs before constructing a campaign payload: currency (for amount fields), "
            "permission flags (allowGeoTargeting, retargeting, schedule), billing state, account type. "
            "Call after search_accounts to confirm the account allows the targeting/scheduling the user wants."
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
        "handler": "account_handlers.get_account",
        "category": "accounts",
    },

    # Campaign Management Tools (READ-ONLY)
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
                    "description": "Campaign ID."
                }
            },
            "required": ["account_id", "campaign_id"]
        },
        "handler": "campaign_handlers.get_campaign",
        "category": "campaigns"
    },

    "create_campaign": {
        "description": _CREATE_CAMPAIGN_DESCRIPTION,
        "schema": {
            "type": "object",
            "properties": _CREATE_CAMPAIGN_PROPERTIES,
            "required": ["account_id", "name", "marketing_objective", "branding_text", "spending_limit_model"],
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

    # Campaign Items Tools (READ-ONLY)
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
                    "description": "Campaign ID."
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

    "search_geos": {
        "description": (
            "Search geos: list valid country/region/dma/city/postal_code values for create_campaign/update_campaign geo targeting (read-only).\n"
            "\n"
            "dimension=countries (no country_code) returns ISO-2 country codes. "
            "dimension=regions|dma|cities|postal_codes requires country_code (ISO-2, e.g. \"US\"). "
            "DMA is US-only.\n"
            "\n"
            "Use returned values directly in geo_targeting (advanced) vectors, e.g. "
            "{country: \"US\", region: \"CA\"}, or in classic *_targeting blocks on update_campaign.\n"
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
            "Search techno: list valid technology-targeting values for create_campaign/update_campaign "
            "platform_targeting / os_targeting / browser_targeting / connection_type_targeting (read-only).\n"
            "\n"
            "dimension=platforms | operating_systems | browsers | connection_types takes no extra args. "
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
                        "platforms",
                        "operating_systems",
                        "operating_system_versions",
                        "browsers",
                        "connection_types",
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
            "Search audiences: list first-party + custom audiences for an account (read-only). "
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

    "search_publisher_groups": {
        "description": (
            "Search sponsored publisher targeting groups (network-scoped, read-only). "
            "Group names returned here populate `publisher_groups_targeting.value` on "
            "create_campaign / update_campaign. No account_id required — groups are global."
        ),
        "schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
        "handler": "discovery_handlers.search_publisher_groups",
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

    "list_realize_resource": {
        "description": (
            "List valid values for bounded campaign-config enums used by create_campaign/update_campaign "
            "scalar fields and activity_schedule.time_zone (read-only).\n"
            "\n"
            "Supported resources:\n"
            "- marketing_objectives — values for `marketing_objective`.\n"
            "- bid_strategies — values for `bid_strategy`.\n"
            "- spending_limit_models — values for `spending_limit_model`.\n"
            "- time_zones — IANA names for `activity_schedule.time_zone` (CUSTOM mode).\n"
            "\n"
            "For geo and technology vocabularies use search_geos and search_techno respectively.\n"
            "\n"
            "Example: { \"resource\": \"marketing_objectives\" }"
        ),
        "schema": {
            "type": "object",
            "properties": {
                "resource": {
                    "type": "string",
                    "enum": [
                        "marketing_objectives",
                        "bid_strategies",
                        "spending_limit_models",
                        "time_zones",
                    ],
                    "description": "Bounded enum vocabulary to fetch.",
                },
            },
            "required": ["resource"],
        },
        "handler": "resources.list_realize_resource",
        "category": "resources",
    },

    # Reporting Tools (READ-ONLY)

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
