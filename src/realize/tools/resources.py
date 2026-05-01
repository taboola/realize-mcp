"""Resource discovery handlers for Realize platform vocabularies.

Three handlers split by argument-shape boundary:
- search_geos      — countries / regions / dma / cities / postal_codes (country-scoped)
- search_techno    — platforms / OS / OS versions / browsers / connection types (os-scoped for versions)
- list_realize_resource — bounded campaign-config enums (no args)

All wrap publisher-console `/api/1.0/resources/...` endpoints.
"""
from typing import Any, Callable, Dict, List
from urllib.parse import quote

import mcp.types as types

from realize.client import client
from realize.tools.errors import ToolInputError
from realize.tools.utils import flatten_results, format_discovery_payload


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
    "platforms": _global("/resources/platforms"),
    "operating_systems": _global("/resources/campaigns_properties/operating_systems"),
    "operating_system_versions": _os_versions,
    "browsers": _global("/resources/campaigns_properties/browsers"),
    "connection_types": _global("/resources/campaigns_properties/connection_types"),
}


_ENUM_DISPATCH: Dict[str, Callable[[Dict[str, Any]], str]] = {
    "marketing_objectives": _global("/resources/campaigns_properties/marketing-objective"),
    "bid_strategies": _global("/resources/campaigns_properties/bid-strategy"),
    "spending_limit_models": _global("/resources/campaigns_properties/spending-limit-model"),
    "time_zones": _global("/resources/campaigns_properties/activity-scheduler-time-zone"),
}


SUPPORTED_GEO_DIMENSIONS = tuple(_GEO_DISPATCH.keys())
SUPPORTED_TECHNO_DIMENSIONS = tuple(_TECHNO_DISPATCH.keys())
SUPPORTED_ENUM_RESOURCES = tuple(_ENUM_DISPATCH.keys())


async def _fetch_and_format(label: str, label_value: str, endpoint: str) -> List[types.TextContent]:
    response = await client.get(endpoint)
    values = flatten_results(response)
    return [
        types.TextContent(type="text", text=format_discovery_payload(label, label_value, values))
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
    return await _fetch_and_format("dimension", dimension, endpoint)


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


async def list_realize_resource(arguments: dict = None) -> List[types.TextContent]:
    """List values for a bounded campaign-config enum (marketing objectives etc.)."""
    args = arguments or {}
    resource = args.get("resource")
    if resource not in _ENUM_DISPATCH:
        raise ToolInputError(
            f"resource must be one of: {', '.join(SUPPORTED_ENUM_RESOURCES)}"
        )

    builder = _ENUM_DISPATCH[resource]
    endpoint = builder(args)
    return await _fetch_and_format("resource", resource, endpoint)
