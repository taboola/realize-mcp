"""Tests for the update_campaign_my_audiences write tool."""
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
        "targeting": {
            "collection": [
                {"collection": [224820, 25287], "type": "INCLUDE"},
            ]
        },
    }
    base.update(overrides)
    return base


class TestMyAudiencesValidation:
    @pytest.mark.asyncio
    async def test_rejects_targeting_not_object(self):
        with pytest.raises(ToolInputError, match="targeting must be an object"):
            await handle_call_tool("update_campaign_my_audiences", _args(targeting=[]))

    @pytest.mark.asyncio
    async def test_rejects_missing_collection(self):
        with pytest.raises(ToolInputError, match="targeting.collection must be a list"):
            await handle_call_tool("update_campaign_my_audiences", _args(targeting={}))

    @pytest.mark.asyncio
    async def test_rejects_collection_not_a_list(self):
        with pytest.raises(ToolInputError, match="targeting.collection must be a list"):
            await handle_call_tool(
                "update_campaign_my_audiences",
                _args(targeting={"collection": "INCLUDE"}),
            )

    @pytest.mark.asyncio
    async def test_rejects_rule_not_object(self):
        with pytest.raises(ToolInputError, match=r"targeting.collection\[0\] must be an object"):
            await handle_call_tool(
                "update_campaign_my_audiences",
                _args(targeting={"collection": ["INCLUDE"]}),
            )

    @pytest.mark.asyncio
    async def test_rejects_rule_missing_type(self):
        with pytest.raises(ToolInputError, match="type must be one of"):
            await handle_call_tool(
                "update_campaign_my_audiences",
                _args(targeting={"collection": [{"collection": [1, 2]}]}),
            )

    @pytest.mark.asyncio
    async def test_rejects_invalid_rule_type(self):
        with pytest.raises(ToolInputError, match="type must be one of"):
            await handle_call_tool(
                "update_campaign_my_audiences",
                _args(targeting={"collection": [{"collection": [1], "type": "ALL"}]}),
            )

    @pytest.mark.asyncio
    async def test_rejects_rule_collection_not_a_list(self):
        with pytest.raises(ToolInputError, match=r"\[0\].collection must be a list of integer audience IDs"):
            await handle_call_tool(
                "update_campaign_my_audiences",
                _args(targeting={"collection": [{"collection": 1, "type": "INCLUDE"}]}),
            )

    @pytest.mark.asyncio
    async def test_rejects_string_id(self):
        with pytest.raises(ToolInputError, match=r"\[0\].collection\[0\] must be an integer"):
            await handle_call_tool(
                "update_campaign_my_audiences",
                _args(targeting={"collection": [{"collection": ["1"], "type": "INCLUDE"}]}),
            )

    @pytest.mark.asyncio
    async def test_rejects_float_id(self):
        with pytest.raises(ToolInputError, match=r"\[0\].collection\[0\] must be an integer"):
            await handle_call_tool(
                "update_campaign_my_audiences",
                _args(targeting={"collection": [{"collection": [1.5], "type": "INCLUDE"}]}),
            )

    @pytest.mark.asyncio
    async def test_rejects_bool_id(self):
        with pytest.raises(ToolInputError, match=r"\[0\].collection\[0\] must be an integer"):
            await handle_call_tool(
                "update_campaign_my_audiences",
                _args(targeting={"collection": [{"collection": [True], "type": "INCLUDE"}]}),
            )

    @pytest.mark.asyncio
    async def test_rejects_null_id(self):
        with pytest.raises(ToolInputError, match=r"\[0\].collection\[1\] must be an integer"):
            await handle_call_tool(
                "update_campaign_my_audiences",
                _args(targeting={"collection": [{"collection": [1, None, 2], "type": "INCLUDE"}]}),
            )

    @pytest.mark.asyncio
    async def test_missing_campaign_id_raises(self):
        args = _args()
        del args["campaign_id"]
        with pytest.raises(ToolInputError, match="campaign_id is required"):
            await handle_call_tool("update_campaign_my_audiences", args)

    @pytest.mark.asyncio
    async def test_numeric_account_id_rejected(self):
        with pytest.raises(ToolInputError, match="search_accounts"):
            await handle_call_tool("update_campaign_my_audiences", _args(account_id="12345"))


class TestMyAudiencesWire:
    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_posts_to_my_audiences_endpoint(self, mock_post):
        mock_post.return_value = {"id": "c-123"}

        await handle_call_tool("update_campaign_my_audiences", _args())

        assert _post_endpoint(mock_post) == "/acme-inc/campaigns/c-123/targeting/my_audiences"

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_url_encodes_path_segments(self, mock_post):
        mock_post.return_value = {"id": "c-123"}

        await handle_call_tool(
            "update_campaign_my_audiences",
            _args(account_id="acme/evil", campaign_id="c/1"),
        )

        assert _post_endpoint(mock_post) == "/acme%2Fevil/campaigns/c%2F1/targeting/my_audiences"

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_body_passes_through_unchanged(self, mock_post):
        mock_post.return_value = {"id": "c-123"}

        targeting = {
            "collection": [
                {"collection": [224820, 25287], "type": "INCLUDE"},
                {"collection": [19884, 29870], "type": "EXCLUDE"},
            ]
        }
        await handle_call_tool(
            "update_campaign_my_audiences",
            _args(targeting=targeting),
        )

        assert _post_body(mock_post) == targeting

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_empty_collection_clears(self, mock_post):
        mock_post.return_value = {"id": "c-123"}

        await handle_call_tool(
            "update_campaign_my_audiences",
            _args(targeting={"collection": []}),
        )

        assert _post_body(mock_post) == {"collection": []}

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_multiple_rules_passed_through(self, mock_post):
        mock_post.return_value = {"id": "c-123"}

        targeting = {
            "collection": [
                {"collection": [1], "type": "INCLUDE"},
                {"collection": [2, 3], "type": "EXCLUDE"},
                {"collection": [4, 5, 6], "type": "INCLUDE"},
            ]
        }
        await handle_call_tool(
            "update_campaign_my_audiences",
            _args(targeting=targeting),
        )

        assert _post_body(mock_post) == targeting


class TestMyAudiencesAnnotations:
    @pytest.mark.asyncio
    async def test_has_destructive_idempotent_open_world_annotations(self):
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        tool = next(t for t in tools if t.name == "update_campaign_my_audiences")

        assert tool.annotations is not None
        assert tool.annotations.destructiveHint is True
        assert tool.annotations.idempotentHint is True
        assert tool.annotations.openWorldHint is True
