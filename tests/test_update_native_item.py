"""Tests for the update_native_item write tool."""
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
        "campaign_id": "49184816",
        "item_id": "987654321",
        "is_active": False,
    }
    base.update(overrides)
    return base


class TestUpdateCampaignItemBaseValidation:
    @pytest.mark.asyncio
    async def test_missing_account_id_raises(self):
        with pytest.raises(ToolInputError, match="account_id is required"):
            await handle_call_tool(
                "update_native_item",
                {"campaign_id": "49184816", "item_id": "987654321", "is_active": False},
            )

    @pytest.mark.asyncio
    async def test_numeric_account_id_rejected(self):
        with pytest.raises(ToolInputError, match="search_accounts"):
            await handle_call_tool("update_native_item", _args(account_id="12345"))

    @pytest.mark.asyncio
    async def test_missing_campaign_id_raises(self):
        args = _args()
        del args["campaign_id"]
        with pytest.raises(ToolInputError, match="campaign_id is required"):
            await handle_call_tool("update_native_item", args)

    @pytest.mark.asyncio
    async def test_missing_item_id_raises(self):
        args = _args()
        del args["item_id"]
        with pytest.raises(ToolInputError, match="item_id is required"):
            await handle_call_tool("update_native_item", args)

    @pytest.mark.asyncio
    async def test_no_updatable_fields_rejected(self):
        with pytest.raises(ToolInputError, match="at least one updatable field"):
            await handle_call_tool(
                "update_native_item",
                {"account_id": "acme-inc", "campaign_id": "49184816", "item_id": "987654321"},
            )

    @pytest.mark.asyncio
    async def test_only_none_values_rejected(self):
        with pytest.raises(ToolInputError, match="at least one updatable field"):
            await handle_call_tool(
                "update_native_item",
                {
                    "account_id": "acme-inc",
                    "campaign_id": "49184816",
                    "item_id": "987654321",
                    "title": None,
                    "description": None,
                },
            )


class TestUpdateCampaignItemWireMapping:
    @pytest.mark.asyncio
    @patch('realize.tools.item_native_handlers.client.post', new_callable=AsyncMock)
    async def test_posts_to_item_endpoint(self, mock_post):
        mock_post.return_value = {"id": "987654321"}
        await handle_call_tool("update_native_item", _args())
        assert _post_endpoint(mock_post) == "/acme-inc/campaigns/49184816/items/987654321"

    @pytest.mark.asyncio
    @patch('realize.tools.item_native_handlers.client.post', new_callable=AsyncMock)
    async def test_url_encodes_path_segments(self, mock_post):
        mock_post.return_value = {"id": "987654321"}
        await handle_call_tool("update_native_item", _args(
            account_id="acme/evil",
            campaign_id="c/1",
            item_id="i/1",
        ))
        assert _post_endpoint(mock_post) == "/acme%2Fevil/campaigns/c%2F1/items/i%2F1"

    @pytest.mark.asyncio
    @patch('realize.tools.item_native_handlers.client.post', new_callable=AsyncMock)
    async def test_path_ids_not_in_body(self, mock_post):
        mock_post.return_value = {"id": "987654321"}
        await handle_call_tool("update_native_item", _args())
        body = _post_body(mock_post)
        assert "account_id" not in body
        assert "campaign_id" not in body
        assert "item_id" not in body

    @pytest.mark.asyncio
    @patch('realize.tools.item_native_handlers.client.post', new_callable=AsyncMock)
    async def test_single_scalar_passes_through(self, mock_post):
        mock_post.return_value = {"id": "987654321"}
        await handle_call_tool("update_native_item", _args())
        assert _post_body(mock_post) == {"is_active": False}

    @pytest.mark.parametrize("field,value", [
        ("url", "https://example.com/new"),
        ("title", "Updated headline"),
        ("description", "Updated body."),
        ("thumbnail_url", "https://cdn.example.com/new.jpg"),
        ("branding_text", "Acme Pro"),
        ("is_active", True),
    ])
    @pytest.mark.asyncio
    @patch('realize.tools.item_native_handlers.client.post', new_callable=AsyncMock)
    async def test_scalar_field_pass_through(self, mock_post, field, value):
        mock_post.return_value = {"id": "987654321"}
        args = {"account_id": "acme-inc", "campaign_id": "49184816", "item_id": "987654321", field: value}
        await handle_call_tool("update_native_item", args)
        assert _post_body(mock_post) == {field: value}

    @pytest.mark.asyncio
    @patch('realize.tools.item_native_handlers.client.post', new_callable=AsyncMock)
    async def test_creative_name_only(self, mock_post):
        mock_post.return_value = {"id": "987654321"}
        await handle_call_tool(
            "update_native_item",
            {
                "account_id": "acme-inc",
                "campaign_id": "49184816",
                "item_id": "987654321",
                "creative_name": "Native renamed",
            },
        )
        assert _post_body(mock_post) == {"custom_data": {"creative_name": "Native renamed"}}

    @pytest.mark.asyncio
    async def test_creative_name_blank_rejected(self):
        with pytest.raises(ToolInputError, match="creative_name must be a non-empty string"):
            await handle_call_tool("update_native_item", _args(creative_name=""))


class TestUpdateCampaignItemNested:
    @pytest.mark.asyncio
    @patch('realize.tools.item_native_handlers.client.post', new_callable=AsyncMock)
    async def test_cta_passes_through(self, mock_post):
        mock_post.return_value = {"id": "987654321"}
        await handle_call_tool(
            "update_native_item",
            _args(cta={"cta_type": "LEARN_MORE"}),
        )
        body = _post_body(mock_post)
        assert body["cta"] == {"cta_type": "LEARN_MORE"}

    @pytest.mark.asyncio
    async def test_cta_invalid_rejected(self):
        with pytest.raises(ToolInputError, match="cta"):
            await handle_call_tool("update_native_item", _args(cta={"cta_type": ""}))

    @pytest.mark.asyncio
    @patch('realize.tools.item_native_handlers.client.post', new_callable=AsyncMock)
    async def test_verification_pixel_full_replace(self, mock_post):
        mock_post.return_value = {"id": "987654321"}
        await handle_call_tool("update_native_item", _args(
            verification_pixel={
                "verification_pixel_items": [
                    {"url": "https://verify.example.com/c", "verification_pixel_type": "CLICK"},
                    {"url": "https://verify.example.com/v", "verification_pixel_type": "VIEWABLE_IMPRESSION"},
                ],
            },
        ))
        body = _post_body(mock_post)
        assert body["verification_pixel"] == {
            "verification_pixel_items": [
                {"url": "https://verify.example.com/c", "verification_pixel_type": "CLICK"},
                {"url": "https://verify.example.com/v", "verification_pixel_type": "VIEWABLE_IMPRESSION"},
            ],
        }

    @pytest.mark.asyncio
    @patch('realize.tools.item_native_handlers.client.post', new_callable=AsyncMock)
    async def test_verification_pixel_empty_clears(self, mock_post):
        mock_post.return_value = {"id": "987654321"}
        await handle_call_tool("update_native_item", _args(
            verification_pixel={"verification_pixel_items": []},
        ))
        body = _post_body(mock_post)
        assert body["verification_pixel"] == {"verification_pixel_items": []}

    @pytest.mark.asyncio
    async def test_verification_pixel_invalid_type_rejected(self):
        with pytest.raises(ToolInputError, match="verification_pixel_type"):
            await handle_call_tool("update_native_item", _args(
                verification_pixel={
                    "verification_pixel_items": [
                        {"url": "https://x.example/", "verification_pixel_type": "BOGUS"},
                    ],
                },
            ))

    @pytest.mark.asyncio
    async def test_verification_pixel_missing_url_rejected(self):
        with pytest.raises(ToolInputError, match="verification_pixel.*url"):
            await handle_call_tool("update_native_item", _args(
                verification_pixel={
                    "verification_pixel_items": [
                        {"verification_pixel_type": "CLICK"},
                    ],
                },
            ))

    @pytest.mark.asyncio
    async def test_verification_pixel_not_object_rejected(self):
        with pytest.raises(ToolInputError, match="verification_pixel must be an object"):
            await handle_call_tool("update_native_item", _args(verification_pixel=[]))

    @pytest.mark.asyncio
    @patch('realize.tools.item_native_handlers.client.post', new_callable=AsyncMock)
    async def test_viewability_tag_full_replace(self, mock_post):
        mock_post.return_value = {"id": "987654321"}
        await handle_call_tool("update_native_item", _args(
            viewability_tag={
                "values": [
                    {"tag": "<script>1</script>", "type": "IAS"},
                    {"tag": "<script>2</script>", "type": "DOUBLE_VERIFY"},
                ],
            },
        ))
        body = _post_body(mock_post)
        assert body["viewability_tag"] == {
            "values": [
                {"tag": "<script>1</script>", "type": "IAS"},
                {"tag": "<script>2</script>", "type": "DOUBLE_VERIFY"},
            ],
        }

    @pytest.mark.asyncio
    @patch('realize.tools.item_native_handlers.client.post', new_callable=AsyncMock)
    async def test_viewability_tag_empty_clears(self, mock_post):
        mock_post.return_value = {"id": "987654321"}
        await handle_call_tool("update_native_item", _args(
            viewability_tag={"values": []},
        ))
        body = _post_body(mock_post)
        assert body["viewability_tag"] == {"values": []}

    @pytest.mark.asyncio
    async def test_viewability_tag_invalid_type_rejected(self):
        with pytest.raises(ToolInputError, match="viewability_tag.*type"):
            await handle_call_tool("update_native_item", _args(
                viewability_tag={"values": [{"tag": "x", "type": "BOGUS"}]},
            ))

    @pytest.mark.asyncio
    async def test_viewability_tag_not_object_rejected(self):
        with pytest.raises(ToolInputError, match="viewability_tag must be an object"):
            await handle_call_tool("update_native_item", _args(viewability_tag=[]))


class TestUpdateCampaignItemMultiField:
    @pytest.mark.asyncio
    @patch('realize.tools.item_native_handlers.client.post', new_callable=AsyncMock)
    async def test_multi_field_update(self, mock_post):
        mock_post.return_value = {"id": "987654321"}
        await handle_call_tool("update_native_item", _args(
            title="New title",
            cta={"cta_type": "READ_MORE"},
            verification_pixel={
                "verification_pixel_items": [
                    {"url": "https://x.example/c", "verification_pixel_type": "CLICK"},
                ],
            },
        ))
        body = _post_body(mock_post)
        assert body["is_active"] is False
        assert body["title"] == "New title"
        assert body["cta"] == {"cta_type": "READ_MORE"}
        assert body["verification_pixel"] == {
            "verification_pixel_items": [
                {"url": "https://x.example/c", "verification_pixel_type": "CLICK"},
            ],
        }


class TestUpdateCampaignItemAnnotations:
    @pytest.mark.asyncio
    async def test_has_destructive_idempotent_annotations(self):
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        update = next(t for t in tools if t.name == "update_native_item")

        assert update.annotations is not None
        assert update.annotations.destructiveHint is True
        assert update.annotations.idempotentHint is True
        assert update.annotations.openWorldHint is True

    @pytest.mark.asyncio
    async def test_required_fields_in_schema(self):
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        update = next(t for t in tools if t.name == "update_native_item")

        assert set(update.inputSchema["required"]) == {"account_id", "campaign_id", "item_id"}
