"""Tests for the get_account tool."""
import pytest
from unittest.mock import AsyncMock, patch

from realize.realize_server import handle_call_tool
from realize.tools.errors import ToolInputError


def _get_endpoint(mock_get):
    args, kwargs = mock_get.call_args
    return args[0] if args else kwargs.get("endpoint")


class TestGetAccount:
    @pytest.mark.asyncio
    @patch('realize.tools.account_handlers.client.get', new_callable=AsyncMock)
    async def test_endpoint(self, mock_get):
        mock_get.return_value = {"id": "acme-inc", "currency": "USD"}
        await handle_call_tool("get_account", {"account_id": "acme-inc"})
        assert _get_endpoint(mock_get) == "/acme-inc"

    @pytest.mark.asyncio
    @patch('realize.tools.account_handlers.client.get', new_callable=AsyncMock)
    async def test_url_encodes_account_id(self, mock_get):
        mock_get.return_value = {}
        await handle_call_tool("get_account", {"account_id": "acme/evil"})
        assert _get_endpoint(mock_get) == "/acme%2Fevil"

    @pytest.mark.asyncio
    async def test_missing_account_id_rejected(self):
        with pytest.raises(ToolInputError, match="account_id is required"):
            await handle_call_tool("get_account", {})

    @pytest.mark.asyncio
    async def test_numeric_account_id_rejected(self):
        with pytest.raises(ToolInputError, match="search_accounts"):
            await handle_call_tool("get_account", {"account_id": "12345"})

    @pytest.mark.asyncio
    @patch('realize.tools.account_handlers.client.get', new_callable=AsyncMock)
    async def test_response_text_includes_account_id(self, mock_get):
        mock_get.return_value = {"id": "acme-inc", "currency": "USD"}
        result = await handle_call_tool("get_account", {"account_id": "acme-inc"})
        assert "acme-inc" in result[0].text


class TestGetAccountSchema:
    @pytest.mark.asyncio
    async def test_get_account_registered(self):
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        names = {t.name for t in tools}
        assert "get_account" in names

    @pytest.mark.asyncio
    async def test_get_account_required_account_id(self):
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        ga = next(t for t in tools if t.name == "get_account")
        assert ga.inputSchema["required"] == ["account_id"]

    @pytest.mark.asyncio
    async def test_get_account_no_destructive_annotation(self):
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        ga = next(t for t in tools if t.name == "get_account")
        assert ga.annotations is None
