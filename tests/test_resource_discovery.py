"""Tests for the three discovery tools: search_geos, search_techno, list_realize_resource."""
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
        mock_get.return_value = {"results": [{"value": {"code": "US"}}]}
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
    async def test_platforms(self, mock_get):
        mock_get.return_value = {"results": []}
        await handle_call_tool("search_techno", {"dimension": "platforms"})
        assert _get_endpoint(mock_get) == "/resources/platforms"

    @pytest.mark.asyncio
    @patch('realize.tools.resources.client.get', new_callable=AsyncMock)
    async def test_operating_systems(self, mock_get):
        mock_get.return_value = {"results": []}
        await handle_call_tool("search_techno", {"dimension": "operating_systems"})
        assert _get_endpoint(mock_get) == "/resources/campaigns_properties/operating_systems"

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
    async def test_unknown_dimension_rejected(self):
        with pytest.raises(ToolInputError, match="dimension must be one of"):
            await handle_call_tool("search_techno", {"dimension": "countries"})


class TestListRealizeResource:
    @pytest.mark.asyncio
    @patch('realize.tools.resources.client.get', new_callable=AsyncMock)
    async def test_marketing_objectives(self, mock_get):
        mock_get.return_value = {"results": []}
        await handle_call_tool("list_realize_resource", {"resource": "marketing_objectives"})
        assert _get_endpoint(mock_get) == "/resources/campaigns_properties/marketing_objective"

    @pytest.mark.asyncio
    @patch('realize.tools.resources.client.get', new_callable=AsyncMock)
    async def test_time_zones(self, mock_get):
        mock_get.return_value = {"results": []}
        await handle_call_tool("list_realize_resource", {"resource": "time_zones"})
        assert _get_endpoint(mock_get) == "/resources/campaigns_properties/activity-scheduler-time-zone"

    @pytest.mark.asyncio
    async def test_geo_resource_no_longer_accepted(self):
        # Geo resources moved to search_geos.
        with pytest.raises(ToolInputError, match="resource must be one of"):
            await handle_call_tool("list_realize_resource", {"resource": "countries"})

    @pytest.mark.asyncio
    async def test_techno_resource_no_longer_accepted(self):
        # Techno resources moved to search_techno.
        with pytest.raises(ToolInputError, match="resource must be one of"):
            await handle_call_tool("list_realize_resource", {"resource": "platforms"})


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
            "platforms", "operating_systems", "operating_system_versions", "browsers", "connection_types",
        }

    @pytest.mark.asyncio
    async def test_list_realize_resource_resource_enum(self):
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        lr = next(t for t in tools if t.name == "list_realize_resource")
        assert set(lr.inputSchema["properties"]["resource"]["enum"]) == {
            "marketing_objectives", "bid_strategies", "spending_limit_models", "time_zones",
        }


class TestFlattenedResponseShape:
    @pytest.mark.asyncio
    @patch('realize.tools.resources.client.get', new_callable=AsyncMock)
    async def test_search_geos_returns_dimension_label(self, mock_get):
        mock_get.return_value = {"results": [{"value": {"code": "US"}}, {"value": {"code": "CA"}}]}
        result = await handle_call_tool("search_geos", {"dimension": "countries"})
        payload = json.loads(result[0].text)
        assert payload["dimension"] == "countries"
        assert payload["values"] == [{"code": "US"}, {"code": "CA"}]

    @pytest.mark.asyncio
    @patch('realize.tools.resources.client.get', new_callable=AsyncMock)
    async def test_list_realize_resource_returns_resource_label(self, mock_get):
        mock_get.return_value = {"results": [{"value": "BRAND_AWARENESS"}]}
        result = await handle_call_tool("list_realize_resource", {"resource": "marketing_objectives"})
        payload = json.loads(result[0].text)
        assert payload["resource"] == "marketing_objectives"
        assert payload["values"] == ["BRAND_AWARENESS"]
