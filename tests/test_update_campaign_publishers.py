"""Tests for the update_campaign_publishers write tool."""
import math

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
        "publisher_targeting": {"type": "INCLUDE", "value": ["pub_alpha"]},
    }
    base.update(overrides)
    return base


class TestPublishersBaseValidation:
    @pytest.mark.asyncio
    async def test_missing_campaign_id_raises(self):
        args = _args()
        del args["campaign_id"]
        with pytest.raises(ToolInputError, match="campaign_id is required"):
            await handle_call_tool("update_campaign_publishers", args)

    @pytest.mark.asyncio
    async def test_numeric_account_id_rejected(self):
        with pytest.raises(ToolInputError, match="search_accounts"):
            await handle_call_tool("update_campaign_publishers", _args(account_id="12345"))

    @pytest.mark.asyncio
    async def test_no_fields_supplied_rejected(self):
        with pytest.raises(ToolInputError, match="at least one of"):
            await handle_call_tool(
                "update_campaign_publishers",
                {"account_id": "acme-inc", "campaign_id": "c-123"},
            )


class TestPublisherTargetingValidation:
    @pytest.mark.asyncio
    async def test_targeting_must_be_object(self):
        with pytest.raises(ToolInputError, match="publisher_targeting must be an object"):
            await handle_call_tool(
                "update_campaign_publishers",
                _args(publisher_targeting=["INCLUDE", ["pub_alpha"]]),
            )

    @pytest.mark.asyncio
    async def test_invalid_type(self):
        with pytest.raises(ToolInputError, match="publisher_targeting.type"):
            await handle_call_tool(
                "update_campaign_publishers",
                _args(publisher_targeting={"type": "ONLY", "value": ["pub_alpha"]}),
            )

    @pytest.mark.asyncio
    async def test_value_must_be_list_of_strings(self):
        with pytest.raises(ToolInputError, match="publisher_targeting.value must be a list"):
            await handle_call_tool(
                "update_campaign_publishers",
                _args(publisher_targeting={"type": "INCLUDE", "value": [1, 2]}),
            )

    @pytest.mark.asyncio
    async def test_all_with_nonempty_value_rejected(self):
        with pytest.raises(ToolInputError, match="empty when type=ALL"):
            await handle_call_tool(
                "update_campaign_publishers",
                _args(publisher_targeting={"type": "ALL", "value": ["pub_alpha"]}),
            )

    @pytest.mark.asyncio
    async def test_include_with_empty_value_rejected(self):
        with pytest.raises(ToolInputError, match="non-empty when type=INCLUDE"):
            await handle_call_tool(
                "update_campaign_publishers",
                _args(publisher_targeting={"type": "INCLUDE", "value": []}),
            )

    @pytest.mark.asyncio
    async def test_empty_string_value_rejected(self):
        with pytest.raises(ToolInputError, match="publisher_targeting.value must be a list"):
            await handle_call_tool(
                "update_campaign_publishers",
                _args(publisher_targeting={"type": "INCLUDE", "value": [""]}),
            )


class TestPublisherGroupsTargetingValidation:
    @pytest.mark.asyncio
    async def test_invalid_type(self):
        with pytest.raises(ToolInputError, match="publisher_groups_targeting.type"):
            await handle_call_tool(
                "update_campaign_publishers",
                _args(
                    publisher_targeting=None,
                    publisher_groups_targeting={"type": "ONLY", "value": ["g1"]},
                ),
            )

    @pytest.mark.asyncio
    async def test_value_must_be_list_of_strings(self):
        with pytest.raises(ToolInputError, match="publisher_groups_targeting.value must be a list"):
            await handle_call_tool(
                "update_campaign_publishers",
                _args(
                    publisher_targeting=None,
                    publisher_groups_targeting={"type": "INCLUDE", "value": [123]},
                ),
            )

    @pytest.mark.asyncio
    async def test_all_with_nonempty_value_rejected(self):
        with pytest.raises(ToolInputError, match="empty when type=ALL"):
            await handle_call_tool(
                "update_campaign_publishers",
                _args(
                    publisher_targeting=None,
                    publisher_groups_targeting={"type": "ALL", "value": ["g1"]},
                ),
            )


class TestPublisherBidModifierValidation:
    @pytest.mark.asyncio
    async def test_must_be_object(self):
        with pytest.raises(ToolInputError, match="publisher_bid_modifier must be an object"):
            await handle_call_tool(
                "update_campaign_publishers",
                _args(publisher_targeting=None, publisher_bid_modifier=[]),
            )

    @pytest.mark.asyncio
    async def test_values_must_be_list(self):
        with pytest.raises(ToolInputError, match="publisher_bid_modifier.values must be a list"):
            await handle_call_tool(
                "update_campaign_publishers",
                _args(publisher_targeting=None, publisher_bid_modifier={"values": "x"}),
            )

    @pytest.mark.asyncio
    async def test_entry_must_be_object(self):
        with pytest.raises(ToolInputError, match=r"publisher_bid_modifier.values\[0\] must be an object"):
            await handle_call_tool(
                "update_campaign_publishers",
                _args(publisher_targeting=None, publisher_bid_modifier={"values": ["nope"]}),
            )

    @pytest.mark.asyncio
    async def test_target_required_non_empty(self):
        with pytest.raises(ToolInputError, match=r"values\[0\].target must be a non-empty string"):
            await handle_call_tool(
                "update_campaign_publishers",
                _args(
                    publisher_targeting=None,
                    publisher_bid_modifier={"values": [{"target": "", "cpc_modification": 1.0}]},
                ),
            )

    @pytest.mark.asyncio
    async def test_cpc_modification_must_be_number(self):
        with pytest.raises(ToolInputError, match=r"values\[0\].cpc_modification must be a number"):
            await handle_call_tool(
                "update_campaign_publishers",
                _args(
                    publisher_targeting=None,
                    publisher_bid_modifier={
                        "values": [{"target": "pub_a", "cpc_modification": "1.0"}]
                    },
                ),
            )

    @pytest.mark.asyncio
    async def test_cpc_modification_rejects_bool(self):
        with pytest.raises(ToolInputError, match=r"values\[0\].cpc_modification must be a number"):
            await handle_call_tool(
                "update_campaign_publishers",
                _args(
                    publisher_targeting=None,
                    publisher_bid_modifier={
                        "values": [{"target": "pub_a", "cpc_modification": True}]
                    },
                ),
            )

    @pytest.mark.asyncio
    async def test_cpc_modification_must_be_finite(self):
        with pytest.raises(ToolInputError, match=r"values\[0\].cpc_modification must be finite"):
            await handle_call_tool(
                "update_campaign_publishers",
                _args(
                    publisher_targeting=None,
                    publisher_bid_modifier={
                        "values": [{"target": "pub_a", "cpc_modification": math.inf}]
                    },
                ),
            )

    @pytest.mark.asyncio
    async def test_cpc_modification_rejects_nan(self):
        with pytest.raises(ToolInputError, match=r"values\[0\].cpc_modification must be finite"):
            await handle_call_tool(
                "update_campaign_publishers",
                _args(
                    publisher_targeting=None,
                    publisher_bid_modifier={
                        "values": [{"target": "pub_a", "cpc_modification": math.nan}]
                    },
                ),
            )

    @pytest.mark.asyncio
    async def test_duplicate_target_rejected(self):
        with pytest.raises(ToolInputError, match="duplicates entry"):
            await handle_call_tool(
                "update_campaign_publishers",
                _args(
                    publisher_targeting=None,
                    publisher_bid_modifier={
                        "values": [
                            {"target": "pub_a", "cpc_modification": 1.0},
                            {"target": "pub_a", "cpc_modification": 1.5},
                        ]
                    },
                ),
            )


class TestPublishersWireMapping:
    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_publisher_targeting_maps_to_wire(self, mock_post):
        mock_post.return_value = {"id": "c-123"}

        await handle_call_tool(
            "update_campaign_publishers",
            _args(publisher_targeting={"type": "EXCLUDE", "value": ["pub_a", "pub_b"]}),
        )

        assert _post_body(mock_post) == {
            "publisher_targeting": {"type": "EXCLUDE", "value": ["pub_a", "pub_b"]}
        }

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_publisher_groups_targeting_maps_to_wire(self, mock_post):
        mock_post.return_value = {"id": "c-123"}

        await handle_call_tool(
            "update_campaign_publishers",
            _args(
                publisher_targeting=None,
                publisher_groups_targeting={"type": "INCLUDE", "value": ["g1"]},
            ),
        )

        assert _post_body(mock_post) == {
            "publisher_groups_targeting": {"type": "INCLUDE", "value": ["g1"]}
        }

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_bid_modifier_passes_cpc_modification(self, mock_post):
        mock_post.return_value = {"id": "c-123"}

        await handle_call_tool(
            "update_campaign_publishers",
            _args(
                publisher_targeting=None,
                publisher_bid_modifier={
                    "values": [
                        {"target": "pub_a", "cpc_modification": 1.25},
                        {"target": "pub_b", "cpc_modification": 0.8},
                    ]
                },
            ),
        )

        assert _post_body(mock_post) == {
            "publisher_bid_modifier": {
                "values": [
                    {"target": "pub_a", "cpc_modification": 1.25},
                    {"target": "pub_b", "cpc_modification": 0.8},
                ]
            }
        }

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_bid_modifier_empty_values_clears(self, mock_post):
        mock_post.return_value = {"id": "c-123"}

        await handle_call_tool(
            "update_campaign_publishers",
            _args(
                publisher_targeting=None,
                publisher_bid_modifier={"values": []},
            ),
        )

        assert _post_body(mock_post) == {"publisher_bid_modifier": {"values": []}}

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_clear_with_all_sends_empty_value(self, mock_post):
        mock_post.return_value = {"id": "c-123"}

        await handle_call_tool(
            "update_campaign_publishers",
            _args(publisher_targeting={"type": "ALL", "value": []}),
        )

        assert _post_body(mock_post) == {
            "publisher_targeting": {"type": "ALL", "value": []}
        }

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_combined_fields_in_one_payload(self, mock_post):
        mock_post.return_value = {"id": "c-123"}

        await handle_call_tool(
            "update_campaign_publishers",
            _args(
                publisher_targeting={"type": "EXCLUDE", "value": ["pub_a"]},
                publisher_groups_targeting={"type": "INCLUDE", "value": ["g1"]},
                publisher_bid_modifier={
                    "values": [{"target": "pub_b", "cpc_modification": 1.5}]
                },
            ),
        )

        assert _post_body(mock_post) == {
            "publisher_targeting": {"type": "EXCLUDE", "value": ["pub_a"]},
            "publisher_groups_targeting": {"type": "INCLUDE", "value": ["g1"]},
            "publisher_bid_modifier": {
                "values": [{"target": "pub_b", "cpc_modification": 1.5}]
            },
        }

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_posts_to_campaign_endpoint(self, mock_post):
        mock_post.return_value = {"id": "c-123"}

        await handle_call_tool("update_campaign_publishers", _args())

        assert _post_endpoint(mock_post) == "/acme-inc/campaigns/c-123"

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_url_encodes_path_segments(self, mock_post):
        mock_post.return_value = {"id": "c-123"}

        await handle_call_tool(
            "update_campaign_publishers",
            _args(account_id="acme/evil", campaign_id="c/1"),
        )

        assert _post_endpoint(mock_post) == "/acme%2Fevil/campaigns/c%2F1"

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.post', new_callable=AsyncMock)
    async def test_int_cpc_modification_normalized_to_float(self, mock_post):
        mock_post.return_value = {"id": "c-123"}

        await handle_call_tool(
            "update_campaign_publishers",
            _args(
                publisher_targeting=None,
                publisher_bid_modifier={
                    "values": [{"target": "pub_a", "cpc_modification": 1}]
                },
            ),
        )

        body = _post_body(mock_post)
        cpc = body["publisher_bid_modifier"]["values"][0]["cpc_modification"]
        assert isinstance(cpc, float)
        assert cpc == 1.0


class TestPublishersAnnotations:
    @pytest.mark.asyncio
    async def test_has_destructive_idempotent_open_world_annotations(self):
        from realize.realize_server import handle_list_tools

        tools = await handle_list_tools()
        tool = next(t for t in tools if t.name == "update_campaign_publishers")

        assert tool.annotations is not None
        assert tool.annotations.destructiveHint is True
        assert tool.annotations.idempotentHint is True
        assert tool.annotations.openWorldHint is True
