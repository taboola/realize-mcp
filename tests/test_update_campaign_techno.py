"""Tests for the update_campaign_techno write tool."""
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
        "dimension": "platform",
        "targeting": {"type": "INCLUDE", "value": ["DESK"]},
    }
    base.update(overrides)
    return base


class TestTechnoValidation:
    @pytest.mark.asyncio
    async def test_rejects_unknown_dimension(self):
        with pytest.raises(ToolInputError, match="dimension must be one of"):
            await handle_call_tool("update_campaign_techno", _args(dimension="resolution"))

    @pytest.mark.asyncio
    async def test_rejects_invalid_targeting_type(self):
        with pytest.raises(ToolInputError, match="targeting.type"):
            await handle_call_tool(
                "update_campaign_techno",
                _args(targeting={"type": "ONLY", "value": ["DESK"]}),
            )

    @pytest.mark.asyncio
    async def test_rejects_all_with_nonempty_value(self):
        with pytest.raises(ToolInputError, match="empty when type=ALL"):
            await handle_call_tool(
                "update_campaign_techno",
                _args(targeting={"type": "ALL", "value": ["DESK"]}),
            )

    @pytest.mark.asyncio
    async def test_rejects_include_with_empty_value(self):
        with pytest.raises(ToolInputError, match="non-empty when type=INCLUDE"):
            await handle_call_tool(
                "update_campaign_techno",
                _args(targeting={"type": "INCLUDE", "value": []}),
            )

    @pytest.mark.asyncio
    async def test_value_must_be_list(self):
        with pytest.raises(ToolInputError, match="targeting.value must be a list"):
            await handle_call_tool(
                "update_campaign_techno",
                _args(targeting={"type": "INCLUDE", "value": "DESK"}),
            )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("dim", ["platform", "browser", "connection_type"])
    async def test_string_dim_rejects_object_items(self, dim):
        with pytest.raises(ToolInputError, match="must be a string"):
            await handle_call_tool(
                "update_campaign_techno",
                _args(
                    dimension=dim,
                    targeting={"type": "INCLUDE", "value": [{"os_family": "Android"}]},
                ),
            )

    @pytest.mark.asyncio
    async def test_os_dim_rejects_string_items(self):
        with pytest.raises(ToolInputError, match="must be an object with os_family"):
            await handle_call_tool(
                "update_campaign_techno",
                _args(
                    dimension="os",
                    targeting={"type": "INCLUDE", "value": ["Android"]},
                ),
            )

    @pytest.mark.asyncio
    async def test_os_dim_requires_os_family(self):
        with pytest.raises(ToolInputError, match="os_family must be a string"):
            await handle_call_tool(
                "update_campaign_techno",
                _args(
                    dimension="os",
                    targeting={"type": "INCLUDE", "value": [{"sub_categories": ["iOS_16"]}]},
                ),
            )

    @pytest.mark.asyncio
    async def test_os_dim_sub_categories_must_be_list(self):
        with pytest.raises(ToolInputError, match="sub_categories must be a list"):
            await handle_call_tool(
                "update_campaign_techno",
                _args(
                    dimension="os",
                    targeting={
                        "type": "INCLUDE",
                        "value": [{"os_family": "iOS", "sub_categories": "iOS_16"}],
                    },
                ),
            )

    @pytest.mark.asyncio
    async def test_os_dim_sub_categories_items_must_be_strings(self):
        with pytest.raises(ToolInputError, match="sub_categories\\[0\\] must be a string"):
            await handle_call_tool(
                "update_campaign_techno",
                _args(
                    dimension="os",
                    targeting={
                        "type": "INCLUDE",
                        "value": [{"os_family": "iOS", "sub_categories": [123]}],
                    },
                ),
            )

    @pytest.mark.asyncio
    async def test_missing_campaign_id_raises(self):
        args = _args()
        del args["campaign_id"]
        with pytest.raises(ToolInputError, match="campaign_id is required"):
            await handle_call_tool("update_campaign_techno", args)

    @pytest.mark.asyncio
    async def test_numeric_account_id_rejected(self):
        with pytest.raises(ToolInputError, match="search_accounts"):
            await handle_call_tool("update_campaign_techno", _args(account_id="12345"))


class TestTechnoWireMapping:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("dimension,wire_field,value", [
        ("platform", "platform_targeting", ["DESK"]),
        ("browser", "browser_targeting", ["Chrome"]),
        ("connection_type", "connection_type_targeting", ["WIFI"]),
    ])
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_string_dimension_maps_to_wire_field(self, mock_post, dimension, wire_field, value):
        mock_post.return_value = {"id": "c-123"}

        await handle_call_tool(
            "update_campaign_techno",
            _args(
                dimension=dimension,
                targeting={"type": "INCLUDE", "value": value},
            ),
        )

        body = _post_body(mock_post)
        assert body == {wire_field: {"type": "INCLUDE", "value": value}}

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_os_dimension_maps_to_wire_field(self, mock_post):
        mock_post.return_value = {"id": "c-123"}

        await handle_call_tool(
            "update_campaign_techno",
            _args(
                dimension="os",
                targeting={"type": "INCLUDE", "value": [{"os_family": "Android"}]},
            ),
        )

        body = _post_body(mock_post)
        assert "os_targeting" in body
        assert set(body.keys()) == {"os_targeting"}

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_posts_to_campaign_endpoint(self, mock_post):
        mock_post.return_value = {"id": "c-123"}

        await handle_call_tool("update_campaign_techno", _args())

        assert _post_endpoint(mock_post) == "/acme-inc/campaigns/c-123"

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_url_encodes_path_segments(self, mock_post):
        mock_post.return_value = {"id": "c-123"}

        await handle_call_tool(
            "update_campaign_techno",
            _args(account_id="acme/evil", campaign_id="c/1"),
        )

        assert _post_endpoint(mock_post) == "/acme%2Fevil/campaigns/c%2F1"

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_clear_with_all_sends_empty_value(self, mock_post):
        mock_post.return_value = {"id": "c-123"}

        await handle_call_tool(
            "update_campaign_techno",
            _args(dimension="browser", targeting={"type": "ALL", "value": []}),
        )

        assert _post_body(mock_post) == {"browser_targeting": {"type": "ALL", "value": []}}

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_string_dim_passes_value_unchanged(self, mock_post):
        mock_post.return_value = {"id": "c-123"}

        await handle_call_tool(
            "update_campaign_techno",
            _args(
                dimension="platform",
                targeting={"type": "INCLUDE", "value": ["DESK", "PHON", "TBLT"]},
            ),
        )

        assert _post_body(mock_post) == {
            "platform_targeting": {"type": "INCLUDE", "value": ["DESK", "PHON", "TBLT"]}
        }

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_os_dim_wire_keys(self, mock_post):
        mock_post.return_value = {"id": "c-123"}

        await handle_call_tool(
            "update_campaign_techno",
            _args(
                dimension="os",
                targeting={
                    "type": "INCLUDE",
                    "value": [
                        {"os_family": "Android"},
                        {"os_family": "iOS", "sub_categories": ["iOS_16", "iOS_17"]},
                    ],
                },
            ),
        )

        assert _post_body(mock_post) == {
            "os_targeting": {
                "type": "INCLUDE",
                "value": [
                    {"os_family": "Android"},
                    {"os_family": "iOS", "sub_categories": ["iOS_16", "iOS_17"]},
                ],
            }
        }

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_os_dim_drops_missing_sub_categories(self, mock_post):
        mock_post.return_value = {"id": "c-123"}

        await handle_call_tool(
            "update_campaign_techno",
            _args(
                dimension="os",
                targeting={"type": "INCLUDE", "value": [{"os_family": "Android"}]},
            ),
        )

        assert _post_body(mock_post) == {
            "os_targeting": {"type": "INCLUDE", "value": [{"os_family": "Android"}]}
        }

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_os_dim_drops_empty_sub_categories(self, mock_post):
        mock_post.return_value = {"id": "c-123"}

        await handle_call_tool(
            "update_campaign_techno",
            _args(
                dimension="os",
                targeting={
                    "type": "INCLUDE",
                    "value": [{"os_family": "Android", "sub_categories": []}],
                },
            ),
        )

        assert _post_body(mock_post) == {
            "os_targeting": {"type": "INCLUDE", "value": [{"os_family": "Android"}]}
        }

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_os_dim_preserves_sub_categories_when_set(self, mock_post):
        mock_post.return_value = {"id": "c-123"}

        await handle_call_tool(
            "update_campaign_techno",
            _args(
                dimension="os",
                targeting={
                    "type": "INCLUDE",
                    "value": [{"os_family": "iOS", "sub_categories": ["iOS_8.4", "iOS_9"]}],
                },
            ),
        )

        assert _post_body(mock_post) == {
            "os_targeting": {
                "type": "INCLUDE",
                "value": [{"os_family": "iOS", "sub_categories": ["iOS_8.4", "iOS_9"]}],
            }
        }


class TestTechnoAnnotations:
    @pytest.mark.asyncio
    async def test_has_destructive_idempotent_open_world_annotations(self):
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        tool = next(t for t in tools if t.name == "update_campaign_techno")

        assert tool.annotations is not None
        assert tool.annotations.destructiveHint is True
        assert tool.annotations.idempotentHint is True
        assert tool.annotations.openWorldHint is True
