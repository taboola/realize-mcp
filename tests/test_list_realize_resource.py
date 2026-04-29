"""Tests for the list_realize_resource discovery tool."""
import json
import pytest
from unittest.mock import AsyncMock, patch

from realize.realize_server import handle_call_tool
from realize.tools.errors import ToolInputError


def _called_endpoint(mock_get):
    args, kwargs = mock_get.call_args
    return args[0] if args else kwargs.get("endpoint")


def _payload(mock_calls=None):
    """Return a representative APIResults<APIResource<String>> payload."""
    return {"results": [{"value": "US"}, {"value": "CA"}, {"value": "GB"}]}


class TestResourceValidation:
    @pytest.mark.asyncio
    async def test_rejects_unknown_resource(self):
        with pytest.raises(ToolInputError, match="resource must be one of"):
            await handle_call_tool("list_realize_resource", {"resource": "bogus"})

    @pytest.mark.asyncio
    async def test_rejects_missing_resource(self):
        with pytest.raises(ToolInputError, match="resource must be one of"):
            await handle_call_tool("list_realize_resource", {})

    @pytest.mark.asyncio
    async def test_rejects_regions_without_country_code(self):
        with pytest.raises(ToolInputError, match="args.country_code is required"):
            await handle_call_tool("list_realize_resource", {"resource": "regions"})

    @pytest.mark.asyncio
    async def test_rejects_dma_without_country_code(self):
        with pytest.raises(ToolInputError, match="args.country_code is required"):
            await handle_call_tool(
                "list_realize_resource", {"resource": "dma", "args": {}}
            )

    @pytest.mark.asyncio
    async def test_rejects_os_versions_without_os_family(self):
        with pytest.raises(ToolInputError, match="args.os_family is required"):
            await handle_call_tool(
                "list_realize_resource", {"resource": "operating_system_versions"}
            )


class TestResourceWire:
    @pytest.mark.asyncio
    @patch("realize.tools.resources.client.get", new_callable=AsyncMock)
    async def test_countries_calls_global_endpoint(self, mock_get):
        mock_get.return_value = _payload()
        await handle_call_tool("list_realize_resource", {"resource": "countries"})
        assert _called_endpoint(mock_get) == "/resources/countries"

    @pytest.mark.asyncio
    @patch("realize.tools.resources.client.get", new_callable=AsyncMock)
    async def test_regions_uses_country_code_in_path(self, mock_get):
        mock_get.return_value = _payload()
        await handle_call_tool(
            "list_realize_resource",
            {"resource": "regions", "args": {"country_code": "US"}},
        )
        assert _called_endpoint(mock_get) == "/resources/countries/US/regions"

    @pytest.mark.asyncio
    @patch("realize.tools.resources.client.get", new_callable=AsyncMock)
    async def test_country_code_is_url_encoded(self, mock_get):
        mock_get.return_value = _payload()
        await handle_call_tool(
            "list_realize_resource",
            {"resource": "cities", "args": {"country_code": "us/evil"}},
        )
        assert _called_endpoint(mock_get) == "/resources/countries/us%2Fevil/cities"

    @pytest.mark.asyncio
    @patch("realize.tools.resources.client.get", new_callable=AsyncMock)
    async def test_os_versions_uses_os_family_in_path(self, mock_get):
        mock_get.return_value = _payload()
        await handle_call_tool(
            "list_realize_resource",
            {"resource": "operating_system_versions", "args": {"os_family": "iOS"}},
        )
        assert _called_endpoint(mock_get) == "/resources/campaigns_properties/operating_systems/iOS"

    @pytest.mark.asyncio
    @patch("realize.tools.resources.client.get", new_callable=AsyncMock)
    async def test_browsers_calls_campaign_properties_path(self, mock_get):
        mock_get.return_value = _payload()
        await handle_call_tool("list_realize_resource", {"resource": "browsers"})
        assert _called_endpoint(mock_get) == "/resources/campaigns_properties/browsers"

    @pytest.mark.asyncio
    @patch("realize.tools.resources.client.get", new_callable=AsyncMock)
    async def test_time_zones_calls_activity_scheduler_path(self, mock_get):
        mock_get.return_value = _payload()
        await handle_call_tool("list_realize_resource", {"resource": "time_zones"})
        assert _called_endpoint(mock_get) == "/resources/campaigns_properties/activity-scheduler-time-zone"


class TestResourceResponse:
    @pytest.mark.asyncio
    @patch("realize.tools.resources.client.get", new_callable=AsyncMock)
    async def test_unwraps_api_results_to_flat_list(self, mock_get):
        mock_get.return_value = {"results": [{"value": "US"}, {"value": "CA"}]}
        result = await handle_call_tool("list_realize_resource", {"resource": "countries"})
        assert len(result) == 1
        body = json.loads(result[0].text)
        assert body["resource"] == "countries"
        assert body["values"] == ["US", "CA"]

    @pytest.mark.asyncio
    @patch("realize.tools.resources.client.get", new_callable=AsyncMock)
    async def test_passes_through_when_no_results_array(self, mock_get):
        # Some endpoints may return objects without a results array.
        mock_get.return_value = {"foo": "bar"}
        result = await handle_call_tool("list_realize_resource", {"resource": "countries"})
        body = json.loads(result[0].text)
        assert body["values"] == {"foo": "bar"}


class TestResourceAnnotations:
    @pytest.mark.asyncio
    async def test_tool_is_registered(self):
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        names = {t.name for t in tools}
        assert "list_realize_resource" in names
