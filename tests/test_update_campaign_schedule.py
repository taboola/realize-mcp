"""Tests for the update_campaign_schedule write tool."""
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


def _custom_rule(**overrides):
    base = {"type": "INCLUDE", "day": "MONDAY", "from_hour": 9, "until_hour": 17}
    base.update(overrides)
    return base


def _args(**overrides):
    base = {
        "account_id": "acme-inc",
        "campaign_id": "c-123",
        "schedule": {"mode": "ALWAYS"},
    }
    base.update(overrides)
    return base


class TestScheduleValidation:
    @pytest.mark.asyncio
    async def test_rejects_schedule_not_object(self):
        with pytest.raises(ToolInputError, match="schedule must be an object"):
            await handle_call_tool("update_campaign_schedule", _args(schedule=[]))

    @pytest.mark.asyncio
    async def test_rejects_unknown_mode(self):
        with pytest.raises(ToolInputError, match="schedule.mode must be one of"):
            await handle_call_tool(
                "update_campaign_schedule",
                _args(schedule={"mode": "SOMETIMES"}),
            )

    @pytest.mark.asyncio
    async def test_rejects_always_with_rules(self):
        with pytest.raises(ToolInputError, match="empty or omitted when mode=ALWAYS"):
            await handle_call_tool(
                "update_campaign_schedule",
                _args(schedule={"mode": "ALWAYS", "rules": [_custom_rule()]}),
            )

    @pytest.mark.asyncio
    async def test_rejects_custom_without_time_zone(self):
        with pytest.raises(ToolInputError, match="time_zone is required when mode=CUSTOM"):
            await handle_call_tool(
                "update_campaign_schedule",
                _args(schedule={"mode": "CUSTOM", "rules": [_custom_rule()]}),
            )

    @pytest.mark.asyncio
    async def test_rejects_custom_with_empty_time_zone(self):
        with pytest.raises(ToolInputError, match="time_zone is required when mode=CUSTOM"):
            await handle_call_tool(
                "update_campaign_schedule",
                _args(schedule={"mode": "CUSTOM", "time_zone": "", "rules": [_custom_rule()]}),
            )

    @pytest.mark.asyncio
    async def test_rejects_custom_without_rules(self):
        with pytest.raises(ToolInputError, match="rules must be a non-empty list when mode=CUSTOM"):
            await handle_call_tool(
                "update_campaign_schedule",
                _args(schedule={"mode": "CUSTOM", "time_zone": "UTC"}),
            )

    @pytest.mark.asyncio
    async def test_rejects_custom_with_empty_rules(self):
        with pytest.raises(ToolInputError, match="rules must be a non-empty list when mode=CUSTOM"):
            await handle_call_tool(
                "update_campaign_schedule",
                _args(schedule={"mode": "CUSTOM", "time_zone": "UTC", "rules": []}),
            )

    @pytest.mark.asyncio
    async def test_rejects_invalid_rule_type(self):
        with pytest.raises(ToolInputError, match=r"rules\[0\].type must be one of"):
            await handle_call_tool(
                "update_campaign_schedule",
                _args(schedule={
                    "mode": "CUSTOM", "time_zone": "UTC",
                    "rules": [_custom_rule(type="ALL")],
                }),
            )

    @pytest.mark.asyncio
    async def test_rejects_invalid_day(self):
        with pytest.raises(ToolInputError, match=r"rules\[0\].day must be one of"):
            await handle_call_tool(
                "update_campaign_schedule",
                _args(schedule={
                    "mode": "CUSTOM", "time_zone": "UTC",
                    "rules": [_custom_rule(day="MON")],
                }),
            )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("from_hour", [-1, 24, 100])
    async def test_rejects_from_hour_out_of_range(self, from_hour):
        with pytest.raises(ToolInputError, match=r"from_hour must be an integer in \[0, 23\]"):
            await handle_call_tool(
                "update_campaign_schedule",
                _args(schedule={
                    "mode": "CUSTOM", "time_zone": "UTC",
                    "rules": [_custom_rule(from_hour=from_hour, until_hour=24)],
                }),
            )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("until_hour", [0, 25, 100])
    async def test_rejects_until_hour_out_of_range(self, until_hour):
        with pytest.raises(ToolInputError, match=r"until_hour must be an integer in \[1, 24\]"):
            await handle_call_tool(
                "update_campaign_schedule",
                _args(schedule={
                    "mode": "CUSTOM", "time_zone": "UTC",
                    "rules": [_custom_rule(until_hour=until_hour)],
                }),
            )

    @pytest.mark.asyncio
    async def test_rejects_until_hour_not_greater_than_from_hour(self):
        with pytest.raises(ToolInputError, match="until_hour must be greater than from_hour"):
            await handle_call_tool(
                "update_campaign_schedule",
                _args(schedule={
                    "mode": "CUSTOM", "time_zone": "UTC",
                    "rules": [_custom_rule(from_hour=12, until_hour=12)],
                }),
            )

    @pytest.mark.asyncio
    async def test_rejects_boolean_hour(self):
        with pytest.raises(ToolInputError, match="from_hour must be an integer"):
            await handle_call_tool(
                "update_campaign_schedule",
                _args(schedule={
                    "mode": "CUSTOM", "time_zone": "UTC",
                    "rules": [_custom_rule(from_hour=True)],
                }),
            )

    @pytest.mark.asyncio
    async def test_rejects_rule_not_object(self):
        with pytest.raises(ToolInputError, match=r"rules\[0\] must be an object"):
            await handle_call_tool(
                "update_campaign_schedule",
                _args(schedule={
                    "mode": "CUSTOM", "time_zone": "UTC",
                    "rules": ["MONDAY"],
                }),
            )

    @pytest.mark.asyncio
    async def test_missing_campaign_id_raises(self):
        args = _args()
        del args["campaign_id"]
        with pytest.raises(ToolInputError, match="campaign_id is required"):
            await handle_call_tool("update_campaign_schedule", args)

    @pytest.mark.asyncio
    async def test_numeric_account_id_rejected(self):
        with pytest.raises(ToolInputError, match="search_accounts"):
            await handle_call_tool("update_campaign_schedule", _args(account_id="12345"))


class TestScheduleWire:
    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_posts_to_campaign_endpoint(self, mock_post):
        mock_post.return_value = {"id": "c-123"}

        await handle_call_tool("update_campaign_schedule", _args())

        assert _post_endpoint(mock_post) == "/acme-inc/campaigns/c-123"

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_url_encodes_path_segments(self, mock_post):
        mock_post.return_value = {"id": "c-123"}

        await handle_call_tool(
            "update_campaign_schedule",
            _args(account_id="acme/evil", campaign_id="c/1"),
        )

        assert _post_endpoint(mock_post) == "/acme%2Fevil/campaigns/c%2F1"

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_always_mode_minimal_body(self, mock_post):
        mock_post.return_value = {"id": "c-123"}

        await handle_call_tool(
            "update_campaign_schedule",
            _args(schedule={"mode": "ALWAYS"}),
        )

        assert _post_body(mock_post) == {"activitySchedule": {"mode": "ALWAYS"}}

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_always_mode_passes_through_optional_time_zone(self, mock_post):
        mock_post.return_value = {"id": "c-123"}

        await handle_call_tool(
            "update_campaign_schedule",
            _args(schedule={"mode": "ALWAYS", "time_zone": "America/Los_Angeles"}),
        )

        assert _post_body(mock_post) == {
            "activitySchedule": {"mode": "ALWAYS", "timeZone": "America/Los_Angeles"}
        }

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_custom_mode_camelcases_keys(self, mock_post):
        mock_post.return_value = {"id": "c-123"}

        await handle_call_tool(
            "update_campaign_schedule",
            _args(schedule={
                "mode": "CUSTOM",
                "time_zone": "America/New_York",
                "rules": [
                    {"type": "INCLUDE", "day": "MONDAY", "from_hour": 9, "until_hour": 21},
                    {"type": "EXCLUDE", "day": "SUNDAY", "from_hour": 0, "until_hour": 24},
                ],
            }),
        )

        assert _post_body(mock_post) == {
            "activitySchedule": {
                "mode": "CUSTOM",
                "timeZone": "America/New_York",
                "rules": [
                    {"type": "INCLUDE", "day": "MONDAY", "fromHour": 9, "untilHour": 21},
                    {"type": "EXCLUDE", "day": "SUNDAY", "fromHour": 0, "untilHour": 24},
                ],
            }
        }

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_body_wraps_in_activitySchedule_key(self, mock_post):
        mock_post.return_value = {"id": "c-123"}

        await handle_call_tool("update_campaign_schedule", _args())

        body = _post_body(mock_post)
        assert set(body.keys()) == {"activitySchedule"}


class TestScheduleAnnotations:
    @pytest.mark.asyncio
    async def test_has_destructive_idempotent_open_world_annotations(self):
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        tool = next(t for t in tools if t.name == "update_campaign_schedule")

        assert tool.annotations is not None
        assert tool.annotations.destructiveHint is True
        assert tool.annotations.idempotentHint is True
        assert tool.annotations.openWorldHint is True
