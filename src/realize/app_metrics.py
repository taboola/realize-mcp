"""Central Prometheus metric definitions for realize-mcp.

All 7 metrics are defined here. The helper methods include a built-in
guard so callers never need to check ``enabled`` themselves.
"""
from __future__ import annotations

import logging
from typing import Optional

from prometheus_client import CollectorRegistry

from .metrics import create_counter, create_histogram

logger = logging.getLogger(__name__)


class AppMetrics:
    """Single source of truth for all Prometheus metrics."""

    def __init__(self, enabled: bool = True, registry: Optional[CollectorRegistry] = None):
        self.enabled = enabled
        if not enabled:
            # All attributes stay None — guard methods become no-ops
            self.http_requests_total = None
            self.http_request_latency_seconds = None
            self.tool_calls_total = None
            self.tool_call_latency_seconds = None
            self.api_requests_total = None
            self.api_request_latency_seconds = None
            self.api_errors_total = None
            return

        # --- HTTP Transport Health ---
        self.http_requests_total = create_counter(
            "realize_mcp_http_requests_total",
            "Total HTTP requests to the MCP server",
            ["method", "endpoint", "http_status", "client_name", "client_version"],
            registry=registry,
        )
        self.http_request_latency_seconds = create_histogram(
            "realize_mcp_http_request_latency_seconds",
            "HTTP request latency in seconds",
            ["endpoint", "client_name", "client_version"],
            registry=registry,
        )

        # --- MCP Tool Execution ---
        self.tool_calls_total = create_counter(
            "realize_mcp_tool_calls_total",
            "Total MCP tool calls",
            ["tool_name", "status", "client_name", "client_version"],
            registry=registry,
        )
        self.tool_call_latency_seconds = create_histogram(
            "realize_mcp_tool_call_latency_seconds",
            "MCP tool call latency in seconds",
            ["tool_name", "client_name", "client_version"],
            registry=registry,
        )

        # --- Upstream Realize API ---
        self.api_requests_total = create_counter(
            "realize_mcp_api_requests_total",
            "Total requests to upstream Realize API",
            ["method", "endpoint_pattern", "http_status"],
            registry=registry,
        )
        self.api_request_latency_seconds = create_histogram(
            "realize_mcp_api_request_latency_seconds",
            "Upstream Realize API request latency in seconds",
            ["method", "endpoint_pattern"],
            registry=registry,
        )
        self.api_errors_total = create_counter(
            "realize_mcp_api_errors_total",
            "Total upstream Realize API errors",
            ["method", "endpoint_pattern", "error_type"],
            registry=registry,
        )

    # ------------------------------------------------------------------
    # Helper methods with built-in guard
    # ------------------------------------------------------------------

    def record_http_request(
        self, method: str, endpoint: str, http_status: int,
        client_name: str, client_version: str, duration: float,
    ) -> None:
        if not self.enabled:
            return
        self.http_requests_total.labels(
            method=method, endpoint=endpoint, http_status=str(http_status),
            client_name=client_name, client_version=client_version,
        ).inc()
        self.http_request_latency_seconds.labels(
            endpoint=endpoint, client_name=client_name, client_version=client_version,
        ).observe(duration)

    def record_tool_call(
        self, tool_name: str, status: str,
        client_name: str, client_version: str, duration: float,
    ) -> None:
        if not self.enabled:
            return
        self.tool_calls_total.labels(
            tool_name=tool_name, status=status,
            client_name=client_name, client_version=client_version,
        ).inc()
        self.tool_call_latency_seconds.labels(
            tool_name=tool_name,
            client_name=client_name, client_version=client_version,
        ).observe(duration)

    def record_api_request(
        self, method: str, endpoint_pattern: str, http_status: int, duration: float,
    ) -> None:
        if not self.enabled:
            return
        self.api_requests_total.labels(
            method=method, endpoint_pattern=endpoint_pattern,
            http_status=str(http_status),
        ).inc()
        self.api_request_latency_seconds.labels(
            method=method, endpoint_pattern=endpoint_pattern,
        ).observe(duration)

    def record_api_error(
        self, method: str, endpoint_pattern: str, error_type: str,
    ) -> None:
        if not self.enabled:
            return
        self.api_errors_total.labels(
            method=method, endpoint_pattern=endpoint_pattern, error_type=error_type,
        ).inc()


def _create_metrics() -> AppMetrics:
    """Factory that reads config at call time (avoids circular imports)."""
    from .config import config
    return AppMetrics(enabled=config.metrics_enabled)


metrics: AppMetrics = _create_metrics()
