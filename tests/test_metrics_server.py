"""Tests for the dedicated metrics server."""
import pytest
from starlette.testclient import TestClient

from realize.transports.metrics_server import create_metrics_app


@pytest.fixture
def client():
    return TestClient(create_metrics_app())


class TestMetricsServer:

    def test_root_returns_metrics(self, client):
        """GET / serves metrics."""
        response = client.get("/")
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]

    def test_metrics_path_returns_metrics(self, client):
        """GET /metrics serves metrics (backward compatibility)."""
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]

    def test_root_contains_metric_names(self, client):
        """Response body contains expected metric names."""
        from realize.app_metrics import metrics
        if not metrics.enabled:
            pytest.skip("Metrics not enabled in test environment")

        body = client.get("/").text
        assert "realize_mcp_http_requests_total" in body or "realize_mcp_api_requests_total" in body

    def test_unknown_path_returns_404(self, client):
        """Unknown paths return 404."""
        response = client.get("/unknown")
        assert response.status_code == 404

    def test_post_returns_405(self, client):
        """POST is not allowed on metrics endpoints."""
        response = client.post("/")
        assert response.status_code == 405
