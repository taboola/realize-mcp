"""Resource discovery handlers for Realize platform vocabularies.

Four handlers:
- search_geos       — countries / regions / dma / cities / postal_codes (country-scoped)
- search_techno     — operating_system_versions (per family) / browsers
- list_time_zones   — IANA time-zone names for activity_schedule.time_zone
- list_cta_types    — cta.cta_type values for create_native_item / update_native_item

All wrap publisher-console `/api/1.0/resources/...` endpoints. Small fixed enums
(platforms, os_family, connection_type, marketing_objective, bid_strategy,
spending_limit_model) are inlined in the tool descriptions and don't require
discovery calls.
"""
from typing import Any, Callable, Dict, List
from urllib.parse import quote

import mcp.types as types

from realize.client import client
from realize.tools.errors import ToolInputError
from realize.tools.utils import flatten_geo_results, flatten_results, format_discovery_payload


def _global(path: str) -> Callable[[Dict[str, Any]], str]:
    return lambda args: path


def _country_scoped(dimension: str, suffix: str) -> Callable[[Dict[str, Any]], str]:
    def build(args: Dict[str, Any]) -> str:
        country_code = (args or {}).get("country_code")
        if not country_code or not isinstance(country_code, str):
            raise ToolInputError(
                f"country_code is required (ISO-2, e.g. 'US') for dimension={dimension}"
            )
        return f"/resources/countries/{quote(country_code, safe='')}{suffix}"

    return build


def _os_versions(args: Dict[str, Any]) -> str:
    os_family = (args or {}).get("os_family")
    if not os_family or not isinstance(os_family, str):
        raise ToolInputError(
            "os_family is required (e.g. 'iOS', 'Android') for dimension=operating_system_versions"
        )
    return f"/resources/campaigns_properties/operating_systems/{quote(os_family, safe='')}"


_GEO_DISPATCH: Dict[str, Callable[[Dict[str, Any]], str]] = {
    "countries": _global("/resources/countries"),
    "regions": _country_scoped("regions", "/regions"),
    "dma": _country_scoped("dma", "/dma"),
    "cities": _country_scoped("cities", "/cities"),
    "postal_codes": _country_scoped("postal_codes", "/postal"),
}


_TECHNO_DISPATCH: Dict[str, Callable[[Dict[str, Any]], str]] = {
    "operating_system_versions": _os_versions,
    "browsers": _global("/resources/campaigns_properties/browsers"),
}


_TIME_ZONES_ENDPOINT = "/resources/campaigns_properties/activity-scheduler-time-zone"
_CTA_TYPES_ENDPOINT = "/resources/campaigns_properties/items_properties/cta_type"


SUPPORTED_GEO_DIMENSIONS = tuple(_GEO_DISPATCH.keys())
SUPPORTED_TECHNO_DIMENSIONS = tuple(_TECHNO_DISPATCH.keys())


async def _fetch_and_format(label: str, label_value: str, endpoint: str) -> List[types.TextContent]:
    response = await client.get(endpoint)
    values = flatten_results(response)
    return [
        types.TextContent(type="text", text=format_discovery_payload(label, label_value, values))
    ]


async def _fetch_and_format_geo(dimension: str, endpoint: str) -> List[types.TextContent]:
    response = await client.get(endpoint)
    values = flatten_geo_results(response)
    return [
        types.TextContent(type="text", text=format_discovery_payload("dimension", dimension, values))
    ]


async def search_geos(arguments: dict = None) -> List[types.TextContent]:
    """List valid geo codes (countries/regions/dma/cities/postal_codes)."""
    args = arguments or {}
    dimension = args.get("dimension")
    if dimension not in _GEO_DISPATCH:
        raise ToolInputError(
            f"dimension must be one of: {', '.join(SUPPORTED_GEO_DIMENSIONS)}"
        )

    builder = _GEO_DISPATCH[dimension]
    endpoint = builder(args)
    return await _fetch_and_format_geo(dimension, endpoint)


async def search_techno(arguments: dict = None) -> List[types.TextContent]:
    """List valid technology-targeting values (platforms/OS/browsers/connection types)."""
    args = arguments or {}
    dimension = args.get("dimension")
    if dimension not in _TECHNO_DISPATCH:
        raise ToolInputError(
            f"dimension must be one of: {', '.join(SUPPORTED_TECHNO_DIMENSIONS)}"
        )

    builder = _TECHNO_DISPATCH[dimension]
    endpoint = builder(args)
    return await _fetch_and_format("dimension", dimension, endpoint)


async def list_time_zones(arguments: dict = None) -> List[types.TextContent]:
    """List valid IANA time-zone names for activity_schedule.time_zone."""
    return await _fetch_and_format("resource", "time_zones", _TIME_ZONES_ENDPOINT)


async def list_cta_types(arguments: dict = None) -> List[types.TextContent]:
    """List allowed cta.cta_type values for create_native_item / update_native_item.

    The Backstage resource emits {name, value} per entry where `name` is the API
    enum (e.g. "SHOP_NOW") and `value` is the i18n display label ("Shop Now").
    The cta validator does strict `APICtaType.valueOf(...)`, so only enum names
    are accepted on input — emit those.
    """
    response = await client.get(_CTA_TYPES_ENDPOINT)
    results = response.get("results") if isinstance(response, dict) else None
    if isinstance(results, list):
        values = [
            entry["name"] for entry in results
            if isinstance(entry, dict) and "name" in entry
        ]
    else:
        values = flatten_results(response)
    return [
        types.TextContent(type="text", text=format_discovery_payload("resource", "cta_types", values))
    ]
