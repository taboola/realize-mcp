"""Tests for the create_campaign_item write tool."""
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
        "url": "https://example.com/landing",
    }
    base.update(overrides)
    return base


class TestCreateCampaignItemHappyPath:
    @pytest.mark.asyncio
    @patch('realize.tools.campaign_item_handlers.client.post', new_callable=AsyncMock)
    async def test_minimal_url_only(self, mock_post):
        mock_post.return_value = {"id": "987654321", "status": "CRAWLING"}

        result = await handle_call_tool("create_campaign_item", _args())

        assert _post_endpoint(mock_post) == "/acme-inc/campaigns/49184816/items"
        body = _post_body(mock_post)
        assert body == {"url": "https://example.com/landing"}
        assert "account_id" not in body
        assert "campaign_id" not in body
        assert "987654321" in result[0].text

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_item_handlers.client.post', new_callable=AsyncMock)
    async def test_full_create_payload(self, mock_post):
        mock_post.return_value = {"id": "987654321"}

        await handle_call_tool("create_campaign_item", _args(
            title="Save 20% This Spring",
            description="Limited-time offer.",
            thumbnail_url="https://cdn.example.com/spring.jpg",
            branding_text="Acme",
            cta={"cta_type": "SHOP_NOW"},
            is_active=True,
        ))

        body = _post_body(mock_post)
        assert body["url"] == "https://example.com/landing"
        assert body["title"] == "Save 20% This Spring"
        assert body["description"] == "Limited-time offer."
        assert body["thumbnail_url"] == "https://cdn.example.com/spring.jpg"
        assert body["branding_text"] == "Acme"
        assert body["cta"] == {"cta_type": "SHOP_NOW"}
        assert body["is_active"] is True

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_item_handlers.client.post', new_callable=AsyncMock)
    async def test_unknown_args_dropped(self, mock_post):
        mock_post.return_value = {"id": "987654321"}

        await handle_call_tool("create_campaign_item", _args(extra_unknown="dropped"))

        body = _post_body(mock_post)
        assert "extra_unknown" not in body


class TestCreateCampaignItemValidation:
    @pytest.mark.asyncio
    async def test_missing_account_id_raises(self):
        with pytest.raises(ToolInputError, match="account_id is required"):
            await handle_call_tool(
                "create_campaign_item",
                {"campaign_id": "49184816", "url": "https://example.com"},
            )

    @pytest.mark.asyncio
    async def test_numeric_account_id_rejected(self):
        with pytest.raises(ToolInputError, match="search_accounts"):
            await handle_call_tool("create_campaign_item", _args(account_id="12345"))

    @pytest.mark.asyncio
    async def test_missing_campaign_id_raises(self):
        args = _args()
        del args["campaign_id"]
        with pytest.raises(ToolInputError, match="campaign_id is required"):
            await handle_call_tool("create_campaign_item", args)

    @pytest.mark.asyncio
    async def test_missing_url_raises(self):
        args = _args()
        del args["url"]
        with pytest.raises(ToolInputError, match="Missing required field.*url"):
            await handle_call_tool("create_campaign_item", args)

    @pytest.mark.asyncio
    async def test_cta_not_object_raises(self):
        with pytest.raises(ToolInputError, match="cta must be an object"):
            await handle_call_tool("create_campaign_item", _args(cta="SHOP_NOW"))

    @pytest.mark.asyncio
    async def test_cta_missing_cta_type_raises(self):
        with pytest.raises(ToolInputError, match="cta.cta_type"):
            await handle_call_tool("create_campaign_item", _args(cta={}))

    @pytest.mark.asyncio
    async def test_cta_empty_cta_type_raises(self):
        with pytest.raises(ToolInputError, match="cta.cta_type"):
            await handle_call_tool("create_campaign_item", _args(cta={"cta_type": ""}))


class TestCreateCampaignItemEncoding:
    @pytest.mark.asyncio
    @patch('realize.tools.campaign_item_handlers.client.post', new_callable=AsyncMock)
    async def test_url_encodes_account_id_and_campaign_id(self, mock_post):
        mock_post.return_value = {"id": "987654321"}

        await handle_call_tool("create_campaign_item", _args(
            account_id="acme/evil", campaign_id="c/1",
        ))

        assert _post_endpoint(mock_post) == "/acme%2Fevil/campaigns/c%2F1/items"


class TestCreateCampaignItemAnnotations:
    @pytest.mark.asyncio
    async def test_has_destructive_annotations(self):
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        create = next(t for t in tools if t.name == "create_campaign_item")

        assert create.annotations is not None
        assert create.annotations.destructiveHint is True
        assert create.annotations.idempotentHint is False
        assert create.annotations.openWorldHint is True

    @pytest.mark.asyncio
    async def test_required_fields_in_schema(self):
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        create = next(t for t in tools if t.name == "create_campaign_item")

        assert set(create.inputSchema["required"]) == {"account_id", "campaign_id", "url"}

    @pytest.mark.asyncio
    async def test_optional_scalars_not_required(self):
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        create = next(t for t in tools if t.name == "create_campaign_item")

        for f in ("title", "description", "thumbnail_url", "is_active", "branding_text", "cta"):
            assert f in create.inputSchema["properties"]
            assert f not in create.inputSchema["required"]

    @pytest.mark.asyncio
    async def test_update_only_fields_not_in_create_schema(self):
        """Update-only fields should not appear in the create surface."""
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        create = next(t for t in tools if t.name == "create_campaign_item")

        for f in ("start_date", "end_date", "activity_schedule", "verification_pixel", "viewability_tag"):
            assert f not in create.inputSchema["properties"], \
                f"create_campaign_item must not expose {f} (update-only field)"


class TestCreateCampaignItemUpdateOnlyFieldsStripped:
    """Even if a caller passes update-only fields, the create handler must drop them."""

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_item_handlers.client.post', new_callable=AsyncMock)
    async def test_start_end_date_dropped_on_create(self, mock_post):
        mock_post.return_value = {"id": "987654321"}

        await handle_call_tool("create_campaign_item", _args(
            start_date="2026-05-01 00:00:00",
            end_date="2026-06-30 23:59:59",
        ))

        body = _post_body(mock_post)
        assert "start_date" not in body
        assert "end_date" not in body

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_item_handlers.client.post', new_callable=AsyncMock)
    async def test_activity_schedule_dropped_on_create(self, mock_post):
        mock_post.return_value = {"id": "987654321"}

        await handle_call_tool("create_campaign_item", _args(
            activity_schedule={"mode": "ALWAYS"},
        ))

        body = _post_body(mock_post)
        assert "activity_schedule" not in body

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_item_handlers.client.post', new_callable=AsyncMock)
    async def test_verification_pixel_dropped_on_create(self, mock_post):
        mock_post.return_value = {"id": "987654321"}

        await handle_call_tool("create_campaign_item", _args(
            verification_pixel=[{"type": "CLICK", "url": "https://x.example/c"}],
        ))

        body = _post_body(mock_post)
        assert "verification_pixel" not in body

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_item_handlers.client.post', new_callable=AsyncMock)
    async def test_viewability_tag_dropped_on_create(self, mock_post):
        mock_post.return_value = {"id": "987654321"}

        await handle_call_tool("create_campaign_item", _args(
            viewability_tag=[{"type": "MOAT", "value": "x"}],
        ))

        body = _post_body(mock_post)
        assert "viewability_tag" not in body
