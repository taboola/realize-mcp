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
        assert self.m.client_connections_total is None

    def test_record_http_request_noop(self):
        # Should not raise
        self.m.record_http_request("GET", "/health", 200, 0.01)

    def test_record_tool_call_noop(self):
        self.m.record_tool_call("get_campaign", "success", 0.1)

    def test_record_client_connection_noop(self):
        self.m.record_client_connection("cursor", "0.45.0")

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
        self.m.record_http_request("GET", "/health", 200, 0.01)
        value = self.registry.get_sample_value(
            "realize_mcp_http_requests_total",
            {"method": "GET", "endpoint": "/health", "http_status": "200"},
        )
        assert value == 1.0

    def test_record_http_request_observes_histogram(self):
        self.m.record_http_request("POST", "/mcp", 200, 0.5)
        count = self.registry.get_sample_value(
            "realize_mcp_http_request_latency_seconds_count",
            {"endpoint": "/mcp"},
        )
        assert count == 1.0

    def test_record_tool_call_increments_counter(self):
        self.m.record_tool_call("get_campaign", "success", 0.2)
        value = self.registry.get_sample_value(
            "realize_mcp_tool_calls_total",
            {"tool_name": "get_campaign", "status": "success"},
        )
        assert value == 1.0

    def test_record_tool_call_observes_histogram(self):
        self.m.record_tool_call("get_campaign", "success", 0.2)
        count = self.registry.get_sample_value(
            "realize_mcp_tool_call_latency_seconds_count",
            {"tool_name": "get_campaign"},
        )
        assert count == 1.0

    def test_record_client_connection_increments_counter(self):
        self.m.record_client_connection("cursor", "0.45.0")
        value = self.registry.get_sample_value(
            "realize_mcp_client_connections_total",
            {"client_name": "cursor", "client_version": "0.45.0"},
        )
        assert value == 1.0

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
# /metrics endpoint test
# ---------------------------------------------------------------------------


class TestMetricsEndpoint:
    @pytest.fixture
    def app(self):
        """Create a test Starlette app with the metrics_handler."""
        from realize.transports.metrics_server import metrics_handler
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
# HTTP label normalizer tests (cardinality guards)
# ---------------------------------------------------------------------------


class TestNormalizeHttpPath:
    def setup_method(self):
        from realize.transports.middleware import _normalize_http_path
        self.fn = _normalize_http_path

    def test_health(self):
        assert self.fn("/health") == "/health"

    def test_register(self):
        assert self.fn("/register") == "/register"

    def test_mcp(self):
        assert self.fn("/mcp") == "/mcp"

    def test_wellknown_protected_resource_base(self):
        assert (
            self.fn("/.well-known/oauth-protected-resource")
            == "/.well-known/oauth-protected-resource"
        )

    def test_wellknown_protected_resource_with_tail(self):
        assert (
            self.fn("/.well-known/oauth-protected-resource/tenant-acme")
            == "/.well-known/oauth-protected-resource"
        )
        assert (
            self.fn("/.well-known/oauth-protected-resource/customer-123/mcp")
            == "/.well-known/oauth-protected-resource"
        )

    def test_wellknown_authorization_server_base(self):
        assert (
            self.fn("/.well-known/oauth-authorization-server")
            == "/.well-known/oauth-authorization-server"
        )

    def test_wellknown_authorization_server_with_tail(self):
        assert (
            self.fn("/.well-known/oauth-authorization-server/tenant-x")
            == "/.well-known/oauth-authorization-server"
        )

    def test_unknown_paths_collapse_to_other(self):
        unknown = [
            "/wp-admin",
            "/phpmyadmin",
            "/.env",
            "/foo/bar",
            "/",
            "",
            # non-OAuth /.well-known probes scanners commonly send
            "/.well-known/matrix/client",
            "/.well-known/matrix/server",
            "/.well-known/security.txt",
            "/.well-known/caldav",
            "/.well-known/webfinger",
            "/.well-known/host-meta",
            # prefix boundary: must not be mis-bucketed into OAuth label
            "/.well-known/oauth-protected-resource-admin",
            "/.well-known/oauth-authorization-server-typo",
        ]
        for p in unknown:
            assert self.fn(p) == "other", p

    def test_trailing_slash_is_unknown(self):
        # Strict allowlist: /health/ is not /health
        assert self.fn("/health/") == "other"

    def test_mcp_subpath_is_unknown(self):
        # /mcp is a bare Route; sub-paths 404
        assert self.fn("/mcp/foo") == "other"


class TestNormalizeHttpMethod:
    def setup_method(self):
        from realize.transports.middleware import _normalize_http_method
        self.fn = _normalize_http_method

    def test_standard_methods_pass_through(self):
        for m in ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]:
            assert self.fn(m) == m

    def test_lowercase_not_allowed(self):
        # ASGI always uppercases; lowercase would be anomalous
        assert self.fn("get") == "other"

    def test_exotic_methods_become_other(self):
        for m in ["PROPFIND", "TRACE", "CONNECT", "FOOBAR", ""]:
            assert self.fn(m) == "other", m

    def test_garbage_bytes_become_other(self):
        # Scanner TLS probes on plain HTTP can produce junk method tokens
        assert self.fn("\x16\x03\x01") == "other"


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

        async def health(request):
            return PlainTextResponse("ok")

        inner_app = Starlette(routes=[Route("/health", health)])
        wrapped = MetricsMiddleware(inner_app)

        with patch("realize.transports.middleware.metrics", test_metrics):
            client = TestClient(wrapped)
            resp = client.get("/health")
            assert resp.status_code == 200

        count = registry.get_sample_value(
            "realize_mcp_http_requests_total",
            {"method": "GET", "endpoint": "/health", "http_status": "200"},
        )
        assert count == 1.0

    def test_middleware_normalizes_wellknown_path(self):
        from prometheus_client import CollectorRegistry
        from realize.transports.middleware import MetricsMiddleware
        from starlette.applications import Starlette
        from starlette.responses import PlainTextResponse
        from starlette.routing import Route
        from starlette.testclient import TestClient

        registry = CollectorRegistry()
        test_metrics = AppMetrics(enabled=True, registry=registry)

        async def handler(request):
            return PlainTextResponse("ok")

        inner_app = Starlette(routes=[
            Route(
                "/.well-known/oauth-protected-resource/{path:path}",
                handler,
                methods=["GET"],
            ),
        ])
        wrapped = MetricsMiddleware(inner_app)

        with patch("realize.transports.middleware.metrics", test_metrics):
            client = TestClient(wrapped)
            client.get("/.well-known/oauth-protected-resource/tenant-x")
            client.get("/.well-known/oauth-protected-resource/tenant-y/mcp")

        count = registry.get_sample_value(
            "realize_mcp_http_requests_total",
            {
                "method": "GET",
                "endpoint": "/.well-known/oauth-protected-resource",
                "http_status": "200",
            },
        )
        assert count == 2.0

    def test_middleware_unknown_path_uses_other(self):
        from prometheus_client import CollectorRegistry
        from realize.transports.middleware import MetricsMiddleware
        from starlette.applications import Starlette
        from starlette.testclient import TestClient

        registry = CollectorRegistry()
        test_metrics = AppMetrics(enabled=True, registry=registry)

        inner_app = Starlette(routes=[])
        wrapped = MetricsMiddleware(inner_app)

        with patch("realize.transports.middleware.metrics", test_metrics):
            client = TestClient(wrapped)
            client.get("/wp-admin")

        count = registry.get_sample_value(
            "realize_mcp_http_requests_total",
            {"method": "GET", "endpoint": "other", "http_status": "404"},
        )
        assert count == 1.0

    def test_middleware_unknown_method_uses_other(self):
        from prometheus_client import CollectorRegistry
        from realize.transports.middleware import MetricsMiddleware
        from starlette.applications import Starlette
        from starlette.responses import PlainTextResponse
        from starlette.routing import Route
        from starlette.testclient import TestClient

        registry = CollectorRegistry()
        test_metrics = AppMetrics(enabled=True, registry=registry)

        async def handler(request):
            return PlainTextResponse("ok")

        # Accept any method so we can drive an exotic one
        inner_app = Starlette(routes=[
            Route("/mcp", handler, methods=["PROPFIND"]),
        ])
        wrapped = MetricsMiddleware(inner_app)

        with patch("realize.transports.middleware.metrics", test_metrics):
            client = TestClient(wrapped)
            resp = client.request("PROPFIND", "/mcp")
            assert resp.status_code == 200

        count = registry.get_sample_value(
            "realize_mcp_http_requests_total",
            {"method": "other", "endpoint": "/mcp", "http_status": "200"},
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
            {"method": "GET", "endpoint": "/metrics", "http_status": "200"},
        )
        # Should be None (not recorded) since /metrics is skipped
        assert count is None


# ---------------------------------------------------------------------------
# _extract_client_info_from_body tests
# ---------------------------------------------------------------------------


class TestExtractClientInfoFromBody:
    def setup_method(self):
        from realize.transports.streamable_http_server import StreamableHTTPEndpoint
        self.extract = StreamableHTTPEndpoint._extract_client_info_from_body

    def test_extracts_from_initialize(self):
        import json
        body = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "clientInfo": {"name": "cursor", "version": "0.45.0"},
                "protocolVersion": "2025-03-26",
                "capabilities": {},
            },
        }).encode()
        result = self.extract(body)
        assert result == ("cursor", "0.45.0")

    def test_ignores_non_initialize(self):
        import json
        body = json.dumps({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "get_campaign"},
        }).encode()
        assert self.extract(body) is None

    def test_handles_empty_body(self):
        assert self.extract(b"") is None

    def test_handles_malformed_json(self):
        assert self.extract(b"not json at all") is None

    def test_missing_client_name_returns_none(self):
        import json
        body = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "clientInfo": {"version": "0.45.0"},
                "protocolVersion": "2025-03-26",
            },
        }).encode()
        assert self.extract(body) is None

    def test_missing_version_defaults_to_question_mark(self):
        import json
        body = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "clientInfo": {"name": "cursor"},
                "protocolVersion": "2025-03-26",
            },
        }).encode()
        result = self.extract(body)
        assert result == ("cursor", "?")
