"""Tests for dynamic report handlers."""
import pytest
import sys
import pathlib
sys.path.append(str(pathlib.Path(__file__).parent.parent / "src"))
from unittest.mock import patch, AsyncMock
import httpx
from realize.tools.dynamic_report_handlers import (
    get_dynamic_report_settings, get_dynamic_report_data,
    _build_query, _extract_numeric_account_id, _format_metamodel_for_ai,
)
from realize.realize_server import handle_call_tool
from realize.tools.registry import get_all_tools


MOCK_METAMODEL = {
    "report": {
        "id": 101,
        "name": "PERFORMANCE_REPORT",
        "version": "1",
        "nodes": {
            "values": [
                {
                    "name": "PERFORMANCE_REPORT.ACCOUNT",
                    "type": "GROUP",
                    "label": "Account",
                    "nodes": {
                        "values": [
                            {
                                "name": "PERFORMANCE_REPORT.ACCOUNT.ACCOUNT_ID",
                                "type": "ROW",
                                "label": "Account ID",
                                "data_type": "NUMERIC",
                                "filters": {
                                    "values": [{
                                        "type": "PREDEFINED_FILTER",
                                        "operators": ["EQUALS"],
                                        "filter_values": ["1065940"],
                                        "mandatory_condition": {"value": "true"}
                                    }]
                                },
                                "nodes": None
                            }
                        ]
                    }
                },
                {
                    "name": "PERFORMANCE_REPORT.CAMPAIGN",
                    "type": "GROUP",
                    "label": "Campaign",
                    "nodes": {
                        "values": [
                            {
                                "name": "PERFORMANCE_REPORT.CAMPAIGN.CAMPAIGN_NAME",
                                "type": "ROW",
                                "label": "Campaign Name",
                                "data_type": "STRING",
                                "nodes": None
                            }
                        ]
                    }
                },
                {
                    "name": "PERFORMANCE_REPORT.METRICS",
                    "type": "GROUP",
                    "label": "Metrics",
                    "nodes": {
                        "values": [
                            {
                                "name": "PERFORMANCE_REPORT.METRICS.CLICKS",
                                "type": "COLUMN",
                                "label": "Clicks",
                                "data_type": "NUMERIC",
                                "nodes": None
                            },
                            {
                                "name": "PERFORMANCE_REPORT.METRICS.SPENT",
                                "type": "COLUMN",
                                "label": "Spent",
                                "data_type": "MONEY",
                                "nodes": None
                            }
                        ]
                    }
                }
            ]
        }
    }
}


class TestDynamicReportSettings:
    """Test get_dynamic_report_settings handler."""

    @pytest.mark.asyncio
    @patch('realize.tools.dynamic_report_handlers.client.get', new_callable=AsyncMock)
    async def test_settings_success(self, mock_get):
        """Test successful settings retrieval with formatted metamodel menu."""
        mock_get.return_value = MOCK_METAMODEL

        result = await get_dynamic_report_settings({"account_id": "test_account"})
        assert len(result) == 1
        text = result[0].text
        assert "Dynamic Report Settings" in text
        assert "test_account" in text
        assert "PERFORMANCE" in text
        # Verify usage guide is included
        assert "HOW TO USE THIS DATA" in text
        assert "get_dynamic_report_data" in text
        assert "LAST_7_DAYS" in text
        # Verify formatted metamodel sections are present
        assert "DIMENSIONS" in text
        assert "METRICS" in text
        assert "PERFORMANCE_REPORT.CAMPAIGN.CAMPAIGN_NAME" in text
        assert "PERFORMANCE_REPORT.METRICS.CLICKS" in text
        # ACCOUNT_ID metamodel node should be excluded (auto-injected)
        assert "PERFORMANCE_REPORT.ACCOUNT.ACCOUNT_ID" not in text
        mock_get.assert_called_once_with(f"/test_account/dynamic-reports/metamodel/PERFORMANCE")

    @pytest.mark.asyncio
    @patch('realize.tools.dynamic_report_handlers.client.get', new_callable=AsyncMock)
    async def test_settings_custom_report_type(self, mock_get):
        """Test settings with custom report type."""
        mock_get.return_value = MOCK_METAMODEL

        result = await get_dynamic_report_settings({
            "account_id": "test_account",
            "report_type": "CUSTOM_TYPE"
        })
        assert len(result) == 1
        assert "CUSTOM_TYPE" in result[0].text
        mock_get.assert_called_once_with(f"/test_account/dynamic-reports/metamodel/CUSTOM_TYPE")

    @pytest.mark.asyncio
    async def test_settings_missing_account_id(self):
        """Test settings with missing account_id."""
        result = await get_dynamic_report_settings({})
        assert len(result) == 1
        assert "account_id is required" in result[0].text

    @pytest.mark.asyncio
    async def test_settings_numeric_account_id(self):
        """Test settings with numeric account_id triggers validation error."""
        result = await get_dynamic_report_settings({"account_id": "12345"})
        assert len(result) == 1
        assert "numeric account ID" in result[0].text
        assert "search_accounts" in result[0].text

    @pytest.mark.asyncio
    @patch('realize.tools.dynamic_report_handlers.client.get', new_callable=AsyncMock)
    async def test_settings_api_error(self, mock_get):
        """Test settings with API error."""
        mock_get.side_effect = Exception("API connection failed")

        result = await get_dynamic_report_settings({"account_id": "test_account"})
        assert len(result) == 1
        assert "Error" in result[0].text
        assert "API connection failed" in result[0].text


class TestExtractNumericAccountId:
    """Test the _extract_numeric_account_id helper."""

    def test_extracts_from_valid_metamodel(self):
        """Test extraction from a valid metamodel structure."""
        result = _extract_numeric_account_id(MOCK_METAMODEL)
        assert result == "1065940"

    def test_returns_none_for_empty_metamodel(self):
        """Test returns None for empty metamodel."""
        result = _extract_numeric_account_id({})
        assert result is None

    def test_returns_none_for_missing_account_node(self):
        """Test returns None when ACCOUNT_ID node is missing."""
        metamodel = {"report": {"nodes": {"values": []}}}
        result = _extract_numeric_account_id(metamodel)
        assert result is None


class TestBuildQuery:
    """Test the _build_query helper that constructs the nested API structure."""

    def test_build_query_basic(self):
        """Test basic query with columns and date preset."""
        query = _build_query(
            "PERFORMANCE",
            ["PERFORMANCE_REPORT.CAMPAIGN.CAMPAIGN_NAME", "PERFORMANCE_REPORT.METRICS.CLICKS"],
            "LAST_7_DAYS",
            None,
            "1065940"
        )
        assert query["report_reference"] == {"report_type": "PERFORMANCE"}
        assert len(query["columns"]["values"]) == 2
        assert query["columns"]["values"][0] == {"node_reference": {"name": "PERFORMANCE_REPORT.CAMPAIGN.CAMPAIGN_NAME"}}
        assert query["columns"]["values"][1] == {"node_reference": {"name": "PERFORMANCE_REPORT.METRICS.CLICKS"}}
        # Should have 2 mandatory filters (DAY + ACCOUNT_ID)
        assert len(query["filters"]["values"]) == 2
        day_filter = query["filters"]["values"][0]
        assert day_filter["node_reference"] == {"name": "PERFORMANCE_REPORT.TIME_UNITS.DAY"}
        assert day_filter["filter_type"] == "PREDEFINED_FILTER"
        assert day_filter["filter_operator"] == "EQUALS"
        assert day_filter["filter_values"] == ["LAST_7_DAYS"]
        account_filter = query["filters"]["values"][1]
        assert account_filter["node_reference"] == {"name": "PERFORMANCE_REPORT.ACCOUNT.ACCOUNT_ID"}
        assert account_filter["filter_values"] == ["1065940"]

    def test_build_query_with_extra_filters(self):
        """Test query with additional user-provided filters."""
        filters = [
            {"name": "PERFORMANCE_REPORT.CAMPAIGN.CAMPAIGN_STATUS", "operator": "IN", "values": ["RUNNING"]},
            {"name": "PERFORMANCE_REPORT.METRICS.SPENT", "operator": "GREATER_THAN", "values": ["100"]}
        ]
        query = _build_query(
            "PERFORMANCE",
            ["PERFORMANCE_REPORT.CAMPAIGN.CAMPAIGN_NAME"],
            "LAST_30_DAYS",
            filters,
            "1065940"
        )
        # 2 mandatory + 2 user filters = 4
        assert len(query["filters"]["values"]) == 4
        status_filter = query["filters"]["values"][2]
        assert status_filter["node_reference"] == {"name": "PERFORMANCE_REPORT.CAMPAIGN.CAMPAIGN_STATUS"}
        assert status_filter["filter_operator"] == "IN"
        assert status_filter["filter_values"] == ["RUNNING"]
        assert status_filter["filter_type"] == "PREDEFINED_FILTER"

    def test_build_query_no_extra_filters(self):
        """Test that query always has mandatory filters even with no user filters."""
        query = _build_query("PERFORMANCE", ["PERFORMANCE_REPORT.METRICS.CLICKS"], "TODAY", None, "999")
        assert len(query["filters"]["values"]) == 2
        query2 = _build_query("PERFORMANCE", ["PERFORMANCE_REPORT.METRICS.CLICKS"], "TODAY", [], "999")
        assert len(query2["filters"]["values"]) == 2

    def test_build_query_uses_values_not_columns(self):
        """Test that the query uses 'values' key (not 'columns') inside columns object."""
        query = _build_query("PERFORMANCE", ["PERFORMANCE_REPORT.METRICS.CLICKS"], "LAST_7_DAYS", None, "999")
        assert "values" in query["columns"]
        assert "columns" not in query["columns"]
        assert "values" in query["filters"]
        assert "filters" not in query["filters"]


class TestDynamicReportData:
    """Test get_dynamic_report_data handler."""

    @pytest.mark.asyncio
    @patch('realize.tools.dynamic_report_handlers.client.post', new_callable=AsyncMock)
    @patch('realize.tools.dynamic_report_handlers.client.get', new_callable=AsyncMock)
    async def test_data_success(self, mock_get, mock_post):
        """Test successful data query."""
        mock_get.return_value = MOCK_METAMODEL
        mock_post.return_value = {
            "results": [
                {"data_columns": [
                    {"id": "campaign_name", "value": "Test Campaign"},
                    {"id": "clicks", "value": "1,000"},
                    {"id": "spent", "value": "$50.00"}
                ]}
            ],
            "metadata": {"total": 1}
        }

        result = await get_dynamic_report_data({
            "account_id": "test_account",
            "columns": [
                "PERFORMANCE_REPORT.CAMPAIGN.CAMPAIGN_NAME",
                "PERFORMANCE_REPORT.METRICS.CLICKS",
                "PERFORMANCE_REPORT.METRICS.SPENT",
            ],
            "date_preset": "LAST_7_DAYS"
        })
        assert len(result) == 1
        assert "Dynamic Report Data" in result[0].text
        assert "Test Campaign" in result[0].text

        # Verify the correct nested structure was built
        call_args = mock_post.call_args
        assert call_args[0][0] == "/test_account/dynamic-reports/query"
        sent_query = call_args[1]["data"]
        assert sent_query["report_reference"] == {"report_type": "PERFORMANCE"}
        assert len(sent_query["columns"]["values"]) == 3
        assert sent_query["columns"]["values"][0] == {"node_reference": {"name": "PERFORMANCE_REPORT.CAMPAIGN.CAMPAIGN_NAME"}}
        # Verify mandatory filters
        filter_names = [f["node_reference"]["name"] for f in sent_query["filters"]["values"]]
        assert "PERFORMANCE_REPORT.TIME_UNITS.DAY" in filter_names
        assert "PERFORMANCE_REPORT.ACCOUNT.ACCOUNT_ID" in filter_names

    @pytest.mark.asyncio
    @patch('realize.tools.dynamic_report_handlers.client.post', new_callable=AsyncMock)
    @patch('realize.tools.dynamic_report_handlers.client.get', new_callable=AsyncMock)
    async def test_data_with_extra_filters(self, mock_get, mock_post):
        """Test data query with additional user filters."""
        mock_get.return_value = MOCK_METAMODEL
        mock_post.return_value = {"results": [{"data_columns": [{"id": "clicks", "value": "50"}]}], "metadata": {"total": 1}}

        result = await get_dynamic_report_data({
            "account_id": "test_account",
            "columns": ["PERFORMANCE_REPORT.METRICS.CLICKS"],
            "date_preset": "LAST_7_DAYS",
            "filters": [
                {"name": "PERFORMANCE_REPORT.CAMPAIGN.CAMPAIGN_STATUS", "operator": "IN", "values": ["RUNNING"]}
            ]
        })
        assert len(result) == 1
        assert "Dynamic Report Data" in result[0].text

        sent_query = mock_post.call_args[1]["data"]
        assert len(sent_query["filters"]["values"]) == 3  # DAY + ACCOUNT_ID + user filter
        status_filter = sent_query["filters"]["values"][2]
        assert status_filter["node_reference"] == {"name": "PERFORMANCE_REPORT.CAMPAIGN.CAMPAIGN_STATUS"}
        assert status_filter["filter_operator"] == "IN"

    @pytest.mark.asyncio
    async def test_data_missing_account_id(self):
        """Test data query with missing account_id."""
        result = await get_dynamic_report_data({"columns": ["PERFORMANCE_REPORT.METRICS.CLICKS"], "date_preset": "LAST_7_DAYS"})
        assert len(result) == 1
        assert "account_id is required" in result[0].text

    @pytest.mark.asyncio
    async def test_data_missing_columns(self):
        """Test data query with missing columns."""
        result = await get_dynamic_report_data({"account_id": "test_account", "date_preset": "LAST_7_DAYS"})
        assert len(result) == 1
        assert "columns is required" in result[0].text

    @pytest.mark.asyncio
    async def test_data_empty_columns(self):
        """Test data query with empty columns list."""
        result = await get_dynamic_report_data({"account_id": "test_account", "columns": [], "date_preset": "LAST_7_DAYS"})
        assert len(result) == 1
        assert "columns is required" in result[0].text

    @pytest.mark.asyncio
    async def test_data_missing_date_preset(self):
        """Test data query with missing date_preset."""
        result = await get_dynamic_report_data({
            "account_id": "test_account",
            "columns": ["PERFORMANCE_REPORT.METRICS.CLICKS"]
        })
        assert len(result) == 1
        assert "date_preset is required" in result[0].text

    @pytest.mark.asyncio
    async def test_data_invalid_filter_structure(self):
        """Test data query with invalid filter (missing required keys)."""
        result = await get_dynamic_report_data({
            "account_id": "test_account",
            "columns": ["PERFORMANCE_REPORT.METRICS.CLICKS"],
            "date_preset": "LAST_7_DAYS",
            "filters": [{"name": "PERFORMANCE_REPORT.CAMPAIGN.CAMPAIGN_STATUS"}]  # missing operator and values
        })
        assert len(result) == 1
        assert "invalid" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_data_numeric_account_id(self):
        """Test data query with numeric account_id triggers validation error."""
        result = await get_dynamic_report_data({
            "account_id": "12345",
            "columns": ["PERFORMANCE_REPORT.METRICS.CLICKS"],
            "date_preset": "LAST_7_DAYS"
        })
        assert len(result) == 1
        assert "numeric account ID" in result[0].text

    @pytest.mark.asyncio
    @patch('realize.tools.dynamic_report_handlers.client.post', new_callable=AsyncMock)
    @patch('realize.tools.dynamic_report_handlers.client.get', new_callable=AsyncMock)
    async def test_data_api_error(self, mock_get, mock_post):
        """Test data query with generic error."""
        mock_get.return_value = MOCK_METAMODEL
        mock_post.side_effect = Exception("Server error")

        result = await get_dynamic_report_data({
            "account_id": "test_account",
            "columns": ["PERFORMANCE_REPORT.METRICS.CLICKS"],
            "date_preset": "LAST_7_DAYS"
        })
        assert len(result) == 1
        assert "Error" in result[0].text
        assert "Server error" in result[0].text

    @pytest.mark.asyncio
    @patch('realize.tools.dynamic_report_handlers.client.post', new_callable=AsyncMock)
    @patch('realize.tools.dynamic_report_handlers.client.get', new_callable=AsyncMock)
    async def test_data_http_400_shows_response_body(self, mock_get, mock_post):
        """Test that HTTP 400 errors surface the API response body and query sent."""
        mock_get.return_value = MOCK_METAMODEL
        mock_response = httpx.Response(
            status_code=400,
            request=httpx.Request("POST", "https://example.com/query"),
            text='{"error": "Invalid column: fake_column"}'
        )
        mock_post.side_effect = httpx.HTTPStatusError(
            "Bad Request", request=mock_response.request, response=mock_response
        )

        result = await get_dynamic_report_data({
            "account_id": "test_account",
            "columns": ["fake_column"],
            "date_preset": "LAST_7_DAYS"
        })
        assert len(result) == 1
        assert "API Error 400" in result[0].text
        assert "Invalid column" in result[0].text
        assert "Query sent" in result[0].text
        assert "fake_column" in result[0].text

    @pytest.mark.asyncio
    @patch('realize.tools.dynamic_report_handlers.client.get', new_callable=AsyncMock)
    async def test_data_metamodel_missing_account_id(self, mock_get):
        """Test handling when metamodel doesn't contain numeric account ID."""
        mock_get.return_value = {"report": {"nodes": {"values": []}}}

        result = await get_dynamic_report_data({
            "account_id": "test_account",
            "columns": ["PERFORMANCE_REPORT.METRICS.CLICKS"],
            "date_preset": "LAST_7_DAYS"
        })
        assert len(result) == 1
        assert "numeric account ID" in result[0].text


class TestDynamicReportIntegration:
    """Test dynamic report tools via handle_call_tool dispatch."""

    @pytest.mark.asyncio
    @patch('realize.tools.dynamic_report_handlers.client.get', new_callable=AsyncMock)
    async def test_settings_via_dispatch(self, mock_get):
        """Test get_dynamic_report_settings via handle_call_tool."""
        mock_get.return_value = MOCK_METAMODEL

        result = await handle_call_tool("get_dynamic_report_settings", {
            "account_id": "test_account"
        })
        assert len(result) == 1
        assert "Dynamic Report Settings" in result[0].text

    @pytest.mark.asyncio
    @patch('realize.tools.dynamic_report_handlers.client.post', new_callable=AsyncMock)
    @patch('realize.tools.dynamic_report_handlers.client.get', new_callable=AsyncMock)
    async def test_data_via_dispatch(self, mock_get, mock_post):
        """Test get_dynamic_report_data via handle_call_tool."""
        mock_get.return_value = MOCK_METAMODEL
        mock_post.return_value = {
            "results": [{"data_columns": [{"id": "clicks", "value": "500"}]}],
            "metadata": {"total": 1}
        }

        result = await handle_call_tool("get_dynamic_report_data", {
            "account_id": "test_account",
            "columns": ["PERFORMANCE_REPORT.CAMPAIGN.CAMPAIGN_NAME", "PERFORMANCE_REPORT.METRICS.CLICKS"],
            "date_preset": "LAST_7_DAYS"
        })
        assert len(result) == 1
        assert "Dynamic Report Data" in result[0].text

    @pytest.mark.asyncio
    async def test_settings_validation_via_dispatch(self):
        """Test validation errors via dispatch."""
        result = await handle_call_tool("get_dynamic_report_settings", {})
        assert len(result) == 1
        assert "account_id is required" in result[0].text

    @pytest.mark.asyncio
    async def test_data_validation_via_dispatch(self):
        """Test data validation errors via dispatch."""
        result = await handle_call_tool("get_dynamic_report_data", {
            "account_id": "test_account"
        })
        assert len(result) == 1
        assert "columns is required" in result[0].text


class TestDynamicReportRegistration:
    """Verify both tools are registered with correct schemas."""

    def test_tools_registered(self):
        """Test both dynamic report tools are in registry."""
        tools = get_all_tools()
        assert "get_dynamic_report_settings" in tools
        assert "get_dynamic_report_data" in tools

    def test_total_tool_count(self):
        """Test total tool count is 13 (11 existing + 2 new)."""
        tools = get_all_tools()
        assert len(tools) == 13

    def test_settings_schema(self):
        """Test settings tool schema structure."""
        tools = get_all_tools()
        settings = tools["get_dynamic_report_settings"]

        assert settings["category"] == "dynamic_reports"
        assert "read-only" in settings["description"].lower()
        assert settings["schema"]["required"] == ["account_id"]
        assert "account_id" in settings["schema"]["properties"]
        assert "report_type" in settings["schema"]["properties"]

    def test_data_schema(self):
        """Test data tool schema structure."""
        tools = get_all_tools()
        data = tools["get_dynamic_report_data"]

        assert data["category"] == "dynamic_reports"
        assert "read-only" in data["description"].lower()
        assert "account_id" in data["schema"]["required"]
        assert "columns" in data["schema"]["required"]
        assert "date_preset" in data["schema"]["required"]
        assert "account_id" in data["schema"]["properties"]
        assert "columns" in data["schema"]["properties"]
        assert "date_preset" in data["schema"]["properties"]

    def test_dynamic_reports_category_exists(self):
        """Test dynamic_reports category has exactly 2 tools."""
        from realize.tools.registry import get_tools_by_category, get_tool_categories
        categories = get_tool_categories()
        assert "dynamic_reports" in categories

        dr_tools = get_tools_by_category("dynamic_reports")
        assert len(dr_tools) == 2

    def test_total_categories(self):
        """Test total category count is 6."""
        from realize.tools.registry import get_tool_categories
        categories = get_tool_categories()
        assert len(categories) == 6


class TestFormatMetamodelForAI:
    """Test the _format_metamodel_for_ai helper."""

    def test_basic_formatting(self):
        """Test that output has DIMENSIONS, METRICS sections with correct field names."""
        result = _format_metamodel_for_ai(MOCK_METAMODEL)
        assert "## DIMENSIONS" in result
        assert "## METRICS" in result
        assert "PERFORMANCE_REPORT.CAMPAIGN.CAMPAIGN_NAME" in result
        assert "PERFORMANCE_REPORT.METRICS.CLICKS" in result
        assert "PERFORMANCE_REPORT.METRICS.SPENT" in result

    def test_account_id_excluded(self):
        """Test that mandatory ACCOUNT_ID field is hidden from the menu."""
        result = _format_metamodel_for_ai(MOCK_METAMODEL)
        assert "ACCOUNT_ID" not in result

    def test_group_labels_present(self):
        """Test that GROUP labels appear as section headers."""
        result = _format_metamodel_for_ai(MOCK_METAMODEL)
        assert "### Campaign" in result
        assert "### Metrics" in result

    def test_empty_metamodel(self):
        """Test graceful handling of empty metamodel."""
        result = _format_metamodel_for_ai({})
        assert "No metamodel data available" in result

    def test_no_nodes(self):
        """Test graceful handling of metamodel with empty nodes."""
        result = _format_metamodel_for_ai({"report": {"nodes": {"values": []}}})
        assert "No metamodel data available" in result

    def test_filterable_fields_section(self):
        """Test that filterable fields with operators and values are shown."""
        metamodel_with_filters = {
            "report": {
                "nodes": {
                    "values": [
                        {
                            "name": "REPORT.CAMPAIGN",
                            "type": "GROUP",
                            "label": "Campaign",
                            "nodes": {
                                "values": [
                                    {
                                        "name": "REPORT.CAMPAIGN.STATUS",
                                        "type": "ROW",
                                        "label": "Campaign Status",
                                        "data_type": "STRING",
                                        "filters": {
                                            "values": [{
                                                "operators": ["IN", "EQUALS"],
                                                "filter_values": ["RUNNING", "PAUSED", "STOPPED"]
                                            }]
                                        }
                                    }
                                ]
                            }
                        }
                    ]
                }
            }
        }
        result = _format_metamodel_for_ai(metamodel_with_filters)
        assert "## FILTERABLE FIELDS" in result
        assert "REPORT.CAMPAIGN.STATUS" in result
        assert "IN" in result
        assert "EQUALS" in result
        assert "RUNNING" in result

    def test_summary_counts(self):
        """Test that summary line shows correct dimension and metric counts."""
        result = _format_metamodel_for_ai(MOCK_METAMODEL)
        # MOCK_METAMODEL has 1 dimension (CAMPAIGN_NAME) and 2 metrics (CLICKS, SPENT)
        # ACCOUNT_ID is skipped
        assert "1 dimensions" in result
        assert "2 metrics" in result

    def test_backtick_wrapped_names(self):
        """Test that field names are wrapped in backticks for copy-paste."""
        result = _format_metamodel_for_ai(MOCK_METAMODEL)
        assert "`PERFORMANCE_REPORT.CAMPAIGN.CAMPAIGN_NAME`" in result
        assert "`PERFORMANCE_REPORT.METRICS.CLICKS`" in result
        assert "`PERFORMANCE_REPORT.METRICS.SPENT`" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
