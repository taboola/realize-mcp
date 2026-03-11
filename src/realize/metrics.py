"""Prometheus metric type factory.

Thin wrappers around prometheus_client constructors,
accepting an optional registry for test isolation.
"""
from prometheus_client import Counter, Histogram, CollectorRegistry, REGISTRY

DEFAULT_BUCKETS = (
    0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0,
)


def create_counter(name: str, description: str, labelnames: list[str],
                   registry: CollectorRegistry | None = None) -> Counter:
    return Counter(name, description, labelnames, registry=registry or REGISTRY)


def create_histogram(name: str, description: str, labelnames: list[str],
                     buckets: tuple | None = None,
                     registry: CollectorRegistry | None = None) -> Histogram:
    return Histogram(
        name, description, labelnames,
        buckets=buckets or DEFAULT_BUCKETS,
        registry=registry or REGISTRY,
    )
