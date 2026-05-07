"""Tests for the four account-scoped discovery tools.

search_audiences, search_lookalike_audiences, search_publishers,
search_conversion_rules.
"""
import json

import pytest
from unittest.mock import AsyncMock, patch

from realize.realize_server import handle_call_tool
from realize.tools.errors import ToolInputError


def _get_endpoint(mock_get):
    args, kwargs = mock_get.call_args
    return args[0] if args else kwargs.get("endpoint")


def _get_params(mock_get):
    _args, kwargs = mock_get.call_args
    return kwargs.get("params")


class TestSearchAudiences:
    @pytest.mark.asyncio
    @patch('realize.tools.discovery_handlers.client.get', new_callable=AsyncMock)
    async def test_basic_endpoint(self, mock_get):
        mock_get.return_value = {"results": []}
        await handle_call_tool("search_audiences", {"account_id": "acme-inc"})
        assert _get_endpoint(mock_get) == "/acme-inc/my_audiences_unified"
        assert _get_params(mock_get) is None

    @pytest.mark.asyncio
    @patch('realize.tools.discovery_handlers.client.get', new_callable=AsyncMock)
    async def test_country_codes_filter(self, mock_get):
        mock_get.return_value = {"results": []}
        await handle_call_tool("search_audiences", {
            "account_id": "acme-inc",
            "country_codes": "US,CA",
        })
        assert _get_params(mock_get) == {"countryCodes": "US,CA"}

    @pytest.mark.asyncio
    @patch('realize.tools.discovery_handlers.client.get', new_callable=AsyncMock)
    async def test_country_targeting_type_filter(self, mock_get):
        mock_get.return_value = {"results": []}
        await handle_call_tool("search_audiences", {
            "account_id": "acme-inc",
            "country_targeting_type": "INCLUDE",
        })
        assert _get_params(mock_get) == {"countryTargetingType": "INCLUDE"}

    @pytest.mark.asyncio
    async def test_invalid_country_targeting_type_rejected(self):
        with pytest.raises(ToolInputError, match="country_targeting_type must be one of"):
            await handle_call_tool("search_audiences", {
                "account_id": "acme-inc",
                "country_targeting_type": "BOGUS",
            })

    @pytest.mark.asyncio
    async def test_missing_account_id_rejected(self):
        with pytest.raises(ToolInputError, match="account_id is required"):
            await handle_call_tool("search_audiences", {})

    @pytest.mark.asyncio
    async def test_numeric_account_id_rejected(self):
        with pytest.raises(ToolInputError, match="search_accounts"):
            await handle_call_tool("search_audiences", {"account_id": "12345"})

    @pytest.mark.asyncio
    @patch('realize.tools.discovery_handlers.client.get', new_callable=AsyncMock)
    async def test_url_encodes_account_id(self, mock_get):
        mock_get.return_value = {"results": []}
        await handle_call_tool("search_audiences", {"account_id": "acme/evil"})
        assert _get_endpoint(mock_get) == "/acme%2Fevil/my_audiences_unified"

    @pytest.mark.asyncio
    @patch('realize.tools.discovery_handlers.client.get', new_callable=AsyncMock)
    async def test_response_shape(self, mock_get):
        mock_get.return_value = {"results": [{"value": {"id": 1, "name": "A"}}]}
        result = await handle_call_tool("search_audiences", {"account_id": "acme-inc"})
        payload = json.loads(result[0].text)
        assert payload["account_id"] == "acme-inc"
        assert payload["values"] == [{"id": 1, "name": "A"}]


class TestSearchLookalikeAudiences:
    @pytest.mark.asyncio
    @patch('realize.tools.discovery_handlers.client.get', new_callable=AsyncMock)
    async def test_no_country(self, mock_get):
        mock_get.return_value = {"results": []}
        await handle_call_tool("search_lookalike_audiences", {"account_id": "acme-inc"})
        assert _get_endpoint(mock_get) == "/acme-inc/dictionary/lookalike_audiences"

    @pytest.mark.asyncio
    @patch('realize.tools.discovery_handlers.client.get', new_callable=AsyncMock)
    async def test_with_country_uses_path_variant(self, mock_get):
        mock_get.return_value = {"results": []}
        await handle_call_tool("search_lookalike_audiences", {
            "account_id": "acme-inc",
            "country_code": "US",
        })
        assert _get_endpoint(mock_get) == "/acme-inc/dictionary/lookalike_audiences/US"

    @pytest.mark.asyncio
    async def test_missing_account_id_rejected(self):
        with pytest.raises(ToolInputError, match="account_id is required"):
            await handle_call_tool("search_lookalike_audiences", {})


class TestSearchPublishers:
    @pytest.mark.asyncio
    @patch('realize.tools.discovery_handlers.client.get', new_callable=AsyncMock)
    async def test_endpoint(self, mock_get):
        mock_get.return_value = {"results": []}
        await handle_call_tool("search_publishers", {"account_id": "acme-inc", "query": "*"})
        assert _get_endpoint(mock_get) == "/acme-inc/allowed-publishers"

    @pytest.mark.asyncio
    @patch('realize.tools.discovery_handlers.client.get', new_callable=AsyncMock)
    async def test_query_filter_forwarded(self, mock_get):
        mock_get.return_value = {"results": []}
        await handle_call_tool("search_publishers", {"account_id": "acme-inc", "query": "yahoo"})
        params = mock_get.call_args.kwargs.get("params") or mock_get.call_args.args[1]
        assert params["search_text"] == "yahoo"
        assert params["page"] == 1
        assert params["page_size"] == 10

    @pytest.mark.asyncio
    @patch('realize.tools.discovery_handlers.client.get', new_callable=AsyncMock)
    async def test_wildcard_omits_search_text(self, mock_get):
        mock_get.return_value = {"results": []}
        await handle_call_tool("search_publishers", {"account_id": "acme-inc", "query": "*"})
        params = mock_get.call_args.kwargs.get("params") or mock_get.call_args.args[1]
        assert "search_text" not in params

    @pytest.mark.asyncio
    @patch('realize.tools.discovery_handlers.client.get', new_callable=AsyncMock)
    async def test_publisher_ids_forwarded(self, mock_get):
        mock_get.return_value = {"results": []}
        await handle_call_tool(
            "search_publishers",
            {"account_id": "acme-inc", "query": "*", "publisher_ids": [1, 2, 3]},
        )
        params = mock_get.call_args.kwargs.get("params") or mock_get.call_args.args[1]
        assert params["publisher_ids"] == "1,2,3"

    @pytest.mark.asyncio
    @patch('realize.tools.discovery_handlers.client.get', new_callable=AsyncMock)
    async def test_response_trimmed(self, mock_get):
        mock_get.return_value = {"results": [{
            "id": 99, "name": "P1", "account_id": "p1", "country": "US", "is_active": True,
            "external_metadata": {"big": "x" * 1000}, "language": "en", "currency": "USD",
        }]}
        result = await handle_call_tool(
            "search_publishers", {"account_id": "acme-inc", "query": "*"}
        )
        text = result[0].text
        assert "external_metadata" not in text
        assert "currency" not in text
        assert "P1" in text

    @pytest.mark.asyncio
    @patch('realize.tools.discovery_handlers.client.get', new_callable=AsyncMock)
    async def test_resolved_account_ids_hint(self, mock_get):
        mock_get.return_value = {
            "results": [
                {"id": 1, "name": "Yahoo! Mail", "account_id": "yahoo-mail",
                 "country": "US", "is_active": True},
                {"id": 2, "name": "Yahoo! News", "account_id": "yahoo-news",
                 "country": None, "is_active": False},
            ],
            "metadata": {"total": 2},
        }
        result = await handle_call_tool(
            "search_publishers", {"account_id": "acme-inc", "query": "yahoo"}
        )
        text = result[0].text
        assert text.startswith("Publisher search results — page 1, page_size 10, total 2")
        assert "Resolved publisher account_ids" in text
        assert "account_id='yahoo-mail' (Yahoo! Mail) [US · active]" in text
        assert "account_id='yahoo-news' (Yahoo! News) [inactive]" in text
        assert "Full response:" in text

    @pytest.mark.asyncio
    async def test_missing_query_rejected(self):
        with pytest.raises(ToolInputError, match="query is required"):
            await handle_call_tool("search_publishers", {"account_id": "acme-inc"})

    @pytest.mark.asyncio
    async def test_missing_account_id_rejected(self):
        with pytest.raises(ToolInputError, match="account_id is required"):
            await handle_call_tool("search_publishers", {"query": "*"})


class TestSearchConversionRules:
    @pytest.mark.asyncio
    @patch('realize.tools.discovery_handlers.client.get', new_callable=AsyncMock)
    async def test_endpoint(self, mock_get):
        mock_get.return_value = {"results": []}
        await handle_call_tool("search_conversion_rules", {"account_id": "acme-inc"})
        assert _get_endpoint(mock_get) == "/acme-inc/universal_pixel/conversion_rule"

    @pytest.mark.asyncio
    async def test_missing_account_id_rejected(self):
        with pytest.raises(ToolInputError, match="account_id is required"):
            await handle_call_tool("search_conversion_rules", {})


class TestDiscoverySchemas:
    @pytest.mark.asyncio
    async def test_search_audiences_schema(self):
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        sa = next(t for t in tools if t.name == "search_audiences")
        props = sa.inputSchema["properties"]
        assert "account_id" in props
        assert "country_codes" in props
        assert "country_targeting_type" in props
        assert set(props["country_targeting_type"]["enum"]) == {"ALL", "INCLUDE", "EXCLUDE"}
        assert sa.inputSchema["required"] == ["account_id"]

    @pytest.mark.asyncio
    async def test_all_discovery_tools_registered(self):
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        names = {t.name for t in tools}
        expected = {
            "search_audiences",
            "search_lookalike_audiences",
            "search_contextual_segments",
            "search_publishers",
            "search_conversion_rules",
        }
        assert expected.issubset(names)


class TestSearchContextualSegments:
    @pytest.mark.asyncio
    @patch('realize.tools.discovery_handlers.client.get', new_callable=AsyncMock)
    async def test_endpoint(self, mock_get):
        mock_get.return_value = {"results": []}
        await handle_call_tool("search_contextual_segments", {"account_id": "acme-inc"})
        assert _get_endpoint(mock_get) == "/acme-inc/dictionary/contextual_segments"

    @pytest.mark.asyncio
    @patch('realize.tools.discovery_handlers.client.get', new_callable=AsyncMock)
    async def test_country_filters_forwarded(self, mock_get):
        mock_get.return_value = {"results": []}
        await handle_call_tool(
            "search_contextual_segments",
            {"account_id": "acme-inc", "country_codes": "US,CA", "country_targeting_type": "INCLUDE"},
        )
        params = mock_get.call_args.kwargs.get("params") or mock_get.call_args.args[1]
        assert params["countryCodes"] == "US,CA"
        assert params["countryTargetingType"] == "INCLUDE"

    @pytest.mark.asyncio
    async def test_missing_account_id_rejected(self):
        with pytest.raises(ToolInputError, match="account_id is required"):
            await handle_call_tool("search_contextual_segments", {})
