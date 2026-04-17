"""Tests for URL-encoding of path parameters (SAY-04).

Verifies that account_id, campaign_id, and item_id values are URL-encoded
per-segment before being interpolated into upstream Realize API URLs.
Protects against path manipulation via `/`, `?`, `#`, and other reserved
characters, and bounds Prometheus label cardinality downstream.
"""
import pytest
from unittest.mock import AsyncMock, patch

from realize.realize_server import handle_call_tool
from realize.client import _normalize_endpoint


def _get_endpoint_arg(mock_get):
    """Extract the endpoint (first positional arg) passed to client.get."""
    args, _kwargs = mock_get.call_args
    return args[0]


class TestCampaignHandlersEncoding:
    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.get', new_callable=AsyncMock)
    async def test_get_all_campaigns_encodes_slash_in_account_id(self, mock_get):
        mock_get.return_value = {"results": [], "metadata": {"total": 0}}

        await handle_call_tool("get_all_campaigns", {"account_id": "acme/evil"})

        assert _get_endpoint_arg(mock_get) == "/acme%2Fevil/campaigns"

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.get', new_callable=AsyncMock)
    async def test_get_all_campaigns_preserves_alphanumeric(self, mock_get):
        mock_get.return_value = {"results": [], "metadata": {"total": 0}}

        await handle_call_tool("get_all_campaigns", {"account_id": "acme-inc"})

        assert _get_endpoint_arg(mock_get) == "/acme-inc/campaigns"

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.get', new_callable=AsyncMock)
    async def test_get_all_campaigns_preserves_dots(self, mock_get):
        mock_get.return_value = {"results": [], "metadata": {"total": 0}}

        await handle_call_tool("get_all_campaigns", {"account_id": "acct.1"})

        # "." is unreserved in RFC 3986 and is preserved by quote()
        assert _get_endpoint_arg(mock_get) == "/acct.1/campaigns"

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.get', new_callable=AsyncMock)
    async def test_get_all_campaigns_encodes_unicode(self, mock_get):
        mock_get.return_value = {"results": [], "metadata": {"total": 0}}

        await handle_call_tool("get_all_campaigns", {"account_id": "tëst"})

        # UTF-8 percent-encoded
        assert _get_endpoint_arg(mock_get) == "/t%C3%ABst/campaigns"

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.get', new_callable=AsyncMock)
    async def test_get_campaign_encodes_both_ids(self, mock_get):
        mock_get.return_value = {"id": "x"}

        await handle_call_tool("get_campaign", {
            "account_id": "acct.1",
            "campaign_id": "123?x=1",
        })

        assert _get_endpoint_arg(mock_get) == "/acct.1/campaigns/123%3Fx%3D1"

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.get', new_callable=AsyncMock)
    async def test_get_campaign_items_encodes_both_ids(self, mock_get):
        mock_get.return_value = {"results": []}

        await handle_call_tool("get_campaign_items", {
            "account_id": "a/b",
            "campaign_id": "c#d",
        })

        assert _get_endpoint_arg(mock_get) == "/a%2Fb/campaigns/c%23d/items/"

    @pytest.mark.asyncio
    @patch('realize.tools.campaign_handlers.client.get', new_callable=AsyncMock)
    async def test_get_campaign_item_encodes_all_three_ids(self, mock_get):
        mock_get.return_value = {"id": "x"}

        await handle_call_tool("get_campaign_item", {
            "account_id": "a/b",
            "campaign_id": "c#d",
            "item_id": "e?f",
        })

        assert _get_endpoint_arg(mock_get) == "/a%2Fb/campaigns/c%23d/items/e%3Ff"


class TestReportHandlersEncoding:
    def _base_args(self, account_id):
        return {
            "account_id": account_id,
            "start_date": "2025-01-01",
            "end_date": "2025-01-02",
        }

    @pytest.mark.asyncio
    @patch('realize.tools.report_handlers.client.get', new_callable=AsyncMock)
    async def test_campaign_breakdown_report_encodes_account_id(self, mock_get):
        mock_get.return_value = {"results": [], "metadata": {}}

        await handle_call_tool("get_campaign_breakdown_report", self._base_args("x/y"))

        assert _get_endpoint_arg(mock_get) == (
            "/x%2Fy/reports/campaign-summary/dimensions/campaign_breakdown"
        )

    @pytest.mark.asyncio
    @patch('realize.tools.report_handlers.client.get', new_callable=AsyncMock)
    async def test_campaign_site_day_breakdown_report_encodes_account_id(self, mock_get):
        mock_get.return_value = {"results": [], "metadata": {}}

        await handle_call_tool(
            "get_campaign_site_day_breakdown_report", self._base_args("x/y")
        )

        assert _get_endpoint_arg(mock_get) == (
            "/x%2Fy/reports/campaign-summary/dimensions/campaign_site_day_breakdown"
        )

    @pytest.mark.asyncio
    @patch('realize.tools.report_handlers.client.get', new_callable=AsyncMock)
    async def test_top_campaign_content_report_encodes_account_id(self, mock_get):
        mock_get.return_value = {"results": [], "metadata": {}}

        await handle_call_tool(
            "get_top_campaign_content_report", self._base_args("x/y")
        )

        assert _get_endpoint_arg(mock_get) == (
            "/x%2Fy/reports/top-campaign-content/dimensions/item_breakdown"
        )

    @pytest.mark.asyncio
    @patch('realize.tools.report_handlers.client.get', new_callable=AsyncMock)
    async def test_campaign_history_report_encodes_account_id(self, mock_get):
        mock_get.return_value = {"results": [], "metadata": {}}

        await handle_call_tool("get_campaign_history_report", self._base_args("x/y"))

        assert _get_endpoint_arg(mock_get) == (
            "/x%2Fy/reports/campaign-history/dimensions/by_account"
        )


class TestNormalizeEndpointWithEncodedSegment:
    """Ensure that once path params are URL-encoded, _normalize_endpoint
    collapses the attacker-controlled segment into the {account_id}
    placeholder instead of leaking raw text into Prometheus labels."""

    def test_encoded_slash_stays_in_first_segment(self):
        # Without encoding, "/acme/evil/campaigns" would split into 3
        # segments and "evil" would leak into the label. With encoding,
        # the slash is %2F and the first segment normalizes cleanly.
        assert (
            _normalize_endpoint("/acme%2Fevil/campaigns")
            == "/{account_id}/campaigns"
        )

    def test_encoded_question_mark_stays_in_segment(self):
        assert (
            _normalize_endpoint("/acct%3Fx%3D1/campaigns")
            == "/{account_id}/campaigns"
        )
