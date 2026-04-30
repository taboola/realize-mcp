"""Account management tool handlers."""
from typing import List
import json
from urllib.parse import quote

import mcp.types as types

from realize.tools.errors import ToolInputError
from realize.tools.utils import format_response, validate_account_id
from realize.client import client



async def search_accounts(query: str, page: int = 1, page_size: int = 10) -> List[types.TextContent]:
    """Search for accounts by numeric ID or text query.

    Returns matching accounts. Each result has an `account_id` field (camelCase string)
    used as input to every other account-scoped tool. Numeric input uses exact ID match;
    text input uses fuzzy name search.
    """
    if not query or not query.strip():
        raise ToolInputError("Query parameter cannot be empty")

    params: dict = {}
    cleaned_query = query.strip()
    if cleaned_query.isdigit():
        params["id"] = cleaned_query
    else:
        params["search_text"] = cleaned_query

    effective_page_size = min(page_size, 10)
    params["page"] = page
    params["page_size"] = effective_page_size

    data = await client.get("/advertisers", params=params)

    if not isinstance(data, dict) or not data.get("results"):
        return [types.TextContent(
            type="text",
            text=f"No accounts found for query: '{query}'\n\nRaw response:\n{json.dumps(data, indent=2, ensure_ascii=False)}",
        )]

    metadata = data.get("metadata", {})
    total = metadata.get("total", len(data["results"]))

    lines = [
        f"Account search results — page {page}, page_size {effective_page_size}, total {total}",
        "",
        "Resolved account_ids (use these in other tools):",
    ]
    for i, result in enumerate(data["results"], 1):
        account_id = result.get("account_id", "<missing>")
        name = result.get("name", "Unknown")
        lines.append(f"  {i}. account_id={account_id!r} ({name})")
    lines.append("")
    lines.append("Full response:")
    lines.append(json.dumps(data, indent=2, ensure_ascii=False))

    return [types.TextContent(type="text", text="\n".join(lines))]


async def get_account(arguments: dict = None) -> List[types.TextContent]:
    """Get one account's full record (read-only).

    Surfaces the validation context an LLM needs before constructing a campaign payload:
    currency, allowGeoTargeting / retargeting / schedule permissions, billing state, account type.
    """
    account_id = arguments.get("account_id") if arguments else None

    is_valid, error_message = validate_account_id(account_id)
    if not is_valid:
        raise ToolInputError(error_message)

    response = await client.get(f"/{quote(account_id, safe='')}")

    return [types.TextContent(
        type="text",
        text=f"Account {account_id} details:\n{format_response(response)}"
    )]
