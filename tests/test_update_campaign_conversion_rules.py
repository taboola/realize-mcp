"""Tests for the update_campaign_conversion_rules write tool."""
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
        "conversion_rules": [{"id": "rule_purchase"}],
    }
    base.update(overrides)
    return base


class TestConversionRulesValidation:
    @pytest.mark.asyncio
    async def test_numeric_account_id_rejected(self):
        with pytest.raises(ToolInputError, match="search_accounts"):
            await handle_call_tool(
                "update_campaign_conversion_rules", _args(account_id="12345")
            )

    @pytest.mark.asyncio
    async def test_missing_campaign_id_raises(self):
        args = _args()
        del args["campaign_id"]
        with pytest.raises(ToolInputError, match="campaign_id is required"):
            await handle_call_tool("update_campaign_conversion_rules", args)

    @pytest.mark.asyncio
    async def test_rejects_conversion_rules_not_list(self):
        with pytest.raises(ToolInputError, match="conversion_rules must be a list"):
            await handle_call_tool(
                "update_campaign_conversion_rules",
                _args(conversion_rules={"id": "rule_purchase"}),
            )

    @pytest.mark.asyncio
    async def test_rejects_conversion_rules_missing(self):
        args = _args()
        del args["conversion_rules"]
        with pytest.raises(ToolInputError, match="conversion_rules must be a list"):
            await handle_call_tool("update_campaign_conversion_rules", args)

    @pytest.mark.asyncio
    async def test_rejects_item_not_object(self):
        with pytest.raises(ToolInputError, match=r"conversion_rules\[0\] must be an object"):
            await handle_call_tool(
                "update_campaign_conversion_rules",
                _args(conversion_rules=["rule_purchase"]),
            )

    @pytest.mark.asyncio
    async def test_rejects_missing_id(self):
        with pytest.raises(ToolInputError, match=r"conversion_rules\[0\].id must be a non-empty string"):
            await handle_call_tool(
                "update_campaign_conversion_rules",
                _args(conversion_rules=[{}]),
            )

    @pytest.mark.asyncio
    async def test_rejects_empty_id(self):
        with pytest.raises(ToolInputError, match=r"conversion_rules\[0\].id must be a non-empty string"):
            await handle_call_tool(
                "update_campaign_conversion_rules",
                _args(conversion_rules=[{"id": ""}]),
            )

    @pytest.mark.asyncio
    async def test_rejects_non_string_id(self):
        with pytest.raises(ToolInputError, match=r"conversion_rules\[0\].id must be a non-empty string"):
            await handle_call_tool(
                "update_campaign_conversion_rules",
                _args(conversion_rules=[{"id": 12345}]),
            )

    @pytest.mark.asyncio
    async def test_rejects_duplicate_id(self):
        with pytest.raises(ToolInputError, match=r"conversion_rules\[1\].id duplicate"):
            await handle_call_tool(
                "update_campaign_conversion_rules",
                _args(conversion_rules=[{"id": "rule_a"}, {"id": "rule_a"}]),
            )

    @pytest.mark.asyncio
    async def test_reports_index_in_error_for_second_item(self):
        with pytest.raises(ToolInputError, match=r"conversion_rules\[1\].id must be a non-empty string"):
            await handle_call_tool(
                "update_campaign_conversion_rules",
                _args(conversion_rules=[{"id": "rule_a"}, {"id": ""}]),
            )


class TestConversionRulesWire:
    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_posts_to_campaign_endpoint(self, mock_post):
        mock_post.return_value = {"id": "c-123"}

        await handle_call_tool("update_campaign_conversion_rules", _args())

        assert _post_endpoint(mock_post) == "/acme-inc/campaigns/c-123"

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_url_encodes_path_segments(self, mock_post):
        mock_post.return_value = {"id": "c-123"}

        await handle_call_tool(
            "update_campaign_conversion_rules",
            _args(account_id="acme/evil", campaign_id="c/1"),
        )

        assert _post_endpoint(mock_post) == "/acme%2Fevil/campaigns/c%2F1"

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_body_wraps_in_conversion_rules_key(self, mock_post):
        mock_post.return_value = {"id": "c-123"}

        await handle_call_tool("update_campaign_conversion_rules", _args())

        body = _post_body(mock_post)
        assert set(body.keys()) == {"conversion_rules"}

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_body_passes_id_refs(self, mock_post):
        mock_post.return_value = {"id": "c-123"}

        await handle_call_tool(
            "update_campaign_conversion_rules",
            _args(conversion_rules=[{"id": "rule_a"}, {"id": "rule_b"}]),
        )

        assert _post_body(mock_post) == {
            "conversion_rules": [{"id": "rule_a"}, {"id": "rule_b"}]
        }

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_empty_list_passes_through(self, mock_post):
        mock_post.return_value = {"id": "c-123"}

        await handle_call_tool(
            "update_campaign_conversion_rules",
            _args(conversion_rules=[]),
        )

        assert _post_body(mock_post) == {"conversion_rules": []}

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_extra_keys_stripped_from_wire(self, mock_post):
        mock_post.return_value = {"id": "c-123"}

        await handle_call_tool(
            "update_campaign_conversion_rules",
            _args(conversion_rules=[
                {"id": "rule_a", "display_name": "ignored", "type": "BASIC"},
            ]),
        )

        assert _post_body(mock_post) == {"conversion_rules": [{"id": "rule_a"}]}


class TestConversionRulesAnnotations:
    @pytest.mark.asyncio
    async def test_has_destructive_idempotent_open_world_annotations(self):
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        tool = next(t for t in tools if t.name == "update_campaign_conversion_rules")

        assert tool.annotations is not None
        assert tool.annotations.destructiveHint is True
        assert tool.annotations.idempotentHint is True
        assert tool.annotations.openWorldHint is True
