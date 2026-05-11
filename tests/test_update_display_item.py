"""Tests for the update_display_item write tool."""
import pytest
from unittest.mock import AsyncMock, patch

from realize.realize_server import handle_call_tool
from realize.tools.errors import ToolInputError


_AD_TAG = '<script src="https://securepubads.g.doubleclick.net/tag/js/gpt.js"></script>'


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


class TestUpdateDisplayItemBaseValidation:
    @pytest.mark.asyncio
    async def test_missing_account_id_raises(self):
        with pytest.raises(ToolInputError, match="account_id is required"):
            await handle_call_tool(
                "update_display_item",
                {"campaign_id": "49184816", "item_id": "987654321", "is_active": False},
            )

    @pytest.mark.asyncio
    async def test_numeric_account_id_rejected(self):
        with pytest.raises(ToolInputError, match="search_accounts"):
            await handle_call_tool("update_display_item", _args(account_id="12345"))

    @pytest.mark.asyncio
    async def test_missing_campaign_id_raises(self):
        args = _args()
        del args["campaign_id"]
        with pytest.raises(ToolInputError, match="campaign_id is required"):
            await handle_call_tool("update_display_item", args)

    @pytest.mark.asyncio
    async def test_missing_item_id_raises(self):
        args = _args()
        del args["item_id"]
        with pytest.raises(ToolInputError, match="item_id is required"):
            await handle_call_tool("update_display_item", args)

    @pytest.mark.asyncio
    async def test_no_updatable_fields_rejected(self):
        with pytest.raises(ToolInputError, match="at least one updatable field"):
            await handle_call_tool(
                "update_display_item",
                {"account_id": "acme-inc", "campaign_id": "49184816", "item_id": "987654321"},
            )


class TestUpdateDisplayItemWireMapping:
    @pytest.mark.asyncio
    @patch('realize.tools.item_display_handlers.client.post', new_callable=AsyncMock)
    async def test_posts_to_item_endpoint(self, mock_post):
        mock_post.return_value = {"id": "987654321"}
        await handle_call_tool("update_display_item", _args())
        assert _post_endpoint(mock_post) == "/acme-inc/campaigns/49184816/items/987654321"

    @pytest.mark.asyncio
    @patch('realize.tools.item_display_handlers.client.post', new_callable=AsyncMock)
    async def test_url_encodes_path_segments(self, mock_post):
        mock_post.return_value = {"id": "987654321"}
        await handle_call_tool("update_display_item", _args(
            account_id="acme/evil",
            campaign_id="c/1",
            item_id="i/1",
        ))
        assert _post_endpoint(mock_post) == "/acme%2Fevil/campaigns/c%2F1/items/i%2F1"

    @pytest.mark.asyncio
    @patch('realize.tools.item_display_handlers.client.post', new_callable=AsyncMock)
    async def test_path_ids_not_in_body(self, mock_post):
        mock_post.return_value = {"id": "987654321"}
        await handle_call_tool("update_display_item", _args())
        body = _post_body(mock_post)
        assert "account_id" not in body
        assert "campaign_id" not in body
        assert "item_id" not in body

    @pytest.mark.asyncio
    @patch('realize.tools.item_display_handlers.client.post', new_callable=AsyncMock)
    async def test_is_active_only(self, mock_post):
        mock_post.return_value = {"id": "987654321"}
        await handle_call_tool("update_display_item", _args())
        assert _post_body(mock_post) == {"is_active": False}

    @pytest.mark.asyncio
    @patch('realize.tools.item_display_handlers.client.post', new_callable=AsyncMock)
    async def test_creative_type_and_display_ad_type_never_sent(self, mock_post):
        """update_display_item must never set creative_type or display_data.display_ad_type."""
        mock_post.return_value = {"id": "987654321"}
        await handle_call_tool("update_display_item", _args(ad_tag=_AD_TAG))
        body = _post_body(mock_post)
        assert "creative_type" not in body
        assert "display_ad_type" not in body.get("display_data", {})


class TestUpdateDisplayItemDisplayDataPartialMerge:
    @pytest.mark.asyncio
    @patch('realize.tools.item_display_handlers.client.post', new_callable=AsyncMock)
    async def test_ad_tag_only(self, mock_post):
        """Sending ad_tag without dimensions emits display_data with just ad_tag."""
        mock_post.return_value = {"id": "987654321"}
        await handle_call_tool(
            "update_display_item",
            {
                "account_id": "acme-inc",
                "campaign_id": "49184816",
                "item_id": "987654321",
                "ad_tag": _AD_TAG,
            },
        )
        body = _post_body(mock_post)
        assert body == {"display_data": {"ad_tag": _AD_TAG}}

    @pytest.mark.asyncio
    @patch('realize.tools.item_display_handlers.client.post', new_callable=AsyncMock)
    async def test_dimensions_only(self, mock_post):
        """Sending dimensions without ad_tag emits display_data with just dimensions."""
        mock_post.return_value = {"id": "987654321"}
        await handle_call_tool(
            "update_display_item",
            {
                "account_id": "acme-inc",
                "campaign_id": "49184816",
                "item_id": "987654321",
                "dimensions": [{"width": 300, "height": 250}],
            },
        )
        body = _post_body(mock_post)
        assert body == {"display_data": {"dimensions": [{"width": 300, "height": 250}]}}

    @pytest.mark.asyncio
    @patch('realize.tools.item_display_handlers.client.post', new_callable=AsyncMock)
    async def test_ad_tag_and_dimensions_together(self, mock_post):
        mock_post.return_value = {"id": "987654321"}
        await handle_call_tool("update_display_item", _args(
            ad_tag=_AD_TAG,
            dimensions=[{"width": 728, "height": 90}],
        ))
        body = _post_body(mock_post)
        assert body["display_data"] == {
            "ad_tag": _AD_TAG,
            "dimensions": [{"width": 728, "height": 90}],
        }

    @pytest.mark.asyncio
    async def test_dimensions_multi_entry_rejected(self):
        with pytest.raises(ToolInputError, match="exactly one"):
            await handle_call_tool("update_display_item", _args(
                dimensions=[
                    {"width": 300, "height": 250},
                    {"width": 728, "height": 90},
                ],
            ))

    @pytest.mark.asyncio
    async def test_ad_tag_invalid_type_rejected(self):
        with pytest.raises(ToolInputError, match="ad_tag must be a string"):
            await handle_call_tool("update_display_item", _args(ad_tag=123))

    @pytest.mark.asyncio
    async def test_dimension_invalid_rejected(self):
        with pytest.raises(ToolInputError, match=r"dimensions\[0\]\.width"):
            await handle_call_tool("update_display_item", _args(
                dimensions=[{"height": 250}],
            ))

    @pytest.mark.parametrize("field,value", [
        ("url", "https://example.com/new"),
        ("is_active", True),
    ])
    @pytest.mark.asyncio
    @patch('realize.tools.item_display_handlers.client.post', new_callable=AsyncMock)
    async def test_scalar_field_pass_through(self, mock_post, field, value):
        mock_post.return_value = {"id": "987654321"}
        args = {"account_id": "acme-inc", "campaign_id": "49184816", "item_id": "987654321", field: value}
        await handle_call_tool("update_display_item", args)
        assert _post_body(mock_post) == {field: value}

    @pytest.mark.asyncio
    @patch('realize.tools.item_display_handlers.client.post', new_callable=AsyncMock)
    async def test_branding_and_cta_dropped_for_display(self, mock_post):
        """Display creatives don't support branding_text or cta — args silently dropped."""
        mock_post.return_value = {"id": "987654321"}
        await handle_call_tool("update_display_item", _args(
            branding_text="Acme",
            cta={"cta_type": "LEARN_MORE"},
        ))
        body = _post_body(mock_post)
        assert "branding_text" not in body
        assert "cta" not in body

    @pytest.mark.asyncio
    @patch('realize.tools.item_display_handlers.client.post', new_callable=AsyncMock)
    async def test_creative_name_only(self, mock_post):
        """Sending only creative_name emits a custom_data block, no display_data."""
        mock_post.return_value = {"id": "987654321"}
        await handle_call_tool(
            "update_display_item",
            {
                "account_id": "acme-inc",
                "campaign_id": "49184816",
                "item_id": "987654321",
                "creative_name": "Acme 300x250 — renamed",
            },
        )
        body = _post_body(mock_post)
        assert body == {"custom_data": {"creative_name": "Acme 300x250 — renamed"}}

    @pytest.mark.asyncio
    async def test_creative_name_blank_rejected(self):
        with pytest.raises(ToolInputError, match="creative_name must be a non-empty string"):
            await handle_call_tool("update_display_item", _args(creative_name=""))

    @pytest.mark.asyncio
    async def test_creative_name_invalid_type_rejected(self):
        with pytest.raises(ToolInputError, match="creative_name must be a string"):
            await handle_call_tool("update_display_item", _args(creative_name=42))


class TestUpdateDisplayItemHostedAssetUrl:
    """1P mode on update: asset_url replaces the hosted asset; subtype is re-detected."""

    @pytest.mark.asyncio
    @patch('realize.tools.item_display_handlers.client.post', new_callable=AsyncMock)
    async def test_asset_url_only(self, mock_post):
        mock_post.return_value = {"id": "987654321"}
        await handle_call_tool(
            "update_display_item",
            {
                "account_id": "acme-inc",
                "campaign_id": "49184816",
                "item_id": "987654321",
                "asset_url": "https://cdn.example.com/creatives/banner-v2.png",
            },
        )
        body = _post_body(mock_post)
        assert body == {
            "display_data": {
                "hosted_display_data": {
                    "asset_url": "https://cdn.example.com/creatives/banner-v2.png",
                },
            },
        }

    @pytest.mark.asyncio
    async def test_asset_url_with_ad_tag_rejected(self):
        with pytest.raises(ToolInputError, match="mutually exclusive"):
            await handle_call_tool("update_display_item", _args(
                ad_tag=_AD_TAG,
                asset_url="https://cdn.example.com/banner.png",
            ))

    @pytest.mark.asyncio
    async def test_asset_url_with_dimensions_rejected(self):
        with pytest.raises(ToolInputError, match="dimensions is not accepted with asset_url"):
            await handle_call_tool("update_display_item", _args(
                asset_url="https://cdn.example.com/banner.png",
                dimensions=[{"width": 300, "height": 250}],
            ))

    @pytest.mark.asyncio
    async def test_asset_url_http_rejected(self):
        with pytest.raises(ToolInputError, match="asset_url must be an https URL"):
            await handle_call_tool("update_display_item", _args(
                asset_url="http://cdn.example.com/banner.png",
            ))


class TestUpdateDisplayItemNested:
    @pytest.mark.asyncio
    @patch('realize.tools.item_display_handlers.client.post', new_callable=AsyncMock)
    async def test_verification_pixel_full_replace(self, mock_post):
        mock_post.return_value = {"id": "987654321"}
        await handle_call_tool("update_display_item", _args(
            verification_pixel={
                "verification_pixel_items": [
                    {"url": "https://verify.example.com/c", "verification_pixel_type": "CLICK"},
                ],
            },
        ))
        body = _post_body(mock_post)
        assert body["verification_pixel"] == {
            "verification_pixel_items": [
                {"url": "https://verify.example.com/c", "verification_pixel_type": "CLICK"},
            ],
        }

    @pytest.mark.asyncio
    @patch('realize.tools.item_display_handlers.client.post', new_callable=AsyncMock)
    async def test_verification_pixel_empty_clears(self, mock_post):
        mock_post.return_value = {"id": "987654321"}
        await handle_call_tool("update_display_item", _args(
            verification_pixel={"verification_pixel_items": []},
        ))
        body = _post_body(mock_post)
        assert body["verification_pixel"] == {"verification_pixel_items": []}

    @pytest.mark.asyncio
    @patch('realize.tools.item_display_handlers.client.post', new_callable=AsyncMock)
    async def test_viewability_tag_full_replace(self, mock_post):
        mock_post.return_value = {"id": "987654321"}
        await handle_call_tool("update_display_item", _args(
            viewability_tag={
                "values": [
                    {"tag": "<script>1</script>", "type": "IAS"},
                ],
            },
        ))
        body = _post_body(mock_post)
        assert body["viewability_tag"] == {
            "values": [{"tag": "<script>1</script>", "type": "IAS"}],
        }

    @pytest.mark.asyncio
    @patch('realize.tools.item_display_handlers.client.post', new_callable=AsyncMock)
    async def test_viewability_tag_empty_clears(self, mock_post):
        mock_post.return_value = {"id": "987654321"}
        await handle_call_tool("update_display_item", _args(
            viewability_tag={"values": []},
        ))
        body = _post_body(mock_post)
        assert body["viewability_tag"] == {"values": []}


class TestUpdateDisplayItemMultiField:
    @pytest.mark.asyncio
    @patch('realize.tools.item_display_handlers.client.post', new_callable=AsyncMock)
    async def test_multi_field_update(self, mock_post):
        mock_post.return_value = {"id": "987654321"}
        await handle_call_tool("update_display_item", _args(
            url="https://example.com/landing-v2",
            ad_tag=_AD_TAG,
            dimensions=[{"width": 300, "height": 250}],
            verification_pixel={
                "verification_pixel_items": [
                    {"url": "https://x.example/c", "verification_pixel_type": "CLICK"},
                ],
            },
        ))
        body = _post_body(mock_post)
        assert body["is_active"] is False
        assert body["url"] == "https://example.com/landing-v2"
        assert body["display_data"] == {
            "ad_tag": _AD_TAG,
            "dimensions": [{"width": 300, "height": 250}],
        }
        assert body["verification_pixel"] == {
            "verification_pixel_items": [
                {"url": "https://x.example/c", "verification_pixel_type": "CLICK"},
            ],
        }


class TestUpdateDisplayItemAnnotations:
    @pytest.mark.asyncio
    async def test_has_destructive_idempotent_annotations(self):
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        update = next(t for t in tools if t.name == "update_display_item")

        assert update.annotations is not None
        assert update.annotations.destructiveHint is True
        assert update.annotations.idempotentHint is True
        assert update.annotations.openWorldHint is True

    @pytest.mark.asyncio
    async def test_required_fields_in_schema(self):
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        update = next(t for t in tools if t.name == "update_display_item")

        assert set(update.inputSchema["required"]) == {"account_id", "campaign_id", "item_id"}

    @pytest.mark.asyncio
    async def test_asset_url_in_update_schema(self):
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        update = next(t for t in tools if t.name == "update_display_item")

        assert "asset_url" in update.inputSchema["properties"]
        assert "ad_tag" in update.inputSchema["properties"]

    @pytest.mark.asyncio
    async def test_native_only_fields_absent(self):
        """Native-specific scalars don't apply to display items."""
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        update = next(t for t in tools if t.name == "update_display_item")

        for f in ("title", "description", "thumbnail_url"):
            assert f not in update.inputSchema["properties"], \
                f"update_display_item must not expose {f} (native-only field)"
