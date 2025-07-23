# Realize MCP Server

A Model Context Protocol (MCP) server that provides read-only access to Taboola's Realize API, enabling AI assistants to analyze campaigns, retrieve performance data, and generate reports through natural language.

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Python-3.10+-green.svg)](https://python.org)
[![MCP](https://img.shields.io/badge/MCP-Compatible-orange.svg)](https://modelcontextprotocol.io/)
[![Latest Version][mdversion-button]][md-pypi]

[mdversion-button]: https://img.shields.io/pypi/v/realize-mcp.svg
[md-pypi]: https://pypi.org/project/realize-mcp/

## Quick Start

### 1. Install

```bash
pip install realize-mcp
```

### 2. Choose Your Authentication Method

**Option A: Browser Authentication** (Recommended - No credentials needed)
- Configure MCP without credentials
- Use the `browser_authenticate` tool when you start

**Option B: API Credentials in MCP Config**
- Add credentials directly to your MCP client configuration
- Best for automated workflows

**Option C: API Credentials via Environment Variables**
- Export credentials as environment variables
- Useful for shared configurations or CI/CD

```bash
export REALIZE_CLIENT_ID="your_client_id"
export REALIZE_CLIENT_SECRET="your_client_secret"
```

### 3. Configure Your MCP Client

**Cursor IDE**

[![Install MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/install-mcp?name=realize-mcp&config=JTdCJTIyY29tbWFuZCUyMiUzQSUyMnJlYWxpemUtbWNwLXNlcnZlciUyMiU3RA%3D%3D)

Add to Cursor Settings → Features → Model Context Protocol:

```json
{
  "mcpServers": {
    "realize-mcp": {
      "command": "realize-mcp-server",
      "env": {
        // For Option B only - add your credentials here
        "REALIZE_CLIENT_ID": "your_client_id",
        "REALIZE_CLIENT_SECRET": "your_client_secret"
      }
    }
  }
}
```

**Claude Desktop**

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "realize-mcp": {
      "command": "realize-mcp-server",
      "env": {
        // For Option B only - add your credentials here
        "REALIZE_CLIENT_ID": "your_client_id",
        "REALIZE_CLIENT_SECRET": "your_client_secret"
      }
    }
  }
}
```

*Note: For Options A & C, omit the `env` section entirely.*

### 4. Start Using

```
User: "Show me campaigns for Marketing Corp"
AI: I'll search for that account and retrieve the campaigns.
```

## Basic Usage

```
User: "Show me campaigns for Marketing Corp"
AI: 
  1. Searches accounts for "Marketing Corp" 
  2. Retrieves campaigns using the found account_id
  3. Returns campaign list with performance metrics
```

**Important**: All operations require getting `account_id` values from `search_accounts` first - never use numeric IDs directly.

## Available Tools

### 🔍 Account Management
- `search_accounts` - **[REQUIRED FIRST]** Find accounts and get account_id values for other tools (with pagination support: page_size max 10)

### 📊 Campaign Tools  
- `get_all_campaigns` - List all campaigns for an account
- `get_campaign` - Get detailed campaign information
- `get_campaign_items` - List campaign creative items
- `get_campaign_item` - Get specific item details

### 📈 Reporting Tools (CSV Format)
- `get_top_campaign_content_report` - Top performing content with sorting & pagination
- `get_campaign_breakdown_report` - Campaign performance breakdown with sorting & pagination  
- `get_campaign_history_report` - Historical campaign data with pagination
- `get_campaign_site_day_breakdown_report` - Site/day performance breakdown with sorting & pagination

### 🔐 Authentication
- `get_auth_token` - Authenticate using client credentials (only available when credentials are configured)
- `browser_authenticate` - Interactive browser authentication via Taboola SSO
- `get_token_details` - Check current authentication token information
- `clear_auth_token` - Clear stored browser authentication token

## Prerequisites

- **Python 3.10+** (Python 3.11+ recommended)
- **MCP-compatible client** (Claude Desktop, Cursor, VS Code, etc.)
- **Taboola Realize API credentials** (optional - can use browser authentication instead)

## Usage Examples

### 1. Find Account and List Campaigns
```
User: "Show campaigns for account 12345"
AI Process:
  Step 1: search_accounts("12345") → Returns account_id: "advertiser_12345_prod"
  Step 2: get_all_campaigns(account_id="advertiser_12345_prod")
  Result: List of campaigns with details
```

### 2. Get Performance Report
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

### 3. Top Performing Content
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

## Important Workflow Notes

### ⚠️ Account ID Requirement

**All campaign and report tools require `account_id` values from `search_accounts`:**

✅ **Correct Workflow:**
```
1. search_accounts("company name" or "numeric_id") 
2. Extract account_id from response
3. Use account_id in other tools
```

❌ **Incorrect:**
```
get_all_campaigns(account_id="12345")  # Numeric IDs won't work
```

### 📊 Report Features

- **CSV Format**: Reports return efficient CSV data with headers and pagination info
- **Pagination**: Default page_size=20, max=100 to prevent overwhelming responses  
- **Sorting**: Available for most reports by `clicks`, `spent`, or `impressions`
- **Size Optimization**: Automatic truncation for large datasets

## Quick Troubleshooting

If you encounter issues with the MCP server, try this quick diagnostic:

```bash
# Test server manually
REALIZE_CLIENT_ID=test REALIZE_CLIENT_SECRET=test realize-mcp-server
```
You should see: `INFO:realize.realize_server:Starting Realize MCP Server...`

## Detailed Documentation

📖 **For comprehensive information, see [design.md](design.md):**

- **Recent Fixes & Version History** - Detailed release notes and upgrade instructions
- **Installation Options** - PyPI & Source installation with troubleshooting  
- **Architecture & Design Principles** - Technical implementation details
- **Advanced Features** - CSV format, pagination, sorting, and optimization
- **Development Guide & Testing** - Setup, testing, and contribution guidelines
- **Comprehensive Troubleshooting** - Detailed solutions for common issues
- **Security Best Practices** - Credential management and operational security
- **Complete API Reference** - Full technical API documentation
- **Technology Stack Details** - Dependencies and system requirements

## License

Licensed under the Apache License 2.0. See [LICENSE](LICENSE) for details.

---

**Realize MCP Server** - Safe, efficient, read-only access to Taboola's advertising platform through natural language. 
