"""Resource discovery handler for global Realize platform vocabularies.

Wraps the publisher-console `/api/1.0/resources/...` endpoints so MCP clients can
discover valid values to pass to create_campaign and update_campaign_* targeting
tools (countries, regions, OS families, time zones, etc.).
"""
import json
from typing import Any, Callable, Dict, List, Tuple
from urllib.parse import quote

import mcp.types as types

from realize.client import client
from realize.tools.errors import ToolInputError


# Each entry: builder takes (args dict) and returns (relative endpoint path,
# tuple of arg keys it consumed). Builders raise ToolInputError on missing args.
def _global(path: str) -> Tuple[Callable[[Dict[str, Any]], str], Tuple[str, ...]]:
    return (lambda args: path, ())


def _country_scoped(suffix: str) -> Tuple[Callable[[Dict[str, Any]], str], Tuple[str, ...]]:
    def build(args: Dict[str, Any]) -> str:
        country_code = (args or {}).get("country_code")
        if not country_code or not isinstance(country_code, str):
            raise ToolInputError(
                "args.country_code is required (ISO-2, e.g. 'US') for this resource"
            )
        return f"/resources/countries/{quote(country_code, safe='')}{suffix}"

    return (build, ("country_code",))


def _os_versions(args: Dict[str, Any]) -> str:
    os_family = (args or {}).get("os_family")
    if not os_family or not isinstance(os_family, str):
        raise ToolInputError(
            "args.os_family is required (e.g. 'iOS', 'Android') for resource=operating_system_versions"
        )
    return f"/resources/campaigns_properties/operating_systems/{quote(os_family, safe='')}"


_RESOURCE_DISPATCH: Dict[str, Tuple[Callable[[Dict[str, Any]], str], Tuple[str, ...]]] = {
    "countries": _global("/resources/countries"),
    "regions": _country_scoped("/regions"),
    "dma": _country_scoped("/dma"),
    "cities": _country_scoped("/cities"),
    "postal_codes": _country_scoped("/postal"),
    "platforms": _global("/resources/platforms"),
    "operating_systems": _global("/resources/campaigns_properties/operating_systems"),
    "operating_system_versions": (_os_versions, ("os_family",)),
    "browsers": _global("/resources/campaigns_properties/browsers"),
    "connection_types": _global("/resources/campaigns_properties/connection_types"),
    "marketing_objectives": _global("/resources/campaigns_properties/marketing_objective"),
    "bid_strategies": _global("/resources/campaigns_properties/bid_strategy"),
    "spending_limit_models": _global("/resources/campaigns_properties/spending_limit_model"),
    "time_zones": _global("/resources/campaigns_properties/activity-scheduler-time-zone"),
}

SUPPORTED_RESOURCES = tuple(_RESOURCE_DISPATCH.keys())


def _flatten_results(payload: Any) -> List[Any]:
    """Unwrap APIResults<APIResource<T>> -> flat list of values."""
    if not isinstance(payload, dict):
        return payload  # passthrough; caller will JSON-serialize
    results = payload.get("results")
    if not isinstance(results, list):
        return payload
    flattened: List[Any] = []
    for entry in results:
        if isinstance(entry, dict) and "value" in entry and len(entry) <= 3:
            # Typical APIResource<String>: {value, name?, type?}
            flattened.append(entry["value"])
        else:
            flattened.append(entry)
    return flattened


async def list_realize_resource(arguments: dict = None) -> List[types.TextContent]:
    """List valid values for a global Realize platform vocabulary."""
    args = arguments or {}
    resource = args.get("resource")
    if resource not in _RESOURCE_DISPATCH:
        raise ToolInputError(
            f"resource must be one of: {', '.join(SUPPORTED_RESOURCES)}"
        )

    builder, _consumed_keys = _RESOURCE_DISPATCH[resource]
    endpoint = builder(args.get("args") or {})

    response = await client.get(endpoint)
    values = _flatten_results(response)

    return [
        types.TextContent(
            type="text",
            text=json.dumps({"resource": resource, "values": values}, ensure_ascii=False, indent=2),
        )
    ]
