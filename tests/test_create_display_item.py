"""Tests for the create_display_item write tool."""
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


def _post_item(mock_post):
    """Unwrap the single-item collection wrapper around the create payload."""
    return _post_body(mock_post)["collection"][0]


def _args(**overrides):
    base = {
        "account_id": "acme-inc",
        "campaign_id": "49184816",
        "url": "https://example.com/landing",
        "ad_tag": _AD_TAG,
        "dimensions": [{"width": 300, "height": 250}],
    }
    base.update(overrides)
    return base


class TestCreateDisplayItemHappyPath:
    @pytest.mark.asyncio
    @patch('realize.tools.item_display_handlers.client.post', new_callable=AsyncMock)
    async def test_minimal_payload(self, mock_post):
        mock_post.return_value = {"results": [{"id": "987654321", "status": "PENDING_APPROVAL"}]}

        result = await handle_call_tool("create_display_item", _args())

        assert _post_endpoint(mock_post) == "/acme-inc/campaigns/49184816/items/mass"
        item = _post_item(mock_post)
        assert item["url"] == "https://example.com/landing"
        assert item["creative_type"] == "DISPLAY"
        assert item["display_data"] == {
            "display_ad_type": "THIRD_PARTY_TAG",
            "ad_tag": _AD_TAG,
            "dimensions": [{"width": 300, "height": 250}],
        }
        assert "account_id" not in item
        assert "campaign_id" not in item
        assert "987654321" in result[0].text

    @pytest.mark.asyncio
    @patch('realize.tools.item_display_handlers.client.post', new_callable=AsyncMock)
    async def test_with_branding_and_cta(self, mock_post):
        mock_post.return_value = {"results": [{"id": "987654321"}]}

        await handle_call_tool("create_display_item", _args(
            dimensions=[{"width": 728, "height": 90}],
            branding_text="Acme",
            cta={"cta_type": "LEARN_MORE"},
        ))

        item = _post_item(mock_post)
        assert item["branding_text"] == "Acme"
        assert item["cta"] == {"cta_type": "LEARN_MORE"}
        assert item["display_data"]["dimensions"] == [{"width": 728, "height": 90}]

    @pytest.mark.asyncio
    @patch('realize.tools.item_display_handlers.client.post', new_callable=AsyncMock)
    async def test_unknown_args_dropped(self, mock_post):
        mock_post.return_value = {"results": [{"id": "987654321"}]}

        await handle_call_tool("create_display_item", _args(extra_unknown="dropped"))

        item = _post_item(mock_post)
        assert "extra_unknown" not in item

    @pytest.mark.asyncio
    @patch('realize.tools.item_display_handlers.client.post', new_callable=AsyncMock)
    async def test_dimension_extra_keys_stripped(self, mock_post):
        mock_post.return_value = {"results": [{"id": "987654321"}]}

        await handle_call_tool("create_display_item", _args(
            dimensions=[{"width": 300, "height": 250, "rogue": "drop"}],
        ))

        item = _post_item(mock_post)
        assert item["display_data"]["dimensions"] == [{"width": 300, "height": 250}]


class TestCreateDisplayItemValidation:
    @pytest.mark.asyncio
    async def test_missing_account_id_raises(self):
        with pytest.raises(ToolInputError, match="account_id is required"):
            await handle_call_tool(
                "create_display_item",
                {
                    "campaign_id": "49184816",
                    "url": "https://example.com",
                    "ad_tag": _AD_TAG,
                    "dimensions": [{"width": 300, "height": 250}],
                },
            )

    @pytest.mark.asyncio
    async def test_numeric_account_id_rejected(self):
        with pytest.raises(ToolInputError, match="search_accounts"):
            await handle_call_tool("create_display_item", _args(account_id="12345"))

    @pytest.mark.asyncio
    async def test_missing_campaign_id_raises(self):
        args = _args()
        del args["campaign_id"]
        with pytest.raises(ToolInputError, match="campaign_id is required"):
            await handle_call_tool("create_display_item", args)

    @pytest.mark.asyncio
    async def test_missing_url_raises(self):
        args = _args()
        del args["url"]
        with pytest.raises(ToolInputError, match="Missing required field.*url"):
            await handle_call_tool("create_display_item", args)

    @pytest.mark.asyncio
    async def test_missing_ad_tag_raises(self):
        args = _args()
        del args["ad_tag"]
        with pytest.raises(ToolInputError, match="Missing required field.*ad_tag"):
            await handle_call_tool("create_display_item", args)

    @pytest.mark.asyncio
    async def test_missing_dimensions_raises(self):
        args = _args()
        del args["dimensions"]
        with pytest.raises(ToolInputError, match="Missing required field.*dimensions"):
            await handle_call_tool("create_display_item", args)

    @pytest.mark.asyncio
    async def test_ad_tag_must_be_string(self):
        with pytest.raises(ToolInputError, match="ad_tag must be a string"):
            await handle_call_tool("create_display_item", _args(ad_tag=12345))

    @pytest.mark.asyncio
    async def test_ad_tag_blank_rejected(self):
        with pytest.raises(ToolInputError, match="Missing required field.*ad_tag"):
            await handle_call_tool("create_display_item", _args(ad_tag=""))

    @pytest.mark.asyncio
    async def test_ad_tag_oversized_rejected(self):
        oversized = "<script>" + ("a" * (16 * 1024)) + "</script>"
        with pytest.raises(ToolInputError, match="ad_tag exceeds"):
            await handle_call_tool("create_display_item", _args(ad_tag=oversized))

    @pytest.mark.asyncio
    async def test_dimensions_not_a_list_rejected(self):
        with pytest.raises(ToolInputError, match="dimensions must be a non-empty array"):
            await handle_call_tool("create_display_item", _args(
                dimensions={"width": 300, "height": 250},
            ))

    @pytest.mark.asyncio
    async def test_dimensions_empty_rejected(self):
        with pytest.raises(ToolInputError, match="Missing required field.*dimensions"):
            await handle_call_tool("create_display_item", _args(dimensions=[]))

    @pytest.mark.asyncio
    async def test_dimensions_multi_entry_rejected(self):
        with pytest.raises(ToolInputError, match="exactly one"):
            await handle_call_tool("create_display_item", _args(
                dimensions=[
                    {"width": 300, "height": 250},
                    {"width": 728, "height": 90},
                ],
            ))

    @pytest.mark.asyncio
    async def test_dimension_missing_width_rejected(self):
        with pytest.raises(ToolInputError, match=r"dimensions\[0\]\.width"):
            await handle_call_tool("create_display_item", _args(
                dimensions=[{"height": 250}],
            ))

    @pytest.mark.asyncio
    async def test_dimension_zero_rejected(self):
        with pytest.raises(ToolInputError, match=r"dimensions\[0\]\.height.*positive integer"):
            await handle_call_tool("create_display_item", _args(
                dimensions=[{"width": 300, "height": 0}],
            ))

    @pytest.mark.asyncio
    async def test_dimension_string_rejected(self):
        with pytest.raises(ToolInputError, match=r"dimensions\[0\]\.width.*positive integer"):
            await handle_call_tool("create_display_item", _args(
                dimensions=[{"width": "300", "height": 250}],
            ))

    @pytest.mark.asyncio
    async def test_cta_invalid_rejected(self):
        with pytest.raises(ToolInputError, match="cta"):
            await handle_call_tool("create_display_item", _args(cta={"cta_type": ""}))


class TestCreateDisplayItemEncoding:
    @pytest.mark.asyncio
    @patch('realize.tools.item_display_handlers.client.post', new_callable=AsyncMock)
    async def test_url_encodes_account_id_and_campaign_id(self, mock_post):
        mock_post.return_value = {"results": [{"id": "987654321"}]}

        await handle_call_tool("create_display_item", _args(
            account_id="acme/evil", campaign_id="c/1",
        ))

        assert _post_endpoint(mock_post) == "/acme%2Fevil/campaigns/c%2F1/items/mass"


class TestCreateDisplayItemAnnotations:
    @pytest.mark.asyncio
    async def test_has_destructive_annotations(self):
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        create = next(t for t in tools if t.name == "create_display_item")

        assert create.annotations is not None
        assert create.annotations.destructiveHint is True
        assert create.annotations.idempotentHint is False
        assert create.annotations.openWorldHint is True

    @pytest.mark.asyncio
    async def test_required_fields_in_schema(self):
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        create = next(t for t in tools if t.name == "create_display_item")

        assert set(create.inputSchema["required"]) == {
            "account_id", "campaign_id", "url", "ad_tag", "dimensions",
        }

    @pytest.mark.asyncio
    async def test_update_only_fields_not_in_create_schema(self):
        """Update-only fields should not appear in the create surface."""
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        create = next(t for t in tools if t.name == "create_display_item")

        for f in ("is_active", "verification_pixel", "viewability_tag"):
            assert f not in create.inputSchema["properties"], \
                f"create_display_item must not expose {f} (update-only field)"

    @pytest.mark.asyncio
    async def test_native_only_fields_absent(self):
        """Native-specific scalars don't apply to display items."""
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        create = next(t for t in tools if t.name == "create_display_item")

        for f in ("title", "description", "thumbnail_url"):
            assert f not in create.inputSchema["properties"], \
                f"create_display_item must not expose {f} (native-only field)"


class TestCreateDisplayItemUpdateOnlyFieldsStripped:
    """Even if a caller passes update-only fields, the create handler must drop them."""

    @pytest.mark.asyncio
    @patch('realize.tools.item_display_handlers.client.post', new_callable=AsyncMock)
    async def test_is_active_dropped_on_create(self, mock_post):
        mock_post.return_value = {"results": [{"id": "987654321"}]}

        await handle_call_tool("create_display_item", _args(is_active=False))

        item = _post_item(mock_post)
        assert "is_active" not in item

    @pytest.mark.asyncio
    @patch('realize.tools.item_display_handlers.client.post', new_callable=AsyncMock)
    async def test_verification_pixel_dropped_on_create(self, mock_post):
        mock_post.return_value = {"results": [{"id": "987654321"}]}

        await handle_call_tool("create_display_item", _args(
            verification_pixel={
                "verification_pixel_items": [
                    {"url": "https://x.example/c", "verification_pixel_type": "CLICK"},
                ],
            },
        ))

        item = _post_item(mock_post)
        assert "verification_pixel" not in item

    @pytest.mark.asyncio
    @patch('realize.tools.item_display_handlers.client.post', new_callable=AsyncMock)
    async def test_viewability_tag_dropped_on_create(self, mock_post):
        mock_post.return_value = {"results": [{"id": "987654321"}]}

        await handle_call_tool("create_display_item", _args(
            viewability_tag={"values": [{"tag": "<script/>", "type": "IAS"}]},
        ))

        item = _post_item(mock_post)
        assert "viewability_tag" not in item
