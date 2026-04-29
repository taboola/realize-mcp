"""Tests for the update_campaign_contextual_segments write tool."""
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
        "contextual_segments": {
            "collection": [
                {"type": "INCLUDE", "collection": [1900004, 1900024]}
            ]
        },
    }
    base.update(overrides)
    return base


class TestContextualSegmentsValidation:
    @pytest.mark.asyncio
    async def test_numeric_account_id_rejected(self):
        with pytest.raises(ToolInputError, match="search_accounts"):
            await handle_call_tool(
                "update_campaign_contextual_segments", _args(account_id="12345")
            )

    @pytest.mark.asyncio
    async def test_missing_campaign_id_raises(self):
        args = _args()
        del args["campaign_id"]
        with pytest.raises(ToolInputError, match="campaign_id is required"):
            await handle_call_tool("update_campaign_contextual_segments", args)

    @pytest.mark.asyncio
    async def test_rejects_contextual_segments_missing(self):
        args = _args()
        del args["contextual_segments"]
        with pytest.raises(
            ToolInputError, match="contextual_segments must be an object"
        ):
            await handle_call_tool("update_campaign_contextual_segments", args)

    @pytest.mark.asyncio
    async def test_rejects_contextual_segments_not_dict(self):
        with pytest.raises(
            ToolInputError, match="contextual_segments must be an object"
        ):
            await handle_call_tool(
                "update_campaign_contextual_segments",
                _args(contextual_segments=[]),
            )

    @pytest.mark.asyncio
    async def test_rejects_missing_collection(self):
        with pytest.raises(
            ToolInputError, match=r"contextual_segments.collection must be a list"
        ):
            await handle_call_tool(
                "update_campaign_contextual_segments",
                _args(contextual_segments={}),
            )

    @pytest.mark.asyncio
    async def test_rejects_collection_not_list(self):
        with pytest.raises(
            ToolInputError, match=r"contextual_segments.collection must be a list"
        ):
            await handle_call_tool(
                "update_campaign_contextual_segments",
                _args(contextual_segments={"collection": "INCLUDE"}),
            )

    @pytest.mark.asyncio
    async def test_rejects_rule_not_object(self):
        with pytest.raises(
            ToolInputError,
            match=r"contextual_segments.collection\[0\] must be an object",
        ):
            await handle_call_tool(
                "update_campaign_contextual_segments",
                _args(contextual_segments={"collection": ["INCLUDE"]}),
            )

    @pytest.mark.asyncio
    async def test_rejects_invalid_type(self):
        with pytest.raises(
            ToolInputError,
            match=r"contextual_segments.collection\[0\].type must be one of: INCLUDE, EXCLUDE",
        ):
            await handle_call_tool(
                "update_campaign_contextual_segments",
                _args(
                    contextual_segments={
                        "collection": [{"type": "ALL", "collection": []}]
                    }
                ),
            )

    @pytest.mark.asyncio
    async def test_rejects_duplicate_type(self):
        with pytest.raises(
            ToolInputError,
            match=r"contextual_segments.collection\[1\].type duplicate",
        ):
            await handle_call_tool(
                "update_campaign_contextual_segments",
                _args(
                    contextual_segments={
                        "collection": [
                            {"type": "INCLUDE", "collection": [1]},
                            {"type": "INCLUDE", "collection": [2]},
                        ]
                    }
                ),
            )

    @pytest.mark.asyncio
    async def test_rejects_inner_collection_not_list(self):
        with pytest.raises(
            ToolInputError,
            match=r"contextual_segments.collection\[0\].collection must be a list",
        ):
            await handle_call_tool(
                "update_campaign_contextual_segments",
                _args(
                    contextual_segments={
                        "collection": [{"type": "INCLUDE", "collection": 1900004}]
                    }
                ),
            )

    @pytest.mark.asyncio
    async def test_rejects_non_int_segment_id(self):
        with pytest.raises(
            ToolInputError,
            match=r"contextual_segments.collection\[0\].collection\[1\] must be an integer",
        ):
            await handle_call_tool(
                "update_campaign_contextual_segments",
                _args(
                    contextual_segments={
                        "collection": [
                            {"type": "INCLUDE", "collection": [1900004, "1900024"]}
                        ]
                    }
                ),
            )

    @pytest.mark.asyncio
    async def test_rejects_bool_segment_id(self):
        with pytest.raises(
            ToolInputError,
            match=r"contextual_segments.collection\[0\].collection\[0\] must be an integer",
        ):
            await handle_call_tool(
                "update_campaign_contextual_segments",
                _args(
                    contextual_segments={
                        "collection": [{"type": "INCLUDE", "collection": [True]}]
                    }
                ),
            )

    @pytest.mark.asyncio
    async def test_rejects_duplicate_segment_id(self):
        with pytest.raises(
            ToolInputError,
            match=r"contextual_segments.collection\[0\].collection\[1\] duplicate",
        ):
            await handle_call_tool(
                "update_campaign_contextual_segments",
                _args(
                    contextual_segments={
                        "collection": [
                            {"type": "INCLUDE", "collection": [1900004, 1900004]}
                        ]
                    }
                ),
            )


class TestContextualSegmentsWire:
    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_posts_to_targeting_subendpoint(self, mock_post):
        mock_post.return_value = {"collection": []}

        await handle_call_tool("update_campaign_contextual_segments", _args())

        assert (
            _post_endpoint(mock_post)
            == "/acme-inc/campaigns/c-123/targeting/contextual_segments"
        )

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_url_encodes_path_segments(self, mock_post):
        mock_post.return_value = {"collection": []}

        await handle_call_tool(
            "update_campaign_contextual_segments",
            _args(account_id="acme/evil", campaign_id="c/1"),
        )

        assert (
            _post_endpoint(mock_post)
            == "/acme%2Fevil/campaigns/c%2F1/targeting/contextual_segments"
        )

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_body_passed_through_unchanged(self, mock_post):
        mock_post.return_value = {"collection": []}

        await handle_call_tool("update_campaign_contextual_segments", _args())

        assert _post_body(mock_post) == {
            "collection": [
                {"type": "INCLUDE", "collection": [1900004, 1900024]}
            ]
        }

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_include_plus_exclude_combo(self, mock_post):
        mock_post.return_value = {"collection": []}

        await handle_call_tool(
            "update_campaign_contextual_segments",
            _args(
                contextual_segments={
                    "collection": [
                        {"type": "INCLUDE", "collection": [1900004, 1900024]},
                        {"type": "EXCLUDE", "collection": [1900100]},
                    ]
                }
            ),
        )

        assert _post_body(mock_post) == {
            "collection": [
                {"type": "INCLUDE", "collection": [1900004, 1900024]},
                {"type": "EXCLUDE", "collection": [1900100]},
            ]
        }

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_empty_outer_collection_clears(self, mock_post):
        mock_post.return_value = {"collection": []}

        await handle_call_tool(
            "update_campaign_contextual_segments",
            _args(contextual_segments={"collection": []}),
        )

        assert _post_body(mock_post) == {"collection": []}


class TestContextualSegmentsAnnotations:
    @pytest.mark.asyncio
    async def test_has_destructive_idempotent_open_world_annotations(self):
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        tool = next(
            t for t in tools if t.name == "update_campaign_contextual_segments"
        )

        assert tool.annotations is not None
        assert tool.annotations.destructiveHint is True
        assert tool.annotations.idempotentHint is True
        assert tool.annotations.openWorldHint is True
