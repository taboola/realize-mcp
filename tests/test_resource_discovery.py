"""Tests for discovery tools: search_geos, search_techno, list_time_zones, list_cta_types."""
import json

import pytest
from unittest.mock import AsyncMock, patch

from realize.realize_server import handle_call_tool
from realize.tools.errors import ToolInputError


def _get_endpoint(mock_get):
    args, kwargs = mock_get.call_args
    return args[0] if args else kwargs.get("endpoint")


class TestSearchGeos:
    @pytest.mark.asyncio
    @patch('realize.tools.resources.client.get', new_callable=AsyncMock)
    async def test_countries_no_country_code(self, mock_get):
        mock_get.return_value = {"results": [{"name": "US", "value": "United States"}]}
        await handle_call_tool("search_geos", {"dimension": "countries"})
        assert _get_endpoint(mock_get) == "/resources/countries"

    @pytest.mark.asyncio
    @patch('realize.tools.resources.client.get', new_callable=AsyncMock)
    async def test_regions_requires_country_code(self, mock_get):
        with pytest.raises(ToolInputError, match="country_code is required"):
            await handle_call_tool("search_geos", {"dimension": "regions"})
        mock_get.assert_not_called()

    @pytest.mark.asyncio
    @patch('realize.tools.resources.client.get', new_callable=AsyncMock)
    async def test_regions_with_country_code(self, mock_get):
        mock_get.return_value = {"results": []}
        await handle_call_tool("search_geos", {"dimension": "regions", "country_code": "US"})
        assert _get_endpoint(mock_get) == "/resources/countries/US/regions"

    @pytest.mark.asyncio
    @patch('realize.tools.resources.client.get', new_callable=AsyncMock)
    async def test_cities_with_country_code(self, mock_get):
        mock_get.return_value = {"results": []}
        await handle_call_tool("search_geos", {"dimension": "cities", "country_code": "US"})
        assert _get_endpoint(mock_get) == "/resources/countries/US/cities"

    @pytest.mark.asyncio
    @patch('realize.tools.resources.client.get', new_callable=AsyncMock)
    async def test_postal_codes_uses_postal_suffix(self, mock_get):
        mock_get.return_value = {"results": []}
        await handle_call_tool("search_geos", {"dimension": "postal_codes", "country_code": "US"})
        assert _get_endpoint(mock_get) == "/resources/countries/US/postal"

    @pytest.mark.asyncio
    async def test_unknown_dimension_rejected(self):
        with pytest.raises(ToolInputError, match="dimension must be one of"):
            await handle_call_tool("search_geos", {"dimension": "platforms"})


class TestSearchTechno:
    @pytest.mark.asyncio
    @patch('realize.tools.resources.client.get', new_callable=AsyncMock)
    async def test_browsers(self, mock_get):
        mock_get.return_value = {"results": []}
        await handle_call_tool("search_techno", {"dimension": "browsers"})
        assert _get_endpoint(mock_get) == "/resources/campaigns_properties/browsers"

    @pytest.mark.asyncio
    @patch('realize.tools.resources.client.get', new_callable=AsyncMock)
    async def test_os_versions_requires_os_family(self, mock_get):
        with pytest.raises(ToolInputError, match="os_family is required"):
            await handle_call_tool("search_techno", {"dimension": "operating_system_versions"})
        mock_get.assert_not_called()

    @pytest.mark.asyncio
    @patch('realize.tools.resources.client.get', new_callable=AsyncMock)
    async def test_os_versions_with_family(self, mock_get):
        mock_get.return_value = {"results": []}
        await handle_call_tool("search_techno", {
            "dimension": "operating_system_versions",
            "os_family": "iOS",
        })
        assert _get_endpoint(mock_get) == "/resources/campaigns_properties/operating_systems/iOS"

    @pytest.mark.asyncio
    async def test_platforms_no_longer_accepted(self):
        with pytest.raises(ToolInputError, match="dimension must be one of"):
            await handle_call_tool("search_techno", {"dimension": "platforms"})

    @pytest.mark.asyncio
    async def test_operating_systems_no_longer_accepted(self):
        with pytest.raises(ToolInputError, match="dimension must be one of"):
            await handle_call_tool("search_techno", {"dimension": "operating_systems"})

    @pytest.mark.asyncio
    async def test_connection_types_no_longer_accepted(self):
        with pytest.raises(ToolInputError, match="dimension must be one of"):
            await handle_call_tool("search_techno", {"dimension": "connection_types"})


class TestListTimeZones:
    @pytest.mark.asyncio
    @patch('realize.tools.resources.client.get', new_callable=AsyncMock)
    async def test_endpoint(self, mock_get):
        mock_get.return_value = {"results": []}
        await handle_call_tool("list_time_zones", {})
        assert _get_endpoint(mock_get) == "/resources/campaigns_properties/activity-scheduler-time-zone"

    @pytest.mark.asyncio
    @patch('realize.tools.resources.client.get', new_callable=AsyncMock)
    async def test_response_shape(self, mock_get):
        mock_get.return_value = {"results": [{"value": "America/New_York"}, {"value": "US/Eastern"}]}
        result = await handle_call_tool("list_time_zones", {})
        payload = json.loads(result[0].text)
        assert payload["resource"] == "time_zones"
        assert payload["values"] == ["America/New_York", "US/Eastern"]


class TestListCtaTypes:
    @pytest.mark.asyncio
    @patch('realize.tools.resources.client.get', new_callable=AsyncMock)
    async def test_endpoint(self, mock_get):
        mock_get.return_value = {"results": []}
        await handle_call_tool("list_cta_types", {})
        assert _get_endpoint(mock_get) == "/resources/campaigns_properties/items_properties/cta"

    @pytest.mark.asyncio
    @patch('realize.tools.resources.client.get', new_callable=AsyncMock)
    async def test_response_shape(self, mock_get):
        mock_get.return_value = {"results": [{"value": "SHOP_NOW"}, {"value": "LEARN_MORE"}]}
        result = await handle_call_tool("list_cta_types", {})
        payload = json.loads(result[0].text)
        assert payload["resource"] == "cta_types"
        assert payload["values"] == ["SHOP_NOW", "LEARN_MORE"]


class TestDiscoverySchemas:
    @pytest.mark.asyncio
    async def test_search_geos_dimension_enum(self):
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        sg = next(t for t in tools if t.name == "search_geos")
        assert set(sg.inputSchema["properties"]["dimension"]["enum"]) == {
            "countries", "regions", "dma", "cities", "postal_codes",
        }

    @pytest.mark.asyncio
    async def test_search_techno_dimension_enum(self):
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        st = next(t for t in tools if t.name == "search_techno")
        assert set(st.inputSchema["properties"]["dimension"]["enum"]) == {
            "operating_system_versions", "browsers",
        }

    @pytest.mark.asyncio
    async def test_list_time_zones_no_required_args(self):
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        lt = next(t for t in tools if t.name == "list_time_zones")
        assert lt.inputSchema["required"] == []

    @pytest.mark.asyncio
    async def test_list_realize_resource_no_longer_registered(self):
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        names = {t.name for t in tools}
        assert "list_realize_resource" not in names
        assert "list_time_zones" in names

    @pytest.mark.asyncio
    async def test_list_cta_types_no_required_args(self):
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        lc = next(t for t in tools if t.name == "list_cta_types")
        assert lc.inputSchema["required"] == []


class TestFlattenedResponseShape:
    @pytest.mark.asyncio
    @patch('realize.tools.resources.client.get', new_callable=AsyncMock)
    async def test_search_geos_returns_dimension_label(self, mock_get):
        mock_get.return_value = {
            "results": [
                {"name": "US", "value": "United States"},
                {"name": "CA", "value": "Canada"},
            ]
        }
        result = await handle_call_tool("search_geos", {"dimension": "countries"})
        payload = json.loads(result[0].text)
        assert payload["dimension"] == "countries"
        assert payload["values"] == [
            {"code": "US", "name": "United States"},
            {"code": "CA", "name": "Canada"},
        ]

    @pytest.mark.asyncio
    @patch('realize.tools.resources.client.get', new_callable=AsyncMock)
    async def test_search_geos_regions_emit_code_and_name(self, mock_get):
        mock_get.return_value = {
            "results": [
                {"name": "CA", "value": "California"},
                {"name": "OR", "value": "Oregon"},
            ]
        }
        result = await handle_call_tool(
            "search_geos", {"dimension": "regions", "country_code": "US"}
        )
        payload = json.loads(result[0].text)
        assert payload["dimension"] == "regions"
        assert payload["values"] == [
            {"code": "CA", "name": "California"},
            {"code": "OR", "name": "Oregon"},
        ]
