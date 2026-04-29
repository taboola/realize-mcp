"""Tests for the update_campaign_lookalike_audience write tool."""
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
                {
                    "type": "INCLUDE",
                    "collection": [
                        {"rule_id": 1234567, "similarity_level": 10},
                    ],
                }
            ]
        },
    }
    base.update(overrides)
    return base


class TestLookalikeValidation:
    @pytest.mark.asyncio
    async def test_missing_campaign_id_raises(self):
        args = _args()
        del args["campaign_id"]
        with pytest.raises(ToolInputError, match="campaign_id is required"):
            await handle_call_tool("update_campaign_lookalike_audience", args)

    @pytest.mark.asyncio
    async def test_numeric_account_id_rejected(self):
        with pytest.raises(ToolInputError, match="search_accounts"):
            await handle_call_tool(
                "update_campaign_lookalike_audience", _args(account_id="12345")
            )

    @pytest.mark.asyncio
    async def test_rejects_targeting_not_object(self):
        with pytest.raises(ToolInputError, match="targeting must be an object"):
            await handle_call_tool(
                "update_campaign_lookalike_audience", _args(targeting=[])
            )

    @pytest.mark.asyncio
    async def test_rejects_missing_collection(self):
        with pytest.raises(ToolInputError, match="targeting.collection must be a list"):
            await handle_call_tool(
                "update_campaign_lookalike_audience", _args(targeting={})
            )

    @pytest.mark.asyncio
    async def test_rejects_collection_not_a_list(self):
        with pytest.raises(ToolInputError, match="targeting.collection must be a list"):
            await handle_call_tool(
                "update_campaign_lookalike_audience",
                _args(targeting={"collection": "INCLUDE"}),
            )

    @pytest.mark.asyncio
    async def test_rejects_outer_collection_size_gt_1(self):
        targeting = {
            "collection": [
                {"type": "INCLUDE", "collection": [{"rule_id": 1, "similarity_level": 5}]},
                {"type": "INCLUDE", "collection": [{"rule_id": 2, "similarity_level": 5}]},
            ]
        }
        with pytest.raises(ToolInputError, match="at most one block"):
            await handle_call_tool(
                "update_campaign_lookalike_audience", _args(targeting=targeting)
            )

    @pytest.mark.asyncio
    async def test_rejects_block_not_object(self):
        with pytest.raises(ToolInputError, match=r"targeting.collection\[0\] must be an object"):
            await handle_call_tool(
                "update_campaign_lookalike_audience",
                _args(targeting={"collection": ["INCLUDE"]}),
            )

    @pytest.mark.asyncio
    async def test_rejects_block_missing_type(self):
        with pytest.raises(ToolInputError, match="must be 'INCLUDE'"):
            await handle_call_tool(
                "update_campaign_lookalike_audience",
                _args(targeting={"collection": [{"collection": []}]}),
            )

    @pytest.mark.asyncio
    async def test_rejects_exclude_type(self):
        with pytest.raises(ToolInputError, match="must be 'INCLUDE'"):
            await handle_call_tool(
                "update_campaign_lookalike_audience",
                _args(targeting={"collection": [{"type": "EXCLUDE", "collection": []}]}),
            )

    @pytest.mark.asyncio
    async def test_rejects_unknown_type(self):
        with pytest.raises(ToolInputError, match="must be 'INCLUDE'"):
            await handle_call_tool(
                "update_campaign_lookalike_audience",
                _args(targeting={"collection": [{"type": "ALL", "collection": []}]}),
            )

    @pytest.mark.asyncio
    async def test_rejects_block_collection_not_a_list(self):
        with pytest.raises(ToolInputError, match=r"\[0\].collection must be a list"):
            await handle_call_tool(
                "update_campaign_lookalike_audience",
                _args(targeting={"collection": [{"type": "INCLUDE", "collection": 1}]}),
            )

    @pytest.mark.asyncio
    async def test_rejects_item_not_object(self):
        with pytest.raises(ToolInputError, match=r"\[0\].collection\[0\] must be an object"):
            await handle_call_tool(
                "update_campaign_lookalike_audience",
                _args(targeting={"collection": [{"type": "INCLUDE", "collection": [123]}]}),
            )

    @pytest.mark.asyncio
    async def test_rejects_missing_rule_id(self):
        with pytest.raises(ToolInputError, match="rule_id must be a positive integer"):
            await handle_call_tool(
                "update_campaign_lookalike_audience",
                _args(targeting={"collection": [{"type": "INCLUDE", "collection": [{"similarity_level": 5}]}]}),
            )

    @pytest.mark.asyncio
    async def test_rejects_missing_similarity_level(self):
        with pytest.raises(ToolInputError, match="similarity_level must be one of"):
            await handle_call_tool(
                "update_campaign_lookalike_audience",
                _args(targeting={"collection": [{"type": "INCLUDE", "collection": [{"rule_id": 1}]}]}),
            )

    @pytest.mark.asyncio
    async def test_rejects_string_rule_id(self):
        with pytest.raises(ToolInputError, match="rule_id must be a positive integer"):
            await handle_call_tool(
                "update_campaign_lookalike_audience",
                _args(targeting={"collection": [{"type": "INCLUDE", "collection": [{"rule_id": "1", "similarity_level": 5}]}]}),
            )

    @pytest.mark.asyncio
    async def test_rejects_float_rule_id(self):
        with pytest.raises(ToolInputError, match="rule_id must be a positive integer"):
            await handle_call_tool(
                "update_campaign_lookalike_audience",
                _args(targeting={"collection": [{"type": "INCLUDE", "collection": [{"rule_id": 1.5, "similarity_level": 5}]}]}),
            )

    @pytest.mark.asyncio
    async def test_rejects_bool_rule_id(self):
        with pytest.raises(ToolInputError, match="rule_id must be a positive integer"):
            await handle_call_tool(
                "update_campaign_lookalike_audience",
                _args(targeting={"collection": [{"type": "INCLUDE", "collection": [{"rule_id": True, "similarity_level": 5}]}]}),
            )

    @pytest.mark.asyncio
    async def test_rejects_zero_rule_id(self):
        with pytest.raises(ToolInputError, match="rule_id must be a positive integer"):
            await handle_call_tool(
                "update_campaign_lookalike_audience",
                _args(targeting={"collection": [{"type": "INCLUDE", "collection": [{"rule_id": 0, "similarity_level": 5}]}]}),
            )

    @pytest.mark.parametrize("similarity", [7, 100, -1, 0, 6])
    @pytest.mark.asyncio
    async def test_rejects_invalid_similarity_level(self, similarity):
        with pytest.raises(ToolInputError, match="similarity_level must be one of"):
            await handle_call_tool(
                "update_campaign_lookalike_audience",
                _args(targeting={"collection": [{"type": "INCLUDE", "collection": [{"rule_id": 1, "similarity_level": similarity}]}]}),
            )

    @pytest.mark.asyncio
    async def test_rejects_bool_similarity_level(self):
        with pytest.raises(ToolInputError, match="similarity_level must be one of"):
            await handle_call_tool(
                "update_campaign_lookalike_audience",
                _args(targeting={"collection": [{"type": "INCLUDE", "collection": [{"rule_id": 1, "similarity_level": True}]}]}),
            )

    @pytest.mark.asyncio
    async def test_rejects_null_item(self):
        with pytest.raises(ToolInputError, match=r"\[0\].collection\[0\] must be an object"):
            await handle_call_tool(
                "update_campaign_lookalike_audience",
                _args(targeting={"collection": [{"type": "INCLUDE", "collection": [None]}]}),
            )


class TestLookalikeWire:
    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_posts_to_lookalike_audience_endpoint(self, mock_post):
        mock_post.return_value = {"id": "c-123"}
        await handle_call_tool("update_campaign_lookalike_audience", _args())
        assert _post_endpoint(mock_post) == "/acme-inc/campaigns/c-123/targeting/lookalike_audience"

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_url_encodes_path_segments(self, mock_post):
        mock_post.return_value = {"id": "c-123"}
        await handle_call_tool(
            "update_campaign_lookalike_audience",
            _args(account_id="acme/evil", campaign_id="c/1"),
        )
        assert _post_endpoint(mock_post) == "/acme%2Fevil/campaigns/c%2F1/targeting/lookalike_audience"

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_body_passes_through_unchanged(self, mock_post):
        mock_post.return_value = {"id": "c-123"}
        targeting = {
            "collection": [
                {
                    "type": "INCLUDE",
                    "collection": [
                        {"rule_id": 1234567, "similarity_level": 10},
                        {"rule_id": 7654321, "similarity_level": 5},
                    ],
                }
            ]
        }
        await handle_call_tool(
            "update_campaign_lookalike_audience", _args(targeting=targeting)
        )
        assert _post_body(mock_post) == targeting

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_empty_outer_collection_clears(self, mock_post):
        mock_post.return_value = {"id": "c-123"}
        await handle_call_tool(
            "update_campaign_lookalike_audience",
            _args(targeting={"collection": []}),
        )
        assert _post_body(mock_post) == {"collection": []}

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_empty_block_collection_accepted(self, mock_post):
        mock_post.return_value = {"id": "c-123"}
        targeting = {"collection": [{"type": "INCLUDE", "collection": []}]}
        await handle_call_tool(
            "update_campaign_lookalike_audience", _args(targeting=targeting)
        )
        assert _post_body(mock_post) == targeting

    @pytest.mark.parametrize("similarity", [1, 2, 3, 4, 5])
    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_pbp_similarity_levels_accepted(self, mock_post, similarity):
        mock_post.return_value = {"id": "c-123"}
        targeting = {"collection": [{"type": "INCLUDE", "collection": [{"rule_id": 1, "similarity_level": similarity}]}]}
        await handle_call_tool(
            "update_campaign_lookalike_audience", _args(targeting=targeting)
        )
        assert _post_body(mock_post) == targeting

    @pytest.mark.parametrize("similarity", [5, 10, 15, 20, 25])
    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_crm_similarity_levels_accepted(self, mock_post, similarity):
        mock_post.return_value = {"id": "c-123"}
        targeting = {"collection": [{"type": "INCLUDE", "collection": [{"rule_id": 1, "similarity_level": similarity}]}]}
        await handle_call_tool(
            "update_campaign_lookalike_audience", _args(targeting=targeting)
        )
        assert _post_body(mock_post) == targeting


class TestLookalikeAnnotations:
    @pytest.mark.asyncio
    async def test_has_destructive_idempotent_open_world_annotations(self):
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        tool = next(t for t in tools if t.name == "update_campaign_lookalike_audience")

        assert tool.annotations is not None
        assert tool.annotations.destructiveHint is True
        assert tool.annotations.idempotentHint is True
        assert tool.annotations.openWorldHint is True
