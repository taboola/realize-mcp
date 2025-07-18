"""Centralized registry for all MCP tools."""

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
        "description": "Search for accounts by numeric ID or text query to get account_id values needed for other tools (read-only). Returns account data including 'account_id' field (camelCase string) required for campaign and report operations. WORKFLOW: Use this tool FIRST to get account_id values, then use those values with other tools.",
        "schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Account ID (numeric) or search term (text) to find accounts. Use the returned 'account_id' field for other tool operations."
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
        "description": "Get top performing campaign content report in CSV format (read-only). Returns compact CSV data with summary header for maximum efficiency. IMPORTANT: Each call provides complete, actionable data - do NOT retry unless there's an explicit error. Use pagination parameters to get more data if needed. WORKFLOW: 1) search_accounts('company_name') 2) Extract 'account_id' from results 3) Use account_id parameter here. Response includes CSV format with clear headers and pagination info.",
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
        "description": "Get campaign history report in CSV format (read-only). Returns compact CSV data with historical metrics for maximum efficiency. IMPORTANT: Each call provides complete, actionable data - do NOT retry unless there's an explicit error. Use pagination parameters to get more data if needed. WORKFLOW: 1) search_accounts('company_name') 2) Extract 'account_id' from results 3) Use account_id parameter here. Response includes CSV format with clear headers and pagination info.",
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
        "description": "Get campaign breakdown report in CSV format (read-only). Returns compact CSV data with campaign metrics for maximum efficiency. IMPORTANT: Each call provides complete, actionable data - do NOT retry unless there's an explicit error. Use pagination parameters to get more data if needed. WORKFLOW: 1) search_accounts('company_name') 2) Extract 'account_id' from results 3) Use account_id parameter here. Response includes CSV format with clear headers and pagination info.",
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
        "description": "Get campaign site day breakdown report in CSV format (read-only). Returns compact CSV data with site/day metrics for maximum efficiency. IMPORTANT: Each call provides complete, actionable data - do NOT retry unless there's an explicit error. Use pagination parameters to get more data if needed. WORKFLOW: 1) search_accounts('company_name') 2) Extract 'account_id' from results 3) Use account_id parameter here. Response includes CSV format with clear headers and pagination info.",
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
    """Get all registered tools."""
    import copy
    return copy.deepcopy(TOOL_REGISTRY)


def get_tools_by_category(category: str):
    """Get tools filtered by category."""
    import copy
    return {name: copy.deepcopy(tool) for name, tool in TOOL_REGISTRY.items() 
            if tool.get("category") == category}


def get_tool_categories():
    """Get list of all available categories."""
    return list(set(tool.get("category", "uncategorized") 
                   for tool in TOOL_REGISTRY.values())) 