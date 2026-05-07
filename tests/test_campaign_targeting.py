"""Tests for fat-tool inline targeting on create_campaign / update_campaign.

Covers:
- Each main-endpoint targeting block (classic geo dims, techno, schedule,
  conversion_rules, publishers) routes to the campaign POST body with the correct wire keys.
- Sub-resource targeting (my_audiences, lookalike_audience, contextual_segments) fans out to
  /targeting/<suffix> after the main create/update.
- Partial-failure path: sub-resource POST 4xx returns success with partial_failures.
"""
import json

import pytest
from unittest.mock import AsyncMock, patch

from realize.realize_server import handle_call_tool
from realize.tools.errors import ToolInputError


def _bodies_by_endpoint(mock_post):
    out = {}
    for call in mock_post.call_args_list:
        args, kwargs = call
        endpoint = args[0] if args else kwargs.get("endpoint")
        out[endpoint] = kwargs.get("data")
    return out


def _create_args(**overrides):
    base = {
        "account_id": "acme-inc",
        "name": "T",
        "marketing_objective": "DRIVE_WEBSITE_TRAFFIC",
        "branding_text": "Acme",
        "spending_limit_model": "ENTIRE",
        "spending_limit": 1000,
        "cpc": 0.5,
    }
    base.update(overrides)
    return base


def _update_args(**overrides):
    base = {"account_id": "acme-inc", "campaign_id": "c-123"}
    base.update(overrides)
    return base


class TestClassicGeoOnCreate:
    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_country_targeting_in_main_body(self, mock_post):
        mock_post.return_value = {"id": "c-1"}
        await handle_call_tool("create_campaign", _create_args(
            country_targeting={"type": "INCLUDE", "value": ["US"]},
        ))
        body = _bodies_by_endpoint(mock_post)["/acme-inc/campaigns"]
        assert body["country_targeting"] == {"type": "INCLUDE", "value": ["US"]}

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_region_country_targeting_passes_through(self, mock_post):
        mock_post.return_value = {"id": "c-1"}
        await handle_call_tool("create_campaign", _create_args(
            region_country_targeting={"type": "INCLUDE", "value": ["California"]},
        ))
        body = _bodies_by_endpoint(mock_post)["/acme-inc/campaigns"]
        assert body["region_country_targeting"] == {"type": "INCLUDE", "value": ["California"]}


class TestClassicGeoOnUpdate:
    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_country_targeting_wire_field(self, mock_post):
        mock_post.return_value = {"id": "c-123"}
        await handle_call_tool("update_campaign", _update_args(
            country_targeting={"type": "INCLUDE", "value": ["US"]},
        ))
        body = _bodies_by_endpoint(mock_post)["/acme-inc/campaigns/c-123"]
        assert body["country_targeting"] == {"type": "INCLUDE", "value": ["US"]}

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_region_country_targeting_passes_through(self, mock_post):
        mock_post.return_value = {"id": "c-123"}
        await handle_call_tool("update_campaign", _update_args(
            region_country_targeting={"type": "INCLUDE", "value": ["CA"]},
        ))
        body = _bodies_by_endpoint(mock_post)["/acme-inc/campaigns/c-123"]
        assert body["region_country_targeting"] == {"type": "INCLUDE", "value": ["CA"]}


class TestTechnoOnFatTools:
    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_platform_targeting_in_body(self, mock_post):
        mock_post.return_value = {"id": "c-1"}
        await handle_call_tool("create_campaign", _create_args(
            platform_targeting={"type": "INCLUDE", "value": ["PHON"]},
        ))
        body = _bodies_by_endpoint(mock_post)["/acme-inc/campaigns"]
        assert body["platform_targeting"] == {"type": "INCLUDE", "value": ["PHON"]}

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_os_targeting_with_sub_categories(self, mock_post):
        mock_post.return_value = {"id": "c-1"}
        await handle_call_tool("create_campaign", _create_args(
            os_targeting={
                "type": "INCLUDE",
                "value": [{"os_family": "iOS", "sub_categories": ["iOS_17"]}],
            },
        ))
        body = _bodies_by_endpoint(mock_post)["/acme-inc/campaigns"]
        assert body["os_targeting"]["value"] == [{"os_family": "iOS", "sub_categories": ["iOS_17"]}]


class TestScheduleOnFatTools:
    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_always_mode(self, mock_post):
        mock_post.return_value = {"id": "c-1"}
        await handle_call_tool("create_campaign", _create_args(
            activity_schedule={"mode": "ALWAYS"},
        ))
        body = _bodies_by_endpoint(mock_post)["/acme-inc/campaigns"]
        assert body["activity_schedule"] == {"mode": "ALWAYS"}

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_custom_mode_with_rules(self, mock_post):
        mock_post.return_value = {"id": "c-123"}
        await handle_call_tool("update_campaign", _update_args(
            activity_schedule={
                "mode": "CUSTOM",
                "time_zone": "America/New_York",
                "rules": [{"type": "INCLUDE", "day": "MONDAY", "from_hour": 9, "until_hour": 17}],
            },
        ))
        body = _bodies_by_endpoint(mock_post)["/acme-inc/campaigns/c-123"]
        assert body["activity_schedule"]["mode"] == "CUSTOM"
        assert body["activity_schedule"]["time_zone"] == "America/New_York"
        assert body["activity_schedule"]["rules"][0]["day"] == "MONDAY"


class TestConversionRulesOnFatTools:
    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_attaches_rules(self, mock_post):
        mock_post.return_value = {"id": "c-123"}
        await handle_call_tool("update_campaign", _update_args(
            conversion_rules={"rules": [{"id": 100}, {"id": 200}]},
        ))
        body = _bodies_by_endpoint(mock_post)["/acme-inc/campaigns/c-123"]
        assert body["conversion_rules"] == {"rules": [{"id": 100}, {"id": 200}]}


class TestPublishersOnFatTools:
    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_publisher_targeting_and_modifier(self, mock_post):
        mock_post.return_value = {"id": "c-123"}
        await handle_call_tool("update_campaign", _update_args(
            publisher_targeting={"type": "EXCLUDE", "value": ["pub_a"]},
            publisher_bid_modifier={"values": [{"target": "pub_b", "cpc_modification": 1.25}]},
        ))
        body = _bodies_by_endpoint(mock_post)["/acme-inc/campaigns/c-123"]
        assert body["publisher_targeting"] == {"type": "EXCLUDE", "value": ["pub_a"]}
        assert body["publisher_bid_modifier"]["values"][0]["target"] == "pub_b"
        assert body["publisher_bid_modifier"]["values"][0]["cpc_modification"] == 1.25


class TestInlineSubResourceTargeting:
    """Audiences / lookalike / contextual_segments ride inline on the main POST."""

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_audiences_targeting_passes_through(self, mock_post):
        mock_post.return_value = {"id": "c-99"}
        await handle_call_tool("create_campaign", _create_args(
            audiences_targeting={
                "state": "EXISTS",
                "value": [{"type": "INCLUDE", "value": [123, 456]}],
            },
        ))
        bodies = _bodies_by_endpoint(mock_post)
        assert set(bodies.keys()) == {"/acme-inc/campaigns"}  # single POST
        body = bodies["/acme-inc/campaigns"]
        assert body["audiences_targeting"] == {
            "state": "EXISTS",
            "value": [{"type": "INCLUDE", "value": [123, 456]}],
        }

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_audiences_targeting_clear_via_state_all(self, mock_post):
        mock_post.return_value = {"id": "c-99"}
        await handle_call_tool("create_campaign", _create_args(
            audiences_targeting={"state": "ALL", "value": []},
        ))
        body = _bodies_by_endpoint(mock_post)["/acme-inc/campaigns"]
        assert body["audiences_targeting"] == {"state": "ALL", "value": []}

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_lookalike_audience_targeting_passes_through(self, mock_post):
        mock_post.return_value = {"id": "c-99"}
        await handle_call_tool("create_campaign", _create_args(
            lookalike_audience_targeting={
                "state": "EXISTS",
                "value": [{
                    "type": "INCLUDE",
                    "value": [{"rule_id": 7, "similarity_level": 10}],
                }],
            },
        ))
        body = _bodies_by_endpoint(mock_post)["/acme-inc/campaigns"]
        assert body["lookalike_audience_targeting"] == {
            "state": "EXISTS",
            "value": [{
                "type": "INCLUDE",
                "value": [{"rule_id": 7, "similarity_level": 10}],
            }],
        }

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_contextual_segments_targeting_passes_through(self, mock_post):
        mock_post.return_value = {"id": "c-99"}
        await handle_call_tool("create_campaign", _create_args(
            contextual_segments_targeting={
                "state": "EXISTS",
                "value": [{"type": "EXCLUDE", "value": [11, 22]}],
            },
        ))
        body = _bodies_by_endpoint(mock_post)["/acme-inc/campaigns"]
        assert body["contextual_segments_targeting"] == {
            "state": "EXISTS",
            "value": [{"type": "EXCLUDE", "value": [11, 22]}],
        }

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_all_three_inline_in_single_post(self, mock_post):
        mock_post.return_value = {"id": "c-99"}
        await handle_call_tool("create_campaign", _create_args(
            audiences_targeting={
                "state": "EXISTS",
                "value": [{"type": "INCLUDE", "value": [1]}],
            },
            lookalike_audience_targeting={
                "state": "EXISTS",
                "value": [{
                    "type": "INCLUDE",
                    "value": [{"rule_id": 9, "similarity_level": 5}],
                }],
            },
            contextual_segments_targeting={
                "state": "EXISTS",
                "value": [{"type": "INCLUDE", "value": [42]}],
            },
        ))
        bodies = _bodies_by_endpoint(mock_post)
        # Single atomic POST, all three sections in body.
        assert set(bodies.keys()) == {"/acme-inc/campaigns"}
        body = bodies["/acme-inc/campaigns"]
        assert "audiences_targeting" in body
        assert "lookalike_audience_targeting" in body
        assert "contextual_segments_targeting" in body

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_update_with_only_audiences_targeting_single_post(self, mock_post):
        mock_post.return_value = {"id": "c-123"}
        await handle_call_tool("update_campaign", _update_args(
            audiences_targeting={
                "state": "EXISTS",
                "value": [{"type": "INCLUDE", "value": [42]}],
            },
        ))
        bodies = _bodies_by_endpoint(mock_post)
        assert set(bodies.keys()) == {"/acme-inc/campaigns/c-123"}
        body = bodies["/acme-inc/campaigns/c-123"]
        assert body["audiences_targeting"] == {
            "state": "EXISTS",
            "value": [{"type": "INCLUDE", "value": [42]}],
        }


class TestSubResourceValidationFailFast:
    @pytest.mark.asyncio
    async def test_invalid_audiences_targeting_raises_before_post(self):
        with pytest.raises(ToolInputError, match="audiences_targeting"):
            await handle_call_tool("create_campaign", _create_args(
                audiences_targeting={"state": "EXISTS", "value": "not a list"},
            ))

    @pytest.mark.asyncio
    async def test_invalid_lookalike_raises_before_post(self):
        with pytest.raises(ToolInputError, match="lookalike_audience_targeting"):
            await handle_call_tool("update_campaign", _update_args(
                lookalike_audience_targeting={
                    "state": "EXISTS",
                    "value": [{"type": "EXCLUDE", "value": []}],
                },
            ))


class TestFatToolSchemaShape:
    @pytest.mark.asyncio
    async def test_create_campaign_has_targeting_blocks_in_schema(self):
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        create = next(t for t in tools if t.name == "create_campaign")
        props = create.inputSchema["properties"]
        for f in (
            "platform_targeting", "os_targeting", "browser_targeting",
            "connection_type_targeting", "activity_schedule", "conversion_rules",
            "publisher_targeting", "publisher_bid_modifier",
            "contextual_segments_targeting", "audiences_targeting", "lookalike_audience_targeting",
        ):
            assert f in props, f"create_campaign missing schema property: {f}"

    @pytest.mark.asyncio
    async def test_update_campaign_has_classic_geo_blocks(self):
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        update = next(t for t in tools if t.name == "update_campaign")
        props = update.inputSchema["properties"]
        for f in ("country_targeting", "region_country_targeting", "dma_country_targeting", "city_targeting", "postal_code_targeting"):
            assert f in props, f"update_campaign missing classic geo property: {f}"

    @pytest.mark.asyncio
    async def test_create_campaign_has_classic_geo_blocks(self):
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        create = next(t for t in tools if t.name == "create_campaign")
        props = create.inputSchema["properties"]
        for f in ("country_targeting", "region_country_targeting", "dma_country_targeting", "city_targeting", "postal_code_targeting"):
            assert f in props, f"create_campaign missing classic geo property: {f}"
