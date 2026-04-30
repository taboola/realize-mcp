"""Tests for fat-tool inline targeting on create_campaign / update_campaign.

Covers:
- Each main-endpoint targeting block (geo advanced, classic dims, techno, schedule,
  conversion_rules, publishers) routes to the campaign POST body with the correct wire keys.
- Sub-resource targeting (my_audiences, lookalike_audience, contextual_segments) fans out to
  /targeting/<suffix> after the main create/update.
- Geo classic+advanced mutex on update; classic geo rejected on create.
- Partial-failure path: sub-resource POST 4xx returns success with partial_failures.
"""
import json

import httpx
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


class TestGeoAdvancedOnCreate:
    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_geo_targeting_in_main_body(self, mock_post):
        mock_post.return_value = {"id": "c-1"}
        await handle_call_tool("create_campaign", _create_args(
            geo_targeting={
                "state": "EXISTS",
                "value": [{"type": "INCLUDE", "value": [{"country": "US"}]}],
            },
        ))
        body = _bodies_by_endpoint(mock_post)["/acme-inc/campaigns"]
        assert body["geo_targeting"]["state"] == "EXISTS"
        assert body["geo_targeting"]["value"][0]["value"][0] == {"country": "US"}

    @pytest.mark.asyncio
    async def test_classic_geo_rejected_on_create(self):
        with pytest.raises(ToolInputError, match="classic geo fields"):
            await handle_call_tool("create_campaign", _create_args(
                country_targeting={"type": "INCLUDE", "value": ["US"]},
            ))


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
    async def test_region_targeting_uses_region_country_wire_field(self, mock_post):
        mock_post.return_value = {"id": "c-123"}
        await handle_call_tool("update_campaign", _update_args(
            region_targeting={"type": "INCLUDE", "value": ["CA"]},
        ))
        body = _bodies_by_endpoint(mock_post)["/acme-inc/campaigns/c-123"]
        assert body["region_country_targeting"] == {"type": "INCLUDE", "value": ["CA"]}

    @pytest.mark.asyncio
    async def test_geo_advanced_and_classic_mutex(self):
        with pytest.raises(ToolInputError, match="advanced.*OR classic|classic.*OR advanced|not both"):
            await handle_call_tool("update_campaign", _update_args(
                geo_targeting={"state": "ALL", "value": []},
                country_targeting={"type": "INCLUDE", "value": ["US"]},
            ))


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
            conversion_rules=[{"id": 100}, {"id": 200}],
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


class TestSubResourceFanOutOnCreate:
    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.get', new_callable=AsyncMock)
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_my_audiences_posts_to_subresource(self, mock_post, mock_get):
        mock_post.return_value = {"id": "c-99"}
        mock_get.return_value = {"id": "c-99", "status": "PAUSED"}
        await handle_call_tool("create_campaign", _create_args(
            my_audiences={"collection": [{"type": "INCLUDE", "collection": [123]}]},
        ))
        bodies = _bodies_by_endpoint(mock_post)
        assert "/acme-inc/campaigns" in bodies
        assert "/acme-inc/campaigns/c-99/targeting/my_audiences" in bodies
        assert bodies["/acme-inc/campaigns/c-99/targeting/my_audiences"] == {
            "collection": [{"type": "INCLUDE", "collection": [123]}]
        }

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.get', new_callable=AsyncMock)
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_all_three_sub_resources_fanned_out(self, mock_post, mock_get):
        mock_post.return_value = {"id": "c-99"}
        mock_get.return_value = {"id": "c-99"}
        await handle_call_tool("create_campaign", _create_args(
            my_audiences={"collection": []},
            lookalike_audience={"collection": []},
            contextual_segments={"collection": []},
        ))
        endpoints = set(_bodies_by_endpoint(mock_post).keys())
        assert "/acme-inc/campaigns" in endpoints
        assert "/acme-inc/campaigns/c-99/targeting/my_audiences" in endpoints
        assert "/acme-inc/campaigns/c-99/targeting/lookalike_audience" in endpoints
        assert "/acme-inc/campaigns/c-99/targeting/contextual_segments" in endpoints


class TestSubResourceFanOutOnUpdate:
    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.get', new_callable=AsyncMock)
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_only_sub_resource_skips_main_post(self, mock_post, mock_get):
        mock_post.return_value = {}
        mock_get.return_value = {"id": "c-123"}
        await handle_call_tool("update_campaign", _update_args(
            my_audiences={"collection": [{"type": "INCLUDE", "collection": [42]}]},
        ))
        endpoints = set(_bodies_by_endpoint(mock_post).keys())
        assert endpoints == {"/acme-inc/campaigns/c-123/targeting/my_audiences"}
        mock_get.assert_called_once_with("/acme-inc/campaigns/c-123")

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.get', new_callable=AsyncMock)
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_main_and_sub_resource_both_post(self, mock_post, mock_get):
        mock_post.return_value = {"id": "c-123"}
        mock_get.return_value = {"id": "c-123"}
        await handle_call_tool("update_campaign", _update_args(
            is_active=True,
            my_audiences={"collection": []},
        ))
        endpoints = set(_bodies_by_endpoint(mock_post).keys())
        assert "/acme-inc/campaigns/c-123" in endpoints
        assert "/acme-inc/campaigns/c-123/targeting/my_audiences" in endpoints


class TestUpdateCampaignSkipsGetWhenMainOnly:
    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.get', new_callable=AsyncMock)
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_main_only_does_not_fire_get(self, mock_post, mock_get):
        mock_post.return_value = {"id": "c-123", "name": "Renamed"}
        await handle_call_tool("update_campaign", {
            "account_id": "acme-inc", "campaign_id": "c-123", "name": "Renamed",
        })
        mock_get.assert_not_called()


class TestSafeErrorBodyNonJson:
    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.get', new_callable=AsyncMock)
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_non_json_4xx_body_falls_back_to_text(self, mock_post, mock_get):
        async def post_side_effect(endpoint, data=None):
            if endpoint == "/acme-inc/campaigns":
                return {"id": "c-99"}
            request = httpx.Request("POST", "https://x" + endpoint)
            response = httpx.Response(
                400, request=request,
                content=b'<html>Bad Request</html>',
                headers={"content-type": "text/html"},
            )
            raise httpx.HTTPStatusError("bad", request=request, response=response)

        mock_post.side_effect = post_side_effect
        mock_get.return_value = {"id": "c-99"}

        result = await handle_call_tool("create_campaign", _create_args(
            my_audiences={"collection": []},
        ))
        text = result[0].text
        assert "partial_failures" in text
        assert "Bad Request" in text


class TestPartialFailures:
    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.get', new_callable=AsyncMock)
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_create_returns_partial_failures_on_subresource_4xx(self, mock_post, mock_get):
        async def post_side_effect(endpoint, data=None):
            if endpoint == "/acme-inc/campaigns":
                return {"id": "c-99"}
            request = httpx.Request("POST", "https://x" + endpoint)
            response = httpx.Response(
                400, request=request,
                content=b'{"error": "audience not found"}',
                headers={"content-type": "application/json"},
            )
            raise httpx.HTTPStatusError("bad", request=request, response=response)

        mock_post.side_effect = post_side_effect
        mock_get.return_value = {"id": "c-99", "status": "PAUSED"}

        result = await handle_call_tool("create_campaign", _create_args(
            my_audiences={"collection": [{"type": "INCLUDE", "collection": [999]}]},
        ))
        text = result[0].text
        assert "c-99" in text
        assert "partial_failures" in text
        assert "my_audiences" in text

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.get', new_callable=AsyncMock)
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_partial_failures_does_not_short_circuit(self, mock_post, mock_get):
        # First sub-resource (my_audiences) fails; second (lookalike) should still be attempted.
        attempted = []

        async def post_side_effect(endpoint, data=None):
            if endpoint == "/acme-inc/campaigns":
                return {"id": "c-99"}
            attempted.append(endpoint)
            if "my_audiences" in endpoint:
                request = httpx.Request("POST", "https://x" + endpoint)
                response = httpx.Response(400, request=request, content=b'{}')
                raise httpx.HTTPStatusError("bad", request=request, response=response)
            return {"ok": True}

        mock_post.side_effect = post_side_effect
        mock_get.return_value = {"id": "c-99"}

        await handle_call_tool("create_campaign", _create_args(
            my_audiences={"collection": []},
            lookalike_audience={"collection": []},
        ))
        assert any("my_audiences" in ep for ep in attempted)
        assert any("lookalike_audience" in ep for ep in attempted)


class TestSubResourceValidationFailFast:
    @pytest.mark.asyncio
    async def test_invalid_my_audiences_raises_before_post(self):
        with pytest.raises(ToolInputError, match="my_audiences"):
            await handle_call_tool("create_campaign", _create_args(
                my_audiences={"collection": "not a list"},
            ))

    @pytest.mark.asyncio
    async def test_invalid_lookalike_raises_before_post(self):
        with pytest.raises(ToolInputError, match="lookalike_audience"):
            await handle_call_tool("update_campaign", _update_args(
                lookalike_audience={"collection": [
                    {"type": "EXCLUDE", "collection": []},
                ]},
            ))


class TestFatToolSchemaShape:
    @pytest.mark.asyncio
    async def test_create_campaign_has_targeting_blocks_in_schema(self):
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        create = next(t for t in tools if t.name == "create_campaign")
        props = create.inputSchema["properties"]
        for f in (
            "geo_targeting", "platform_targeting", "os_targeting", "browser_targeting",
            "connection_type_targeting", "activity_schedule", "conversion_rules",
            "publisher_targeting", "publisher_groups_targeting", "publisher_bid_modifier",
            "contextual_segments", "my_audiences", "lookalike_audience",
        ):
            assert f in props, f"create_campaign missing schema property: {f}"

    @pytest.mark.asyncio
    async def test_update_campaign_has_classic_geo_blocks(self):
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        update = next(t for t in tools if t.name == "update_campaign")
        props = update.inputSchema["properties"]
        for f in ("country_targeting", "region_targeting", "dma_targeting", "city_targeting", "postal_code_targeting"):
            assert f in props, f"update_campaign missing classic geo property: {f}"

    @pytest.mark.asyncio
    async def test_create_campaign_has_no_classic_geo_blocks(self):
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        create = next(t for t in tools if t.name == "create_campaign")
        props = create.inputSchema["properties"]
        for f in ("country_targeting", "region_targeting", "dma_targeting", "city_targeting", "postal_code_targeting"):
            assert f not in props, f"create_campaign should not expose classic geo {f}"
