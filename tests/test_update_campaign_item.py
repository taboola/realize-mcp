"""Tests for the update_campaign_item write tool."""
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
                "update_campaign_item",
                {"campaign_id": "49184816", "item_id": "987654321", "is_active": False},
            )

    @pytest.mark.asyncio
    async def test_numeric_account_id_rejected(self):
        with pytest.raises(ToolInputError, match="search_accounts"):
            await handle_call_tool("update_campaign_item", _args(account_id="12345"))

    @pytest.mark.asyncio
    async def test_missing_campaign_id_raises(self):
        args = _args()
        del args["campaign_id"]
        with pytest.raises(ToolInputError, match="campaign_id is required"):
            await handle_call_tool("update_campaign_item", args)

    @pytest.mark.asyncio
    async def test_missing_item_id_raises(self):
        args = _args()
        del args["item_id"]
        with pytest.raises(ToolInputError, match="item_id is required"):
            await handle_call_tool("update_campaign_item", args)

    @pytest.mark.asyncio
    async def test_no_updatable_fields_rejected(self):
        with pytest.raises(ToolInputError, match="at least one updatable field"):
            await handle_call_tool(
                "update_campaign_item",
                {"account_id": "acme-inc", "campaign_id": "49184816", "item_id": "987654321"},
            )

    @pytest.mark.asyncio
    async def test_only_none_values_rejected(self):
        with pytest.raises(ToolInputError, match="at least one updatable field"):
            await handle_call_tool(
                "update_campaign_item",
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
    @patch('realize.tools.campaign_item_handlers.client.post', new_callable=AsyncMock)
    async def test_posts_to_item_endpoint(self, mock_post):
        mock_post.return_value = {"id": "987654321"}
        await handle_call_tool("update_campaign_item", _args())
        assert _post_endpoint(mock_post) == "/acme-inc/campaigns/49184816/items/987654321"

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_item_handlers.client.post', new_callable=AsyncMock)
    async def test_url_encodes_path_segments(self, mock_post):
        mock_post.return_value = {"id": "987654321"}
        await handle_call_tool("update_campaign_item", _args(
            account_id="acme/evil",
            campaign_id="c/1",
            item_id="i/1",
        ))
        assert _post_endpoint(mock_post) == "/acme%2Fevil/campaigns/c%2F1/items/i%2F1"

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_item_handlers.client.post', new_callable=AsyncMock)
    async def test_path_ids_not_in_body(self, mock_post):
        mock_post.return_value = {"id": "987654321"}
        await handle_call_tool("update_campaign_item", _args())
        body = _post_body(mock_post)
        assert "account_id" not in body
        assert "campaign_id" not in body
        assert "item_id" not in body

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_item_handlers.client.post', new_callable=AsyncMock)
    async def test_single_scalar_passes_through(self, mock_post):
        mock_post.return_value = {"id": "987654321"}
        await handle_call_tool("update_campaign_item", _args())
        assert _post_body(mock_post) == {"is_active": False}

    @pytest.mark.parametrize("field,value", [
        ("url", "https://example.com/new"),
        ("title", "Updated headline"),
        ("description", "Updated body."),
        ("thumbnail_url", "https://cdn.example.com/new.jpg"),
        ("branding_text", "Acme Pro"),
        ("is_active", True),
        ("start_date", "2026-05-01 00:00:00"),
        ("end_date", "2026-06-30 23:59:59"),
    ])
    @pytest.mark.asyncio
    @patch('realize.tools.campaign_item_handlers.client.post', new_callable=AsyncMock)
    async def test_scalar_field_pass_through(self, mock_post, field, value):
        mock_post.return_value = {"id": "987654321"}
        args = {"account_id": "acme-inc", "campaign_id": "49184816", "item_id": "987654321", field: value}
        await handle_call_tool("update_campaign_item", args)
        assert _post_body(mock_post) == {field: value}


class TestUpdateCampaignItemNested:
    @pytest.mark.asyncio
    @patch('realize.tools.campaign_item_handlers.client.post', new_callable=AsyncMock)
    async def test_cta_passes_through(self, mock_post):
        mock_post.return_value = {"id": "987654321"}
        await handle_call_tool(
            "update_campaign_item",
            _args(cta={"cta_type": "LEARN_MORE"}),
        )
        body = _post_body(mock_post)
        assert body["cta"] == {"cta_type": "LEARN_MORE"}

    @pytest.mark.asyncio
    async def test_cta_invalid_rejected(self):
        with pytest.raises(ToolInputError, match="cta"):
            await handle_call_tool("update_campaign_item", _args(cta={"cta_type": ""}))

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_item_handlers.client.post', new_callable=AsyncMock)
    async def test_activity_schedule_validates_and_serializes(self, mock_post):
        mock_post.return_value = {"id": "987654321"}
        await handle_call_tool("update_campaign_item", _args(
            activity_schedule={
                "mode": "CUSTOM",
                "time_zone": "America/New_York",
                "rules": [
                    {"type": "INCLUDE", "day": "MONDAY", "from_hour": 9, "until_hour": 17},
                ],
            },
        ))
        body = _post_body(mock_post)
        assert body["activity_schedule"]["mode"] == "CUSTOM"
        assert body["activity_schedule"]["time_zone"] == "America/New_York"
        assert len(body["activity_schedule"]["rules"]) == 1

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_item_handlers.client.post', new_callable=AsyncMock)
    async def test_verification_pixel_full_replace(self, mock_post):
        mock_post.return_value = {"id": "987654321"}
        await handle_call_tool("update_campaign_item", _args(
            verification_pixel=[
                {"type": "CLICK", "url": "https://verify.example.com/c"},
                {"type": "VIEWABLE_IMPRESSION", "url": "https://verify.example.com/v"},
            ],
        ))
        body = _post_body(mock_post)
        assert body["verification_pixel"] == [
            {"type": "CLICK", "url": "https://verify.example.com/c"},
            {"type": "VIEWABLE_IMPRESSION", "url": "https://verify.example.com/v"},
        ]

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_item_handlers.client.post', new_callable=AsyncMock)
    async def test_verification_pixel_empty_clears(self, mock_post):
        mock_post.return_value = {"id": "987654321"}
        await handle_call_tool("update_campaign_item", _args(verification_pixel=[]))
        body = _post_body(mock_post)
        assert body["verification_pixel"] == []

    @pytest.mark.asyncio
    async def test_verification_pixel_invalid_type_rejected(self):
        with pytest.raises(ToolInputError, match="verification_pixel.*type"):
            await handle_call_tool("update_campaign_item", _args(
                verification_pixel=[{"type": "BOGUS", "url": "https://x.example/"}],
            ))

    @pytest.mark.asyncio
    async def test_verification_pixel_missing_url_rejected(self):
        with pytest.raises(ToolInputError, match="verification_pixel.*url"):
            await handle_call_tool("update_campaign_item", _args(
                verification_pixel=[{"type": "CLICK"}],
            ))

    @pytest.mark.asyncio
    async def test_verification_pixel_not_list_rejected(self):
        with pytest.raises(ToolInputError, match="verification_pixel must be a list"):
            await handle_call_tool("update_campaign_item", _args(verification_pixel={}))

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_item_handlers.client.post', new_callable=AsyncMock)
    async def test_viewability_tag_full_replace(self, mock_post):
        mock_post.return_value = {"id": "987654321"}
        await handle_call_tool("update_campaign_item", _args(
            viewability_tag=[
                {"type": "MOAT", "value": "moat-id-1"},
                {"type": "IAS", "value": "ias-id-2"},
            ],
        ))
        body = _post_body(mock_post)
        assert body["viewability_tag"] == [
            {"type": "MOAT", "value": "moat-id-1"},
            {"type": "IAS", "value": "ias-id-2"},
        ]

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_item_handlers.client.post', new_callable=AsyncMock)
    async def test_viewability_tag_empty_clears(self, mock_post):
        mock_post.return_value = {"id": "987654321"}
        await handle_call_tool("update_campaign_item", _args(viewability_tag=[]))
        body = _post_body(mock_post)
        assert body["viewability_tag"] == []

    @pytest.mark.asyncio
    async def test_viewability_tag_invalid_type_rejected(self):
        with pytest.raises(ToolInputError, match="viewability_tag.*type"):
            await handle_call_tool("update_campaign_item", _args(
                viewability_tag=[{"type": "BOGUS", "value": "x"}],
            ))


class TestUpdateCampaignItemMultiField:
    @pytest.mark.asyncio
    @patch('realize.tools.campaign_item_handlers.client.post', new_callable=AsyncMock)
    async def test_multi_field_update(self, mock_post):
        mock_post.return_value = {"id": "987654321"}
        await handle_call_tool("update_campaign_item", _args(
            title="New title",
            cta={"cta_type": "READ_MORE"},
            verification_pixel=[{"type": "CLICK", "url": "https://x.example/c"}],
        ))
        body = _post_body(mock_post)
        assert body["is_active"] is False
        assert body["title"] == "New title"
        assert body["cta"] == {"cta_type": "READ_MORE"}
        assert body["verification_pixel"] == [{"type": "CLICK", "url": "https://x.example/c"}]


class TestUpdateCampaignItemAnnotations:
    @pytest.mark.asyncio
    async def test_has_destructive_idempotent_annotations(self):
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        update = next(t for t in tools if t.name == "update_campaign_item")

        assert update.annotations is not None
        assert update.annotations.destructiveHint is True
        assert update.annotations.idempotentHint is True
        assert update.annotations.openWorldHint is True

    @pytest.mark.asyncio
    async def test_required_fields_in_schema(self):
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        update = next(t for t in tools if t.name == "update_campaign_item")

        assert set(update.inputSchema["required"]) == {"account_id", "campaign_id", "item_id"}
