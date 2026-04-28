"""Tests for the update_campaign_geo_advanced write tool."""
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
        "geo_targeting": {
            "state": "EXISTS",
            "value": [
                {"type": "INCLUDE", "value": [{"country": "US"}]},
            ],
        },
    }
    base.update(overrides)
    return base


class TestAdvancedValidation:
    @pytest.mark.asyncio
    async def test_rejects_unsupported_state(self):
        with pytest.raises(ToolInputError, match="state must be one of"):
            await handle_call_tool(
                "update_campaign_geo_advanced",
                _args(geo_targeting={"state": "NONE", "value": []}),
            )

    @pytest.mark.asyncio
    async def test_rejects_state_all_with_rules(self):
        with pytest.raises(ToolInputError, match="empty when state=ALL"):
            await handle_call_tool(
                "update_campaign_geo_advanced",
                _args(geo_targeting={
                    "state": "ALL",
                    "value": [{"type": "INCLUDE", "value": [{"country": "US"}]}],
                }),
            )

    @pytest.mark.asyncio
    async def test_rejects_state_exists_without_rules(self):
        with pytest.raises(ToolInputError, match="non-empty when state=EXISTS"):
            await handle_call_tool(
                "update_campaign_geo_advanced",
                _args(geo_targeting={"state": "EXISTS", "value": []}),
            )

    @pytest.mark.asyncio
    async def test_rejects_invalid_rule_type(self):
        with pytest.raises(ToolInputError, match=r"value\[0\]\.type"):
            await handle_call_tool(
                "update_campaign_geo_advanced",
                _args(geo_targeting={
                    "state": "EXISTS",
                    "value": [{"type": "ONLY", "value": [{"country": "US"}]}],
                }),
            )

    @pytest.mark.asyncio
    async def test_rejects_empty_vector_list(self):
        with pytest.raises(ToolInputError, match="non-empty list of vectors"):
            await handle_call_tool(
                "update_campaign_geo_advanced",
                _args(geo_targeting={
                    "state": "EXISTS",
                    "value": [{"type": "INCLUDE", "value": []}],
                }),
            )

    @pytest.mark.asyncio
    async def test_rejects_vector_with_all_nulls(self):
        with pytest.raises(ToolInputError, match="must set at least one of"):
            await handle_call_tool(
                "update_campaign_geo_advanced",
                _args(geo_targeting={
                    "state": "EXISTS",
                    "value": [{"type": "INCLUDE", "value": [
                        {"country": None, "region": None, "dma": None,
                         "city": None, "postal_code": None}
                    ]}],
                }),
            )

    @pytest.mark.asyncio
    async def test_missing_campaign_id_raises(self):
        args = _args()
        del args["campaign_id"]
        with pytest.raises(ToolInputError, match="campaign_id is required"):
            await handle_call_tool("update_campaign_geo_advanced", args)

    @pytest.mark.asyncio
    async def test_numeric_account_id_rejected(self):
        with pytest.raises(ToolInputError, match="search_accounts"):
            await handle_call_tool("update_campaign_geo_advanced", _args(account_id="12345"))


class TestAdvancedWire:
    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_posts_geoTargeting_only(self, mock_post):
        mock_post.return_value = {"id": "c-123"}

        await handle_call_tool("update_campaign_geo_advanced", _args())

        body = _post_body(mock_post)
        assert set(body.keys()) == {"geoTargeting"}
        assert _post_endpoint(mock_post) == "/acme-inc/campaigns/c-123"

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_camelcases_postal_code(self, mock_post):
        mock_post.return_value = {"id": "c-123"}

        await handle_call_tool(
            "update_campaign_geo_advanced",
            _args(geo_targeting={
                "state": "EXISTS",
                "value": [{"type": "INCLUDE", "value": [
                    {"country": "US", "postal_code": "94110"}
                ]}],
            }),
        )

        vec = _post_body(mock_post)["geoTargeting"]["value"][0]["value"][0]
        assert "postalCode" in vec
        assert vec["postalCode"] == "94110"
        assert "postal_code" not in vec

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_strips_null_dimensions_from_vectors(self, mock_post):
        mock_post.return_value = {"id": "c-123"}

        await handle_call_tool(
            "update_campaign_geo_advanced",
            _args(geo_targeting={
                "state": "EXISTS",
                "value": [{"type": "INCLUDE", "value": [
                    {"country": "US", "region": None, "dma": None,
                     "city": None, "postal_code": None}
                ]}],
            }),
        )

        vec = _post_body(mock_post)["geoTargeting"]["value"][0]["value"][0]
        assert vec == {"country": "US"}

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_state_all_emits_empty_rules(self, mock_post):
        mock_post.return_value = {"id": "c-123"}

        await handle_call_tool(
            "update_campaign_geo_advanced",
            _args(geo_targeting={"state": "ALL", "value": []}),
        )

        assert _post_body(mock_post)["geoTargeting"] == {"state": "ALL", "value": []}

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_include_and_exclude_rules_round_trip(self, mock_post):
        mock_post.return_value = {"id": "c-123"}

        await handle_call_tool(
            "update_campaign_geo_advanced",
            _args(geo_targeting={
                "state": "EXISTS",
                "value": [
                    {"type": "INCLUDE", "value": [
                        {"country": "US"}, {"country": "CA"},
                    ]},
                    {"type": "EXCLUDE", "value": [
                        {"country": "US", "region": "TX"},
                    ]},
                ],
            }),
        )

        gt = _post_body(mock_post)["geoTargeting"]
        assert gt["state"] == "EXISTS"
        assert gt["value"][0]["type"] == "INCLUDE"
        assert gt["value"][0]["value"] == [{"country": "US"}, {"country": "CA"}]
        assert gt["value"][1]["type"] == "EXCLUDE"
        assert gt["value"][1]["value"] == [{"country": "US", "region": "TX"}]


class TestAdvancedAnnotations:
    @pytest.mark.asyncio
    async def test_has_destructive_idempotent_annotations(self):
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        tool = next(t for t in tools if t.name == "update_campaign_geo_advanced")

        assert tool.annotations is not None
        assert tool.annotations.destructiveHint is True
        assert tool.annotations.idempotentHint is True
        assert tool.annotations.openWorldHint is True
