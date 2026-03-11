"""Tests for Prometheus metrics instrumentation."""
import pytest
from unittest.mock import MagicMock, patch
from prometheus_client import CollectorRegistry

from realize.client import _normalize_endpoint
from realize.app_metrics import AppMetrics


# ---------------------------------------------------------------------------
# _normalize_endpoint tests
# ---------------------------------------------------------------------------


class TestNormalizeEndpoint:
    def test_simple_account_campaigns(self):
        assert _normalize_endpoint("/acme-inc/campaigns") == "/{account_id}/campaigns"

    def test_campaign_with_numeric_id(self):
        assert _normalize_endpoint("/acme-inc/campaigns/12345") == "/{account_id}/campaigns/{id}"

    def test_campaign_items(self):
        assert (
            _normalize_endpoint("/acme-inc/campaigns/123/items")
            == "/{account_id}/campaigns/{id}/items"
        )

    def test_campaign_item_with_id(self):
        assert (
            _normalize_endpoint("/acme-inc/campaigns/123/items/456")
            == "/{account_id}/campaigns/{id}/items/{id}"
        )

    def test_advertisers_not_replaced(self):
        assert _normalize_endpoint("/advertisers") == "/advertisers"

    def test_root_path(self):
        assert _normalize_endpoint("/") == "/"

    def test_empty_string(self):
        assert _normalize_endpoint("") == ""

    def test_account_only(self):
        assert _normalize_endpoint("/my-account") == "/{account_id}"

    def test_numeric_account_id(self):
        # When account_id itself is numeric, first segment becomes {account_id},
        # then {id} replacement won't apply because it's already been replaced
        result = _normalize_endpoint("/99999/campaigns")
        assert result == "/{account_id}/campaigns"


# ---------------------------------------------------------------------------
# AppMetrics disabled guard
# ---------------------------------------------------------------------------


class TestAppMetricsDisabled:
    def setup_method(self):
        self.m = AppMetrics(enabled=False)

    def test_all_metric_attrs_are_none(self):
        assert self.m.http_requests_total is None
        assert self.m.http_request_latency_seconds is None
        assert self.m.tool_calls_total is None
        assert self.m.tool_call_latency_seconds is None
        assert self.m.api_requests_total is None
        assert self.m.api_request_latency_seconds is None
        assert self.m.api_errors_total is None

    def test_record_http_request_noop(self):
        # Should not raise
        self.m.record_http_request("GET", "/health", 200, "unknown", "unknown", 0.01)

    def test_record_tool_call_noop(self):
        self.m.record_tool_call("get_campaign", "success", "c", "1", 0.1)

    def test_record_api_request_noop(self):
        self.m.record_api_request("GET", "/{account_id}/campaigns", 200, 0.05)

    def test_record_api_error_noop(self):
        self.m.record_api_error("GET", "/{account_id}/campaigns", "auth_expired")


# ---------------------------------------------------------------------------
# AppMetrics enabled — counters/histograms work
# ---------------------------------------------------------------------------


class TestAppMetricsEnabled:
    def setup_method(self):
        self.registry = CollectorRegistry()
        self.m = AppMetrics(enabled=True, registry=self.registry)

    def test_record_http_request_increments_counter(self):
        self.m.record_http_request("GET", "/health", 200, "unknown", "unknown", 0.01)
        value = self.registry.get_sample_value(
            "realize_mcp_http_requests_total",
            {"method": "GET", "endpoint": "/health", "http_status": "200",
             "client_name": "unknown", "client_version": "unknown"},
        )
        assert value == 1.0

    def test_record_http_request_observes_histogram(self):
        self.m.record_http_request("POST", "/mcp", 200, "test", "1.0", 0.5)
        count = self.registry.get_sample_value(
            "realize_mcp_http_request_latency_seconds_count",
            {"endpoint": "/mcp", "client_name": "test", "client_version": "1.0"},
        )
        assert count == 1.0

    def test_record_tool_call_increments_counter(self):
        self.m.record_tool_call("get_campaign", "success", "cursor", "0.1", 0.2)
        value = self.registry.get_sample_value(
            "realize_mcp_tool_calls_total",
            {"tool_name": "get_campaign", "status": "success",
             "client_name": "cursor", "client_version": "0.1"},
        )
        assert value == 1.0

    def test_record_tool_call_observes_histogram(self):
        self.m.record_tool_call("get_campaign", "success", "cursor", "0.1", 0.2)
        count = self.registry.get_sample_value(
            "realize_mcp_tool_call_latency_seconds_count",
            {"tool_name": "get_campaign",
             "client_name": "cursor", "client_version": "0.1"},
        )
        assert count == 1.0

    def test_record_api_request_increments_counter(self):
        self.m.record_api_request("GET", "/{account_id}/campaigns", 200, 0.1)
        value = self.registry.get_sample_value(
            "realize_mcp_api_requests_total",
            {"method": "GET", "endpoint_pattern": "/{account_id}/campaigns", "http_status": "200"},
        )
        assert value == 1.0

    def test_record_api_request_observes_histogram(self):
        self.m.record_api_request("GET", "/{account_id}/campaigns", 200, 0.1)
        count = self.registry.get_sample_value(
            "realize_mcp_api_request_latency_seconds_count",
            {"method": "GET", "endpoint_pattern": "/{account_id}/campaigns"},
        )
        assert count == 1.0

    def test_record_api_error_increments_counter(self):
        self.m.record_api_error("GET", "/{account_id}/campaigns", "auth_expired")
        value = self.registry.get_sample_value(
            "realize_mcp_api_errors_total",
            {"method": "GET", "endpoint_pattern": "/{account_id}/campaigns",
             "error_type": "auth_expired"},
        )
        assert value == 1.0

    def test_multiple_increments(self):
        for _ in range(5):
            self.m.record_api_request("POST", "/{account_id}/campaigns", 201, 0.05)
        value = self.registry.get_sample_value(
            "realize_mcp_api_requests_total",
            {"method": "POST", "endpoint_pattern": "/{account_id}/campaigns",
             "http_status": "201"},
        )
        assert value == 5.0


# ---------------------------------------------------------------------------
# _get_client_info tests
# ---------------------------------------------------------------------------


class TestGetClientInfo:
    def test_returns_unknown_when_no_session(self):
        from realize.realize_server import _get_client_info, server
        # request_context is not set outside of a request, so AttributeError
        name, version = _get_client_info()
        assert name == "unknown"
        assert version == "unknown"

    def test_returns_real_values_when_available(self):
        from realize.realize_server import _get_client_info, server

        mock_info = MagicMock()
        mock_info.name = "cursor"
        mock_info.version = "0.45.0"
        mock_session = MagicMock()
        mock_session.client_params.clientInfo = mock_info
        mock_ctx = MagicMock()
        mock_ctx.session = mock_session

        with patch.object(type(server), "request_context", new_callable=lambda: property(lambda self: mock_ctx)):
            name, version = _get_client_info()
        assert name == "cursor"
        assert version == "0.45.0"


# ---------------------------------------------------------------------------
# /metrics endpoint test
# ---------------------------------------------------------------------------


class TestMetricsEndpoint:
    @pytest.fixture
    def app(self):
        """Create a test Starlette app with the metrics_handler."""
        from realize.transports.app import metrics_handler
        from starlette.applications import Starlette
        from starlette.routing import Route
        from starlette.testclient import TestClient

        test_app = Starlette(routes=[
            Route("/metrics", metrics_handler, methods=["GET"]),
        ])
        return TestClient(test_app)

    def test_metrics_endpoint_returns_200(self, app):
        response = app.get("/metrics")
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]

    def test_metrics_endpoint_contains_metric_names(self, app):
        from realize.app_metrics import metrics
        if not metrics.enabled:
            pytest.skip("Metrics not enabled in test environment")

        response = app.get("/metrics")
        body = response.text
        assert "realize_mcp_http_requests_total" in body or "realize_mcp_api_requests_total" in body


# ---------------------------------------------------------------------------
# MetricsMiddleware test
# ---------------------------------------------------------------------------


class TestMetricsMiddleware:
    def test_middleware_records_request(self):
        from prometheus_client import CollectorRegistry
        from realize.transports.middleware import MetricsMiddleware
        from starlette.applications import Starlette
        from starlette.responses import PlainTextResponse
        from starlette.routing import Route
        from starlette.testclient import TestClient

        registry = CollectorRegistry()
        test_metrics = AppMetrics(enabled=True, registry=registry)

        async def hello(request):
            return PlainTextResponse("ok")

        inner_app = Starlette(routes=[Route("/hello", hello)])
        wrapped = MetricsMiddleware(inner_app)

        with patch("realize.transports.middleware.metrics", test_metrics):
            client = TestClient(wrapped)
            resp = client.get("/hello")
            assert resp.status_code == 200

        count = registry.get_sample_value(
            "realize_mcp_http_requests_total",
            {"method": "GET", "endpoint": "/hello", "http_status": "200",
             "client_name": "unknown", "client_version": "unknown"},
        )
        assert count == 1.0

    def test_middleware_skips_metrics_endpoint(self):
        from realize.transports.middleware import MetricsMiddleware
        from starlette.applications import Starlette
        from starlette.responses import PlainTextResponse
        from starlette.routing import Route
        from starlette.testclient import TestClient

        registry = CollectorRegistry()
        test_metrics = AppMetrics(enabled=True, registry=registry)

        async def metrics_page(request):
            return PlainTextResponse("metrics")

        inner_app = Starlette(routes=[Route("/metrics", metrics_page)])
        wrapped = MetricsMiddleware(inner_app)

        with patch("realize.transports.middleware.metrics", test_metrics):
            client = TestClient(wrapped)
            resp = client.get("/metrics")
            assert resp.status_code == 200

        count = registry.get_sample_value(
            "realize_mcp_http_requests_total",
            {"method": "GET", "endpoint": "/metrics", "http_status": "200",
             "client_name": "unknown", "client_version": "unknown"},
        )
        # Should be None (not recorded) since /metrics is skipped
        assert count is None
