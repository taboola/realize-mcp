"""Tests for the create_campaign write tool."""
import pytest
from unittest.mock import AsyncMock, patch

from realize.realize_server import handle_call_tool
from realize.tools.errors import ToolInputError


def _post_endpoint_arg(mock_post):
    args, kwargs = mock_post.call_args
    return args[0] if args else kwargs.get("endpoint")


def _post_body(mock_post):
    _args, kwargs = mock_post.call_args
    return kwargs.get("data")


def _minimal_args(**overrides):
    base = {
        "account_id": "acme-inc",
        "name": "Spring Promo",
        "branding_text": "Acme",
        "spending_limit_model": "ENTIRE",
        "marketing_objective": "DRIVE_WEBSITE_TRAFFIC",
    }
    base.update(overrides)
    return base


class TestCreateCampaignHappyPath:
    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_happy_path_sends_required_fields(self, mock_post):
        mock_post.return_value = {"id": "c-123", "status": "PAUSED"}

        result = await handle_call_tool("create_campaign", _minimal_args(
            cpc=0.5, spending_limit=1000.0,
        ))

        assert _post_endpoint_arg(mock_post) == "/acme-inc/campaigns"
        body = _post_body(mock_post)
        assert body["name"] == "Spring Promo"
        assert body["branding_text"] == "Acme"
        assert body["spending_limit_model"] == "ENTIRE"
        assert body["marketing_objective"] == "DRIVE_WEBSITE_TRAFFIC"
        assert body["cpc"] == 0.5
        assert body["spending_limit"] == 1000.0
        assert "account_id" not in body
        assert "c-123" in result[0].text

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_includes_optional_bid_strategy(self, mock_post):
        mock_post.return_value = {"id": "c-1"}

        await handle_call_tool("create_campaign", _minimal_args(bid_strategy="MAX_CONVERSIONS"))

        assert _post_body(mock_post)["bid_strategy"] == "MAX_CONVERSIONS"

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_includes_optional_cpa_goal(self, mock_post):
        mock_post.return_value = {"id": "c-1"}

        await handle_call_tool("create_campaign", _minimal_args(
            bid_strategy="TARGET_CPA",
            cpa_goal=5.0,
        ))

        body = _post_body(mock_post)
        assert body["bid_strategy"] == "TARGET_CPA"
        assert body["cpa_goal"] == 5.0


class TestCreateCampaignValidation:
    @pytest.mark.asyncio
    async def test_missing_account_id_raises(self):
        with pytest.raises(ToolInputError, match="account_id is required"):
            await handle_call_tool("create_campaign", {"name": "x"})

    @pytest.mark.asyncio
    async def test_numeric_account_id_raises(self):
        with pytest.raises(ToolInputError, match="search_accounts"):
            await handle_call_tool("create_campaign", _minimal_args(account_id="12345"))

    @pytest.mark.parametrize("field", [
        "name", "branding_text", "spending_limit_model", "marketing_objective",
    ])
    @pytest.mark.asyncio
    async def test_each_required_field_missing_raises(self, field):
        args = _minimal_args()
        del args[field]
        with pytest.raises(ToolInputError, match=f"Missing required field.*{field}"):
            await handle_call_tool("create_campaign", args)

    @pytest.mark.asyncio
    async def test_multiple_missing_fields_listed(self):
        args = _minimal_args()
        del args["name"]
        del args["branding_text"]
        with pytest.raises(ToolInputError, match="name.*branding_text|branding_text.*name"):
            await handle_call_tool("create_campaign", args)


class TestCreateCampaignEncoding:
    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_url_encodes_account_id(self, mock_post):
        mock_post.return_value = {"id": "c-1"}

        await handle_call_tool("create_campaign", _minimal_args(account_id="acme/evil"))

        assert _post_endpoint_arg(mock_post) == "/acme%2Fevil/campaigns"


class TestCreateCampaignAnnotations:
    """Tool annotations signal destructive write to MCP hosts."""

    @pytest.mark.asyncio
    async def test_create_campaign_has_destructive_annotations(self):
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        create = next(t for t in tools if t.name == "create_campaign")

        assert create.annotations is not None
        assert create.annotations.destructiveHint is True
        assert create.annotations.idempotentHint is False
        assert create.annotations.openWorldHint is True

    @pytest.mark.asyncio
    async def test_read_tools_have_no_annotations(self):
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        for name in ("get_campaign", "get_all_campaigns", "search_accounts"):
            tool = next(t for t in tools if t.name == name)
            assert tool.annotations is None, f"{name} is read-only and should have no annotations"

    @pytest.mark.asyncio
    async def test_marketing_objective_enum_in_schema(self):
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        create = next(t for t in tools if t.name == "create_campaign")
        mo = create.inputSchema["properties"]["marketing_objective"]

        assert set(mo["enum"]) == {
            "BRAND_AWARENESS", "DRIVE_WEBSITE_TRAFFIC",
            "LEADS_GENERATION", "ONLINE_PURCHASES", "MOBILE_APP_INSTALL",
        }

    @pytest.mark.asyncio
    async def test_bid_strategy_enum_in_schema(self):
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        create = next(t for t in tools if t.name == "create_campaign")
        bs = create.inputSchema["properties"]["bid_strategy"]

        assert set(bs["enum"]) == {"SMART", "FIXED", "TARGET_CPA", "MAX_CONVERSIONS", "MAX_VALUE"}

    @pytest.mark.asyncio
    async def test_spending_limit_model_enum_in_schema(self):
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        create = next(t for t in tools if t.name == "create_campaign")
        slm = create.inputSchema["properties"]["spending_limit_model"]

        assert set(slm["enum"]) == {"NONE", "MONTHLY", "ENTIRE"}


class TestCreateCampaignTopLevelFields:
    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_optional_top_level_scalars_sent(self, mock_post):
        mock_post.return_value = {"id": "c-1"}

        await handle_call_tool("create_campaign", _minimal_args(
            spending_limit_model="NONE",
            daily_cap=50.0,
            start_date="2026-05-01",
            end_date="2026-06-01",
            tracking_code="utm_source=foo",
            cpc_cap=1.5,
            comments="internal note",
        ))

        body = _post_body(mock_post)
        assert body["daily_cap"] == 50.0
        assert body["start_date"] == "2026-05-01"
        assert body["end_date"] == "2026-06-01"
        assert body["tracking_code"] == "utm_source=foo"
        assert body["cpc_cap"] == 1.5
        assert body["comments"] == "internal note"

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_unknown_args_not_forwarded(self, mock_post):
        mock_post.return_value = {"id": "c-1"}

        await handle_call_tool("create_campaign", _minimal_args(
            cpc=0.5, spending_limit=100.0,
            country_targeting={"type": "INCLUDE", "value": ["US"]},
            extra_unknown="should be dropped",
        ))

        body = _post_body(mock_post)
        assert "country_targeting" not in body
        assert "extra_unknown" not in body
        assert "account_id" not in body


class TestCreateCampaignDeliveryFields:
    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_includes_optional_daily_ad_delivery_model(self, mock_post):
        mock_post.return_value = {"id": "c-1"}

        await handle_call_tool("create_campaign", _minimal_args(
            cpc=0.5, spending_limit=100.0,
            daily_ad_delivery_model="BALANCED",
        ))

        assert _post_body(mock_post)["daily_ad_delivery_model"] == "BALANCED"

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_includes_optional_traffic_allocation_mode(self, mock_post):
        mock_post.return_value = {"id": "c-1"}

        await handle_call_tool("create_campaign", _minimal_args(
            cpc=0.5, spending_limit=100.0,
            traffic_allocation_mode="EVEN",
        ))

        assert _post_body(mock_post)["traffic_allocation_mode"] == "EVEN"

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_omitted_delivery_fields_not_in_body(self, mock_post):
        mock_post.return_value = {"id": "c-1"}

        await handle_call_tool("create_campaign", _minimal_args(
            cpc=0.5, spending_limit=100.0,
        ))

        body = _post_body(mock_post)
        assert "daily_ad_delivery_model" not in body
        assert "traffic_allocation_mode" not in body

    @pytest.mark.asyncio
    async def test_daily_ad_delivery_model_enum_in_schema(self):
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        create = next(t for t in tools if t.name == "create_campaign")
        dadm = create.inputSchema["properties"]["daily_ad_delivery_model"]

        assert set(dadm["enum"]) == {"BALANCED", "STRICT"}

    @pytest.mark.asyncio
    async def test_traffic_allocation_mode_enum_in_schema(self):
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        create = next(t for t in tools if t.name == "create_campaign")
        tam = create.inputSchema["properties"]["traffic_allocation_mode"]

        assert set(tam["enum"]) == {"OPTIMIZED", "EVEN"}


class TestCreateCampaignIsActive:
    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_includes_is_active_true(self, mock_post):
        mock_post.return_value = {"id": "c-1"}

        await handle_call_tool("create_campaign", _minimal_args(
            cpc=0.5, spending_limit=100.0,
            is_active=True,
        ))

        assert _post_body(mock_post)["is_active"] is True

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_includes_is_active_false(self, mock_post):
        mock_post.return_value = {"id": "c-1"}

        await handle_call_tool("create_campaign", _minimal_args(
            cpc=0.5, spending_limit=100.0,
            is_active=False,
        ))

        assert _post_body(mock_post)["is_active"] is False

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_omitted_is_active_not_in_body(self, mock_post):
        mock_post.return_value = {"id": "c-1"}

        await handle_call_tool("create_campaign", _minimal_args(
            cpc=0.5, spending_limit=100.0,
        ))

        assert "is_active" not in _post_body(mock_post)

    @pytest.mark.asyncio
    async def test_is_active_is_boolean_in_schema(self):
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        create = next(t for t in tools if t.name == "create_campaign")
        ia = create.inputSchema["properties"]["is_active"]

        assert ia["type"] == "boolean"

    @pytest.mark.asyncio
    async def test_is_active_not_required(self):
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        create = next(t for t in tools if t.name == "create_campaign")

        assert "is_active" not in create.inputSchema["required"]
