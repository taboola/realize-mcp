"""Dynamic report handlers for Realize MCP server."""
import json
import logging
from typing import List
import httpx
import mcp.types as types
from realize.tools.utils import format_large_response_with_csv_truncation, validate_account_id
from realize.client import client

logger = logging.getLogger(__name__)


USAGE_GUIDE = """
## HOW TO USE THIS DATA WITH get_dynamic_report_data

1. **Pick columns** from the DIMENSIONS and METRICS sections below (copy the exact backtick-wrapped names)
2. **Choose a date_preset** (REQUIRED): LAST_7_DAYS, LAST_30_DAYS, LAST_3_MONTHS, YESTERDAY, TODAY
3. **Add filters** (optional): only fields listed in FILTERABLE FIELDS can be filtered

### Example call:
```json
{
  "account_id": "<same account_id>",
  "columns": [
    "PERFORMANCE_REPORT.CAMPAIGN.CAMPAIGN_NAME",
    "PERFORMANCE_REPORT.METRICS.CLICKS",
    "PERFORMANCE_REPORT.METRICS.SPENT"
  ],
  "date_preset": "LAST_7_DAYS"
}
```

### Key rules:
- Column/filter names MUST be exact fully qualified names (e.g. PERFORMANCE_REPORT.METRICS.CLICKS, NOT "clicks")
- date_preset is REQUIRED - queries without it will fail
- ACCOUNT_ID and DAY filters are auto-injected - do NOT add them
- All filter values MUST be strings (even numbers: "100" not 100)
"""

# Fields auto-injected by the query builder; hide from the AI menu
_SKIP_FIELDS = {"ACCOUNT_ID", "DAY"}


async def get_dynamic_report_settings(arguments: dict = None) -> List[types.TextContent]:
    """Get available dimensions, metrics, filters and options for dynamic reports (read-only)."""
    try:
        account_id = arguments.get("account_id") if arguments else None
        report_type = arguments.get("report_type", "PERFORMANCE") if arguments else "PERFORMANCE"

        # Validate account_id format
        is_valid, error_message = validate_account_id(account_id)
        if not is_valid:
            return [types.TextContent(
                type="text",
                text=error_message
            )]

        # GET /{account_id}/dynamic-reports/metamodel/{report_type}
        endpoint = f"/{account_id}/dynamic-reports/metamodel/{report_type}"
        response = await client.get(endpoint)

        metamodel_menu = _format_metamodel_for_ai(response)
        return [types.TextContent(
            type="text",
            text=f"Dynamic Report Settings - Account: {account_id} | Type: {report_type}\n{USAGE_GUIDE}\n---\n{metamodel_menu}"
        )]

    except Exception as e:
        logger.error(f"Failed to get dynamic report settings: {e}")
        return [types.TextContent(
            type="text",
            text=f"❌ **Error:** Failed to get dynamic report settings: {str(e)}"
        )]


def _extract_numeric_account_id(metamodel: dict) -> str:
    """Extract numeric account ID from metamodel ACCOUNT_ID filter."""
    report = metamodel.get("report", metamodel)
    top_nodes = report.get("nodes", {})
    if isinstance(top_nodes, dict):
        for group in top_nodes.get("values", []):
            child_nodes = group.get("nodes")
            if child_nodes and isinstance(child_nodes, dict):
                for node in child_nodes.get("values", []):
                    if node.get("name") == "PERFORMANCE_REPORT.ACCOUNT.ACCOUNT_ID":
                        filters = node.get("filters")
                        if filters and isinstance(filters, dict):
                            for f in filters.get("values", []):
                                fv = f.get("filter_values", [])
                                if fv:
                                    return str(fv[0])
    return None


def _format_metamodel_for_ai(metamodel: dict) -> str:
    """Transform raw metamodel JSON into a flat, AI-readable markdown menu.

    Walks report.nodes.values -> group -> nodes.values -> individual nodes
    and produces DIMENSIONS, METRICS, and FILTERABLE FIELDS sections.
    Skips auto-injected fields (ACCOUNT_ID, DAY).
    """
    report = metamodel.get("report", metamodel)
    top_nodes = report.get("nodes", {})
    if not isinstance(top_nodes, dict):
        return "(No metamodel data available)"

    groups = top_nodes.get("values", [])
    if not groups:
        return "(No metamodel data available)"

    dimensions = []  # (group_label, name, label, data_type)
    metrics = []     # (group_label, name, label, data_type)
    filterable = []  # (name, label, operators, values)

    for group in groups:
        group_label = group.get("label", group.get("name", ""))
        child_nodes = group.get("nodes")
        if not child_nodes or not isinstance(child_nodes, dict):
            continue
        for node in child_nodes.get("values", []):
            name = node.get("name", "")
            label = node.get("label", "")
            data_type = node.get("data_type", "")
            node_type = node.get("type", "")

            # Skip auto-injected fields
            short_name = name.rsplit(".", 1)[-1] if name else ""
            if short_name in _SKIP_FIELDS:
                # Also skip if mandatory
                filters_section = node.get("filters")
                if filters_section and isinstance(filters_section, dict):
                    for f in filters_section.get("values", []):
                        mc = f.get("mandatory_condition", {})
                        if isinstance(mc, dict) and mc.get("value") == "true":
                            break
                    else:
                        # Not mandatory, but still in skip list (DAY)
                        pass
                continue

            if node_type == "ROW":
                dimensions.append((group_label, name, label, data_type))
            elif node_type == "COLUMN":
                metrics.append((group_label, name, label, data_type))

            # Collect filterable fields
            filters_section = node.get("filters")
            if filters_section and isinstance(filters_section, dict):
                for f in filters_section.get("values", []):
                    operators = f.get("operators", [])
                    values = f.get("filter_values", [])
                    # Skip mandatory filters
                    mc = f.get("mandatory_condition", {})
                    if isinstance(mc, dict) and mc.get("value") == "true":
                        continue
                    filterable.append((name, label, operators, values))

    lines = []

    # DIMENSIONS section
    lines.append("## DIMENSIONS (use in `columns` parameter)")
    current_group = None
    for group_label, name, label, data_type in dimensions:
        if group_label != current_group:
            lines.append(f"### {group_label}")
            current_group = group_label
        lines.append(f"- `{name}` -- {label} ({data_type})")

    lines.append("")

    # METRICS section
    lines.append("## METRICS (use in `columns` parameter)")
    current_group = None
    for group_label, name, label, data_type in metrics:
        if group_label != current_group:
            lines.append(f"### {group_label}")
            current_group = group_label
        lines.append(f"- `{name}` -- {label} ({data_type})")

    # FILTERABLE FIELDS section
    if filterable:
        lines.append("")
        lines.append("## FILTERABLE FIELDS")
        for name, label, operators, values in filterable:
            parts = f"- `{name}` ({label})"
            if operators:
                parts += f" -- operators: {', '.join(operators)}"
            if values:
                parts += f" -- values: [{', '.join(str(v) for v in values)}]"
            lines.append(parts)

    # Summary
    lines.append("")
    lines.append(f"**Total: {len(dimensions)} dimensions, {len(metrics)} metrics, {len(filterable)} filterable fields**")

    return "\n".join(lines)


def _build_query(report_type, columns, date_preset, filters, numeric_account_id):
    """Build the correct nested API query structure.

    The real API uses:
    - columns.values (not columns.columns)
    - filters.values (not filters.filters)
    - filter_operator, filter_values, filter_type (not operator, values)
    - Fully qualified node names (PERFORMANCE_REPORT.CAMPAIGN.CAMPAIGN_NAME)
    - Mandatory ACCOUNT_ID and DAY filters
    """
    query = {
        "report_reference": {
            "report_type": report_type
        },
        "columns": {
            "values": [
                {"node_reference": {"name": col}} for col in columns
            ]
        },
        "filters": {
            "values": [
                # Mandatory date filter
                {
                    "node_reference": {"name": "PERFORMANCE_REPORT.TIME_UNITS.DAY"},
                    "filter_type": "PREDEFINED_FILTER",
                    "filter_operator": "EQUALS",
                    "filter_values": [date_preset]
                },
                # Mandatory account ID filter
                {
                    "node_reference": {"name": "PERFORMANCE_REPORT.ACCOUNT.ACCOUNT_ID"},
                    "filter_type": "PREDEFINED_FILTER",
                    "filter_operator": "EQUALS",
                    "filter_values": [numeric_account_id]
                }
            ]
        }
    }

    # Add user-provided filters
    if filters:
        for f in filters:
            query["filters"]["values"].append({
                "node_reference": {"name": f["name"]},
                "filter_type": "PREDEFINED_FILTER",
                "filter_operator": f["operator"],
                "filter_values": f["values"]
            })

    return query


async def get_dynamic_report_data(arguments: dict = None) -> List[types.TextContent]:
    """Execute a dynamic report query and return results (read-only)."""
    try:
        account_id = arguments.get("account_id") if arguments else None
        columns = arguments.get("columns") if arguments else None
        date_preset = arguments.get("date_preset") if arguments else None
        filters = arguments.get("filters") if arguments else None
        report_type = arguments.get("report_type", "PERFORMANCE") if arguments else "PERFORMANCE"

        # Validate account_id format
        is_valid, error_message = validate_account_id(account_id)
        if not is_valid:
            return [types.TextContent(
                type="text",
                text=error_message
            )]

        if not columns or not isinstance(columns, list) or len(columns) == 0:
            return [types.TextContent(
                type="text",
                text="columns is required - provide a list of fully qualified dimension/metric names from get_dynamic_report_settings (e.g. [\"PERFORMANCE_REPORT.CAMPAIGN.CAMPAIGN_NAME\", \"PERFORMANCE_REPORT.METRICS.CLICKS\"])"
            )]

        if not date_preset or not isinstance(date_preset, str):
            return [types.TextContent(
                type="text",
                text="date_preset is required - use one of: LAST_7_DAYS, LAST_30_DAYS, LAST_3_MONTHS, YESTERDAY, TODAY"
            )]

        # Validate filter structure if provided
        if filters:
            if not isinstance(filters, list):
                return [types.TextContent(
                    type="text",
                    text="filters must be a list of objects with name, operator, and values"
                )]
            for i, f in enumerate(filters):
                if not isinstance(f, dict) or "name" not in f or "operator" not in f or "values" not in f:
                    return [types.TextContent(
                        type="text",
                        text=f"Filter at index {i} is invalid - each filter must have name, operator, and values (e.g. {{\"name\": \"PERFORMANCE_REPORT.CAMPAIGN.CAMPAIGN_STATUS\", \"operator\": \"IN\", \"values\": [\"RUNNING\"]}})"
                    )]

        # Fetch metamodel to get numeric account ID for mandatory ACCOUNT_ID filter
        metamodel = await client.get(f"/{account_id}/dynamic-reports/metamodel/{report_type}")
        numeric_account_id = _extract_numeric_account_id(metamodel)
        if not numeric_account_id:
            return [types.TextContent(
                type="text",
                text="❌ Could not extract numeric account ID from metamodel. Please verify the account_id is valid."
            )]

        # Build the nested API query structure
        query = _build_query(report_type, columns, date_preset, filters, numeric_account_id)

        logger.info(f"Dynamic report query for account {account_id}: {json.dumps(query)}")

        # POST /{account_id}/dynamic-reports/query
        endpoint = f"/{account_id}/dynamic-reports/query"
        response = await client.post(endpoint, data=query)

        return [types.TextContent(
            type="text",
            text=f"📊 **Dynamic Report Data** - Account: {account_id}\n\n{format_large_response_with_csv_truncation(response)}"
        )]

    except httpx.HTTPStatusError as e:
        # Surface the API error response body so we can see what went wrong
        error_body = ""
        try:
            error_body = e.response.text
        except Exception:
            pass
        logger.error(f"Dynamic report API error: {e} | Response: {error_body}")
        query_sent = json.dumps(query, indent=2) if 'query' in dir() else "unknown"
        return [types.TextContent(
            type="text",
            text=f"❌ **API Error {e.response.status_code}** for dynamic report query.\n\n**API Response:** {error_body}\n\n**Query sent:**\n```json\n{query_sent}\n```\nCheck that column names match exactly from get_dynamic_report_settings metamodel. Use fully qualified names like PERFORMANCE_REPORT.METRICS.CLICKS."
        )]

    except Exception as e:
        logger.error(f"Failed to get dynamic report data: {e}")
        return [types.TextContent(
            type="text",
            text=f"❌ **Error:** Failed to get dynamic report data: {str(e)}"
        )]
