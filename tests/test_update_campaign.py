"""Tests for the update_campaign write tool."""
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
        "name": "Renamed",
    }
    base.update(overrides)
    return base


class TestUpdateCampaignBaseValidation:
    @pytest.mark.asyncio
    async def test_missing_account_id_raises(self):
        with pytest.raises(ToolInputError, match="account_id is required"):
            await handle_call_tool("update_campaign", {"campaign_id": "c-123", "name": "x"})

    @pytest.mark.asyncio
    async def test_numeric_account_id_rejected(self):
        with pytest.raises(ToolInputError, match="search_accounts"):
            await handle_call_tool("update_campaign", _args(account_id="12345"))

    @pytest.mark.asyncio
    async def test_missing_campaign_id_raises(self):
        args = _args()
        del args["campaign_id"]
        with pytest.raises(ToolInputError, match="campaign_id is required"):
            await handle_call_tool("update_campaign", args)

    @pytest.mark.asyncio
    async def test_no_updatable_fields_rejected(self):
        with pytest.raises(ToolInputError, match="at least one updatable field"):
            await handle_call_tool(
                "update_campaign",
                {"account_id": "acme-inc", "campaign_id": "c-123"},
            )

    @pytest.mark.asyncio
    async def test_only_none_values_rejected(self):
        with pytest.raises(ToolInputError, match="at least one updatable field"):
            await handle_call_tool(
                "update_campaign",
                {"account_id": "acme-inc", "campaign_id": "c-123", "name": None, "comments": None},
            )


class TestUpdateCampaignCrossFieldValidation:
    @pytest.mark.asyncio
    async def test_spending_limit_model_monthly_requires_spending_limit(self):
        with pytest.raises(ToolInputError, match="spending_limit is required"):
            await handle_call_tool(
                "update_campaign",
                _args(spending_limit_model="MONTHLY"),
            )

    @pytest.mark.asyncio
    async def test_spending_limit_model_entire_requires_spending_limit(self):
        with pytest.raises(ToolInputError, match="spending_limit is required"):
            await handle_call_tool(
                "update_campaign",
                _args(spending_limit_model="ENTIRE"),
            )

    @pytest.mark.asyncio
    async def test_spending_limit_model_none_requires_daily_cap(self):
        with pytest.raises(ToolInputError, match="daily_cap is required"):
            await handle_call_tool(
                "update_campaign",
                _args(spending_limit_model="NONE"),
            )

    @pytest.mark.asyncio
    async def test_bid_strategy_cpa_goal_requires_cpa_goal(self):
        with pytest.raises(ToolInputError, match="cpa_goal is required"):
            await handle_call_tool(
                "update_campaign",
                _args(bid_strategy="TARGET_CPA"),
            )

    @pytest.mark.asyncio
    async def test_end_date_before_start_date_rejected(self):
        with pytest.raises(ToolInputError, match="end_date must be on or after start_date"):
            await handle_call_tool(
                "update_campaign",
                _args(start_date="2026-06-01", end_date="2026-05-01"),
            )

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_solo_spending_limit_passes(self, mock_post):
        mock_post.return_value = {"id": "c-123"}
        await handle_call_tool(
            "update_campaign",
            {"account_id": "acme-inc", "campaign_id": "c-123", "spending_limit": 5000},
        )
        assert _post_body(mock_post) == {"spending_limit": 5000}

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_solo_cpa_goal_passes(self, mock_post):
        mock_post.return_value = {"id": "c-123"}
        await handle_call_tool(
            "update_campaign",
            {"account_id": "acme-inc", "campaign_id": "c-123", "cpa_goal": 12.5},
        )
        assert _post_body(mock_post) == {"cpa_goal": 12.5}

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_solo_daily_cap_passes(self, mock_post):
        mock_post.return_value = {"id": "c-123"}
        await handle_call_tool(
            "update_campaign",
            {"account_id": "acme-inc", "campaign_id": "c-123", "daily_cap": 100},
        )
        assert _post_body(mock_post) == {"daily_cap": 100}

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_solo_start_date_passes(self, mock_post):
        mock_post.return_value = {"id": "c-123"}
        await handle_call_tool(
            "update_campaign",
            {"account_id": "acme-inc", "campaign_id": "c-123", "start_date": "2026-05-01"},
        )
        assert _post_body(mock_post) == {"start_date": "2026-05-01"}

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_solo_end_date_passes(self, mock_post):
        mock_post.return_value = {"id": "c-123"}
        await handle_call_tool(
            "update_campaign",
            {"account_id": "acme-inc", "campaign_id": "c-123", "end_date": "2026-05-01"},
        )
        assert _post_body(mock_post) == {"end_date": "2026-05-01"}

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_bid_strategy_max_conv_no_cpa_goal_required(self, mock_post):
        mock_post.return_value = {"id": "c-123"}
        await handle_call_tool(
            "update_campaign",
            _args(bid_strategy="MAX_CONVERSIONS"),
        )
        assert _post_body(mock_post)["bid_strategy"] == "MAX_CONVERSIONS"

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_equal_dates_pass(self, mock_post):
        mock_post.return_value = {"id": "c-123"}
        await handle_call_tool(
            "update_campaign",
            _args(start_date="2026-05-01", end_date="2026-05-01"),
        )
        body = _post_body(mock_post)
        assert body["start_date"] == "2026-05-01"
        assert body["end_date"] == "2026-05-01"


class TestUpdateCampaignWireMapping:
    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_posts_to_campaign_endpoint(self, mock_post):
        mock_post.return_value = {"id": "c-123"}
        await handle_call_tool("update_campaign", _args())
        assert _post_endpoint(mock_post) == "/acme-inc/campaigns/c-123"

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_url_encodes_path_segments(self, mock_post):
        mock_post.return_value = {"id": "c-1"}
        await handle_call_tool(
            "update_campaign",
            _args(account_id="acme/evil", campaign_id="c/1"),
        )
        assert _post_endpoint(mock_post) == "/acme%2Fevil/campaigns/c%2F1"

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_account_id_and_campaign_id_not_in_body(self, mock_post):
        mock_post.return_value = {"id": "c-123"}
        await handle_call_tool("update_campaign", _args())
        body = _post_body(mock_post)
        assert "account_id" not in body
        assert "campaign_id" not in body

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_single_scalar_passes_through(self, mock_post):
        mock_post.return_value = {"id": "c-123"}
        await handle_call_tool("update_campaign", _args())
        assert _post_body(mock_post) == {"name": "Renamed"}

    @pytest.mark.parametrize("field,value,extras", [
        ("name", "New name", {}),
        ("marketing_objective", "BRAND_AWARENESS", {}),
        ("branding_text", "Acme", {}),
        ("spending_limit_model", "MONTHLY", {"spending_limit": 5000}),
        ("spending_limit", 5000, {}),
        ("daily_cap", 50, {}),
        ("cpc", 0.25, {}),
        ("bid_strategy", "MAX_CONVERSIONS", {}),
        ("cpa_goal", 15, {}),
        ("start_date", "2026-05-01", {}),
        ("end_date", "2026-06-01", {}),
        ("tracking_code", "utm_source=foo", {}),
        ("cpc_cap", 1.5, {}),
        ("comments", "internal", {}),
        ("daily_ad_delivery_model", "BALANCED", {}),
        ("traffic_allocation_mode", "OPTIMIZED", {}),
        ("is_active", True, {}),
    ])
    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_each_scalar_field_passes_through(self, mock_post, field, value, extras):
        mock_post.return_value = {"id": "c-123"}
        payload = {"account_id": "acme-inc", "campaign_id": "c-123", field: value, **extras}
        await handle_call_tool("update_campaign", payload)
        body = _post_body(mock_post)
        assert body[field] == value
        for k, v in extras.items():
            assert body[k] == v
        assert "account_id" not in body
        assert "campaign_id" not in body

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_multi_field_update_body_shape(self, mock_post):
        mock_post.return_value = {"id": "c-123"}
        await handle_call_tool(
            "update_campaign",
            _args(end_date="2026-09-30", cpc_cap=1.5, comments="bumped"),
        )
        body = _post_body(mock_post)
        assert body == {
            "name": "Renamed",
            "end_date": "2026-09-30",
            "cpc_cap": 1.5,
            "comments": "bumped",
        }

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_unknown_args_not_forwarded(self, mock_post):
        mock_post.return_value = {"id": "c-123"}
        await handle_call_tool(
            "update_campaign",
            _args(
                geo_targeting={"state": "ALL", "value": []},
                country_targeting={"type": "INCLUDE", "value": ["US"]},
                extra_unknown="dropped",
            ),
        )
        body = _post_body(mock_post)
        assert body == {"name": "Renamed"}

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_response_text_contains_campaign_id(self, mock_post):
        mock_post.return_value = {"id": "c-123"}
        result = await handle_call_tool("update_campaign", _args())
        assert "c-123" in result[0].text

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_solo_daily_ad_delivery_model_passes(self, mock_post):
        mock_post.return_value = {"id": "c-123"}
        await handle_call_tool(
            "update_campaign",
            {"account_id": "acme-inc", "campaign_id": "c-123", "daily_ad_delivery_model": "STRICT"},
        )
        assert _post_body(mock_post) == {"daily_ad_delivery_model": "STRICT"}

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_solo_traffic_allocation_mode_passes(self, mock_post):
        mock_post.return_value = {"id": "c-123"}
        await handle_call_tool(
            "update_campaign",
            {"account_id": "acme-inc", "campaign_id": "c-123", "traffic_allocation_mode": "EVEN"},
        )
        assert _post_body(mock_post) == {"traffic_allocation_mode": "EVEN"}

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_solo_is_active_true_passes(self, mock_post):
        mock_post.return_value = {"id": "c-123"}
        await handle_call_tool(
            "update_campaign",
            {"account_id": "acme-inc", "campaign_id": "c-123", "is_active": True},
        )
        assert _post_body(mock_post) == {"is_active": True}

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_solo_is_active_false_passes(self, mock_post):
        mock_post.return_value = {"id": "c-123"}
        await handle_call_tool(
            "update_campaign",
            {"account_id": "acme-inc", "campaign_id": "c-123", "is_active": False},
        )
        assert _post_body(mock_post) == {"is_active": False}


class TestUpdateCampaignSchema:
    @pytest.mark.asyncio
    async def test_marketing_objective_enum(self):
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        update = next(t for t in tools if t.name == "update_campaign")
        mo = update.inputSchema["properties"]["marketing_objective"]
        assert set(mo["enum"]) == {
            "BRAND_AWARENESS", "DRIVE_WEBSITE_TRAFFIC", "WEBSITE_ENGAGEMENT",
            "LEADS_GENERATION", "ONLINE_PURCHASES", "MOBILE_APP_INSTALL",
        }

    @pytest.mark.asyncio
    async def test_spending_limit_model_enum(self):
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        update = next(t for t in tools if t.name == "update_campaign")
        slm = update.inputSchema["properties"]["spending_limit_model"]
        assert set(slm["enum"]) == {"NONE", "MONTHLY", "ENTIRE"}

    @pytest.mark.asyncio
    async def test_bid_strategy_enum(self):
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        update = next(t for t in tools if t.name == "update_campaign")
        bs = update.inputSchema["properties"]["bid_strategy"]
        assert set(bs["enum"]) == {"SMART", "FIXED", "TARGET_CPA", "MAX_CONVERSIONS", "MAX_VALUE"}

    @pytest.mark.asyncio
    async def test_only_account_and_campaign_required(self):
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        update = next(t for t in tools if t.name == "update_campaign")
        assert update.inputSchema["required"] == ["account_id", "campaign_id"]

    @pytest.mark.asyncio
    async def test_all_17_fields_present_as_optional_properties(self):
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        update = next(t for t in tools if t.name == "update_campaign")
        props = update.inputSchema["properties"]
        required = update.inputSchema["required"]

        expected_fields = {
            "name", "marketing_objective", "branding_text", "spending_limit_model",
            "spending_limit", "daily_cap", "cpc", "bid_strategy", "cpa_goal",
            "start_date", "end_date", "tracking_code", "cpc_cap", "comments",
            "daily_ad_delivery_model", "traffic_allocation_mode", "is_active",
        }
        for f in expected_fields:
            assert f in props, f"missing schema property: {f}"
            assert f not in required, f"{f} should be optional"

    @pytest.mark.asyncio
    async def test_is_active_is_boolean_in_schema(self):
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        update = next(t for t in tools if t.name == "update_campaign")
        ia = update.inputSchema["properties"]["is_active"]
        assert ia["type"] == "boolean"

    @pytest.mark.asyncio
    async def test_daily_ad_delivery_model_enum(self):
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        update = next(t for t in tools if t.name == "update_campaign")
        dadm = update.inputSchema["properties"]["daily_ad_delivery_model"]
        assert set(dadm["enum"]) == {"BALANCED", "STRICT"}

    @pytest.mark.asyncio
    async def test_traffic_allocation_mode_enum(self):
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        update = next(t for t in tools if t.name == "update_campaign")
        tam = update.inputSchema["properties"]["traffic_allocation_mode"]
        assert set(tam["enum"]) == {"OPTIMIZED", "EVEN"}


class TestUpdateCampaignAnnotations:
    @pytest.mark.asyncio
    async def test_has_destructive_idempotent_open_world_annotations(self):
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        update = next(t for t in tools if t.name == "update_campaign")
        assert update.annotations is not None
        assert update.annotations.destructiveHint is True
        assert update.annotations.idempotentHint is True
        assert update.annotations.openWorldHint is True
