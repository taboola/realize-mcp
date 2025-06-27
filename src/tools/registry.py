"""Centralized registry for all MCP tools."""

# Tool Registry - Add new tools here
TOOL_REGISTRY = {
    # Authentication & Token Tools
    "get_auth_token": {
        "description": "Authenticate with Realize API using client credentials",
        "schema": {
            "type": "object",
            "properties": {},
            "required": []
        },
        "handler": "auth_handlers.get_auth_token",
        "category": "authentication"
    },
    
    "get_token_details": {
        "description": "Get details about current authentication token",
        "schema": {
            "type": "object", 
            "properties": {},
            "required": []
        },
        "handler": "auth_handlers.get_token_details",
        "category": "authentication"
    },
    
    # Account Management Tools
    "get_user_allowed_accounts": {
        "description": "Get list of accounts accessible to current user",
        "schema": {
            "type": "object",
            "properties": {},
            "required": []
        },
        "handler": "account_handlers.get_user_allowed_accounts",
        "category": "accounts"
    },
    
    "get_user_account": {
        "description": "Get current user's account information",
        "schema": {
            "type": "object",
            "properties": {},
            "required": []
        },
        "handler": "account_handlers.get_user_account", 
        "category": "accounts"
    },
    
    # Campaign Management Tools (READ-ONLY)
    "get_all_campaigns": {
        "description": "Get all campaigns for an account (read-only)",
        "schema": {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string",
                    "description": "Account ID to get campaigns for"
                }
            },
            "required": ["account_id"]
        },
        "handler": "campaign_handlers.get_all_campaigns",
        "category": "campaigns"
    },

    "get_campaign": {
        "description": "Get specific campaign details (read-only)",
        "schema": {
            "type": "object",
            "properties": {
                "account_id": {
                    "type": "string",
                    "description": "Account ID"
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
        "description": "Get all items for a campaign (read-only)",
        "schema": {
            "type": "object",
            "properties": {
                "account_id": {"type": "string", "description": "Account ID"},
                "campaign_id": {"type": "string", "description": "Campaign ID"}
            },
            "required": ["account_id", "campaign_id"]
        },
        "handler": "campaign_handlers.get_campaign_items",
        "category": "campaign_items"
    },

    "get_campaign_item": {
        "description": "Get specific campaign item details (read-only)",
        "schema": {
            "type": "object",
            "properties": {
                "account_id": {"type": "string", "description": "Account ID"},
                "campaign_id": {"type": "string", "description": "Campaign ID"},
                "item_id": {"type": "string", "description": "Item ID to get details for"}
            },
            "required": ["account_id", "campaign_id", "item_id"]
        },
        "handler": "campaign_handlers.get_campaign_item",
        "category": "campaign_items"
    },

    # Reporting Tools (READ-ONLY)

    "get_top_campaign_content_report": {
        "description": "Get top performing campaign content report (read-only)",
        "schema": {
            "type": "object",
            "properties": {
                "account_id": {"type": "string", "description": "Account ID"},
                "start_date": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                "end_date": {"type": "string", "description": "End date (YYYY-MM-DD)"},
                "count": {"type": "integer", "description": "Number of top items to return", "default": 10}
            },
            "required": ["account_id", "start_date", "end_date"]
        },
        "handler": "report_handlers.get_top_campaign_content_report",
        "category": "reports"
    },

    "get_campaign_history_report": {
        "description": "Get campaign history report (read-only)",
        "schema": {
            "type": "object",
            "properties": {
                "account_id": {"type": "string", "description": "Account ID"},
                "start_date": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                "end_date": {"type": "string", "description": "End date (YYYY-MM-DD)"}
            },
            "required": ["account_id", "start_date", "end_date"]
        },
        "handler": "report_handlers.get_campaign_history_report",
        "category": "reports"
    },

    "get_campaign_breakdown_report": {
        "description": "Get campaign breakdown report with hardcoded dimension (read-only)",
        "schema": {
            "type": "object",
            "properties": {
                "account_id": {"type": "string", "description": "Account ID"},
                "start_date": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                "end_date": {"type": "string", "description": "End date (YYYY-MM-DD)"},
                "filters": {
                    "type": "object", 
                    "description": "Optional filters (flexible JSON object)",
                    "additionalProperties": {"type": "string"}
                }
            },
            "required": ["account_id", "start_date", "end_date"]
        },
        "handler": "report_handlers.get_campaign_breakdown_report",
        "category": "reports"
    },

    "get_campaign_site_day_breakdown_report": {
        "description": "Get campaign site day breakdown report with hardcoded dimension (read-only)",
        "schema": {
            "type": "object",
            "properties": {
                "account_id": {"type": "string", "description": "Account ID"},
                "start_date": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                "end_date": {"type": "string", "description": "End date (YYYY-MM-DD)"},
                "filters": {
                    "type": "object", 
                    "description": "Optional filters (flexible JSON object)",
                    "additionalProperties": {"type": "string"}
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
    return TOOL_REGISTRY


def get_tools_by_category(category: str):
    """Get tools filtered by category."""
    return {name: tool for name, tool in TOOL_REGISTRY.items() 
            if tool.get("category") == category}


def get_tool_categories():
    """Get list of all available categories."""
    return list(set(tool.get("category", "uncategorized") 
                   for tool in TOOL_REGISTRY.values())) 