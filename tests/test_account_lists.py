"""Tests for the per-account list_account_* discovery tools."""
import pytest
from unittest.mock import AsyncMock, patch

from realize.realize_server import handle_call_tool
from realize.tools.errors import ToolInputError


def _called(mock_get):
    args, kwargs = mock_get.call_args
    endpoint = args[0] if args else kwargs.get("endpoint")
    return endpoint, kwargs.get("params")


class TestAudiences:
    @pytest.mark.asyncio
    @patch("realize.tools.account_lists.client.get", new_callable=AsyncMock)
    async def test_calls_my_audiences_unified(self, mock_get):
        mock_get.return_value = {"results": []}
        await handle_call_tool("list_account_audiences", {"account_id": "acme-inc"})
        endpoint, params = _called(mock_get)
        assert endpoint == "/acme-inc/my_audiences_unified"
        assert params is None

    @pytest.mark.asyncio
    async def test_rejects_numeric_account_id(self):
        with pytest.raises(ToolInputError, match="search_accounts"):
            await handle_call_tool("list_account_audiences", {"account_id": "12345"})

    @pytest.mark.asyncio
    @patch("realize.tools.account_lists.client.get", new_callable=AsyncMock)
    async def test_url_encodes_account_id(self, mock_get):
        mock_get.return_value = {"results": []}
        await handle_call_tool("list_account_audiences", {"account_id": "acme/evil"})
        endpoint, _ = _called(mock_get)
        assert endpoint == "/acme%2Fevil/my_audiences_unified"


class TestConversionRules:
    @pytest.mark.asyncio
    @patch("realize.tools.account_lists.client.get", new_callable=AsyncMock)
    async def test_calls_conversion_rule_endpoint(self, mock_get):
        mock_get.return_value = {"results": []}
        await handle_call_tool("list_account_conversion_rules", {"account_id": "acme-inc"})
        endpoint, _ = _called(mock_get)
        assert endpoint == "/acme-inc/universal_pixel/conversion_rule"

    @pytest.mark.asyncio
    async def test_rejects_numeric_account_id(self):
        with pytest.raises(ToolInputError, match="search_accounts"):
            await handle_call_tool(
                "list_account_conversion_rules", {"account_id": "12345"}
            )


class TestPublishers:
    @pytest.mark.asyncio
    @patch("realize.tools.account_lists.client.get", new_callable=AsyncMock)
    async def test_calls_allowed_publishers_endpoint(self, mock_get):
        mock_get.return_value = {"results": []}
        await handle_call_tool("list_account_publishers", {"account_id": "acme-inc"})
        endpoint, params = _called(mock_get)
        assert endpoint == "/acme-inc/allowed-publishers"
        assert params is None

    @pytest.mark.asyncio
    @patch("realize.tools.account_lists.client.get", new_callable=AsyncMock)
    async def test_passes_search_text_param(self, mock_get):
        mock_get.return_value = {"results": []}
        await handle_call_tool(
            "list_account_publishers",
            {"account_id": "acme-inc", "search_text": "premium"},
        )
        _, params = _called(mock_get)
        assert params == {"search_text": "premium"}

    @pytest.mark.asyncio
    async def test_rejects_non_string_search_text(self):
        with pytest.raises(ToolInputError, match="search_text must be a string"):
            await handle_call_tool(
                "list_account_publishers",
                {"account_id": "acme-inc", "search_text": 123},
            )

    @pytest.mark.asyncio
    async def test_rejects_numeric_account_id(self):
        with pytest.raises(ToolInputError, match="search_accounts"):
            await handle_call_tool(
                "list_account_publishers", {"account_id": "12345"}
            )


class TestContextualSegments:
    @pytest.mark.asyncio
    @patch("realize.tools.account_lists.client.get", new_callable=AsyncMock)
    async def test_calls_dictionary_endpoint(self, mock_get):
        mock_get.return_value = {"results": []}
        await handle_call_tool(
            "list_account_contextual_segments", {"account_id": "acme-inc"}
        )
        endpoint, params = _called(mock_get)
        assert endpoint == "/acme-inc/dictionary/contextual_segments"
        assert params is None

    @pytest.mark.asyncio
    @patch("realize.tools.account_lists.client.get", new_callable=AsyncMock)
    async def test_passes_country_codes_param(self, mock_get):
        mock_get.return_value = {"results": []}
        await handle_call_tool(
            "list_account_contextual_segments",
            {"account_id": "acme-inc", "country_codes": "US,CA"},
        )
        _, params = _called(mock_get)
        assert params == {"countryCodes": "US,CA"}

    @pytest.mark.asyncio
    async def test_rejects_non_string_country_codes(self):
        with pytest.raises(ToolInputError, match="country_codes must be a comma-separated string"):
            await handle_call_tool(
                "list_account_contextual_segments",
                {"account_id": "acme-inc", "country_codes": ["US", "CA"]},
            )


class TestRegistration:
    @pytest.mark.asyncio
    async def test_all_account_tools_registered(self):
        from realize.realize_server import handle_list_tools

        tools = {t.name for t in await handle_list_tools()}
        for name in (
            "list_account_audiences",
            "list_account_conversion_rules",
            "list_account_publishers",
            "list_account_contextual_segments",
        ):
            assert name in tools
