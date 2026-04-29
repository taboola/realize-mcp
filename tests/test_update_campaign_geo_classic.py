"""Tests for the update_campaign_geo_classic write tool."""
import pytest
from unittest.mock import AsyncMock, patch

from realize.realize_server import handle_call_tool
from realize.tools.errors import ToolInputError


def _post_endpoint(mock_post):
    args, kwargs = mock_post.call_args
    return args[0] if args else kwargs.get("endpoint")


def _post_body(mock_post):
    _args, kwargs = mock_post.call_args
    return kwargs.get("data")


def _args(**overrides):
    base = {
        "account_id": "acme-inc",
        "campaign_id": "c-123",
        "dimension": "country",
        "targeting": {"type": "INCLUDE", "value": ["US"]},
    }
    base.update(overrides)
    return base


class TestClassicValidation:
    @pytest.mark.asyncio
    async def test_rejects_unknown_dimension(self):
        with pytest.raises(ToolInputError, match="dimension must be one of"):
            await handle_call_tool("update_campaign_geo_classic", _args(dimension="zip"))

    @pytest.mark.asyncio
    async def test_rejects_invalid_type(self):
        with pytest.raises(ToolInputError, match="targeting.type"):
            await handle_call_tool(
                "update_campaign_geo_classic",
                _args(targeting={"type": "ONLY", "value": ["US"]}),
            )

    @pytest.mark.asyncio
    async def test_rejects_all_with_nonempty_value(self):
        with pytest.raises(ToolInputError, match="empty when type=ALL"):
            await handle_call_tool(
                "update_campaign_geo_classic",
                _args(targeting={"type": "ALL", "value": ["US"]}),
            )

    @pytest.mark.asyncio
    async def test_rejects_include_with_empty_value(self):
        with pytest.raises(ToolInputError, match="non-empty when type=INCLUDE"):
            await handle_call_tool(
                "update_campaign_geo_classic",
                _args(targeting={"type": "INCLUDE", "value": []}),
            )

    @pytest.mark.asyncio
    async def test_value_must_be_list_of_strings(self):
        with pytest.raises(ToolInputError, match="list of strings"):
            await handle_call_tool(
                "update_campaign_geo_classic",
                _args(targeting={"type": "INCLUDE", "value": [1, 2]}),
            )

    @pytest.mark.asyncio
    async def test_missing_campaign_id_raises(self):
        args = _args()
        del args["campaign_id"]
        with pytest.raises(ToolInputError, match="campaign_id is required"):
            await handle_call_tool("update_campaign_geo_classic", args)

    @pytest.mark.asyncio
    async def test_numeric_account_id_rejected(self):
        with pytest.raises(ToolInputError, match="search_accounts"):
            await handle_call_tool("update_campaign_geo_classic", _args(account_id="12345"))


class TestClassicWireMapping:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("dimension,wire_field", [
        ("country", "country_targeting"),
        ("region", "region_country_targeting"),
        ("dma", "dma_country_targeting"),
        ("city", "city_targeting"),
        ("postal_code", "postal_code_targeting"),
    ])
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_dimension_maps_to_wire_field(self, mock_post, dimension, wire_field):
        mock_post.return_value = {"id": "c-123"}

        await handle_call_tool(
            "update_campaign_geo_classic",
            _args(
                dimension=dimension,
                targeting={"type": "INCLUDE", "value": ["X"]},
            ),
        )

        body = _post_body(mock_post)
        assert wire_field in body
        assert body[wire_field] == {"type": "INCLUDE", "value": ["X"]}
        # body contains only the chosen wire field
        assert set(body.keys()) == {wire_field}

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_posts_to_campaign_endpoint(self, mock_post):
        mock_post.return_value = {"id": "c-123"}

        await handle_call_tool("update_campaign_geo_classic", _args())

        assert _post_endpoint(mock_post) == "/acme-inc/campaigns/c-123"

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_url_encodes_path_segments(self, mock_post):
        mock_post.return_value = {"id": "c-123"}

        await handle_call_tool(
            "update_campaign_geo_classic",
            _args(account_id="acme/evil", campaign_id="c/1"),
        )

        assert _post_endpoint(mock_post) == "/acme%2Fevil/campaigns/c%2F1"

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_clear_with_all_sends_empty_value(self, mock_post):
        mock_post.return_value = {"id": "c-123"}

        await handle_call_tool(
            "update_campaign_geo_classic",
            _args(dimension="city", targeting={"type": "ALL", "value": []}),
        )

        assert _post_body(mock_post) == {"city_targeting": {"type": "ALL", "value": []}}


class TestClassicAnnotations:
    @pytest.mark.asyncio
    async def test_has_destructive_idempotent_annotations(self):
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        tool = next(t for t in tools if t.name == "update_campaign_geo_classic")

        assert tool.annotations is not None
        assert tool.annotations.destructiveHint is True
        assert tool.annotations.idempotentHint is True
        assert tool.annotations.openWorldHint is True
