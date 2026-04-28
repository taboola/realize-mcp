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
            "All amounts (spending_limit, daily_cap, cpc, target_cpa, cpc_cap) are numbers in the account's default currency. Do not include a currency symbol or code.\n"
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
            "    -> set cpc (number). bid_strategy (string enum) optional (SMART default, or FIXED). Omit target_cpa.\n"
            "- LEADS_GENERATION | ONLINE_PURCHASES | MOBILE_APP_INSTALL\n"
            "    -> set bid_strategy (string enum) = TARGET_CPA | MAX_CONVERSIONS | MAX_VALUE.\n"
            "       If bid_strategy = TARGET_CPA, set target_cpa (number). Omit cpc.\n"
            "\n"
            "Optional scalars: start_date (string, YYYY-MM-DD), end_date (string, YYYY-MM-DD), tracking_code (string), cpc_cap (number), comments (string). If both dates set: end_date >= start_date.\n"
            "\n"
            "Read-only - NEVER send: id, advertiser_id, status, approval_state, is_active, spent, policy_review.\n"
            "\n"
            "Not supported here: targeting, audiences, conversion_rules, schedule. After creation, use update tools (forthcoming) to add these.\n"
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
            "  \"bid_strategy\": \"TARGET_CPA\", \"target_cpa\": 15 }"
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
                "target_cpa": {"type": "number", "description": "Target cost per acquisition in account's default currency (e.g. 15). Required when bid_strategy=TARGET_CPA."},
                "start_date": {"type": "string", "description": "YYYY-MM-DD. Optional; defaults to immediate."},
                "end_date": {"type": "string", "description": "YYYY-MM-DD. Optional; omit for ongoing."},
                "tracking_code": {"type": "string", "description": "Query string appended to item URLs."},
                "cpc_cap": {"type": "number", "description": "Upper bound on bids in account's default currency (e.g. 1.50)."},
                "comments": {"type": "string", "description": "Internal notes."}
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