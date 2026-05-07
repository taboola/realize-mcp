"""Utility functions for tools."""
import json
import csv
import io
from typing import Dict, Any, Tuple, List


def flatten_results(payload: Any) -> List[Any]:
    """Unwrap APIResults<APIResource<T>> -> flat list of values.

    Used by resource discovery tools to project the standard Backstage
    pagination wrapper (`{"results": [{"value": …}, …]}`) into a flat list.
    Non-dict payloads and dicts without a `results` list pass through.
    """
    if not isinstance(payload, dict):
        return payload
    results = payload.get("results")
    if not isinstance(results, list):
        return payload
    flattened: List[Any] = []
    for entry in results:
        if isinstance(entry, dict) and "value" in entry:
            flattened.append(entry["value"])
        else:
            flattened.append(entry)
    return flattened


def flatten_geo_results(payload: Any) -> List[Any]:
    """Project APIResource<String> entries into [{code, name}] pairs.

    Backstage's geo dictionary endpoints emit each entry as
    `{"name": "<code>", "value": "<display name>"}` (e.g. `{"name": "CA",
    "value": "California"}`). The targeting wire fields (country_targeting,
    region_targeting, etc.) accept the *code* — `name` here. To make that
    contract obvious to LLM callers, we emit `{code, name}` objects so the
    code is unambiguous and the human-readable label is still visible.

    Entries that don't match the {name, value} shape pass through unchanged.
    """
    if not isinstance(payload, dict):
        return payload
    results = payload.get("results")
    if not isinstance(results, list):
        return payload
    flattened: List[Any] = []
    for entry in results:
        if isinstance(entry, dict) and "name" in entry and "value" in entry:
            flattened.append({"code": entry["name"], "name": entry["value"]})
        else:
            flattened.append(entry)
    return flattened


def format_discovery_payload(label: str, label_value: str, values: Any) -> str:
    """Render a discovery-tool response as `{<label>: <label_value>, "values": [...]}` JSON.

    Shared by resources.py and discovery_handlers.py so all `search_*` / `list_*` tools
    return the same shape. Pass `label=None` for tools without a context label
    (network-scoped discovery), which emits `{"values": [...]}` only.
    """
    body: Dict[str, Any] = {}
    if label is not None:
        body[label] = label_value
    body["values"] = values
    return json.dumps(body, ensure_ascii=False, indent=2)


def format_response_as_csv(data: Dict[str, Any], max_records_display: int = 1000) -> str:
    """
    Format API response data as CSV with summary header for maximum compactness.
    
    Args:
        data: Raw API response data
        max_records_display: Maximum number of records to include in CSV
        
    Returns:
        Formatted string with summary header and CSV data
    """
    if not isinstance(data, dict):
        return json.dumps(data, indent=2, ensure_ascii=False)
    
    # Extract common response structure
    results = data.get("results", [])
    metadata = data.get("metadata", {})
    
    if not results:
        return "📊 **SUMMARY:** No records found"
    
    # Build compact summary header
    summary_parts = []
    summary_parts.append(f"📊 Records: {len(results)}")
    
    if metadata:
        if "total" in metadata:
            summary_parts.append(f"Total: {metadata['total']}")
        if "page" in metadata:
            summary_parts.append(f"Page: {metadata['page']}")
        if "page_size" in metadata:
            summary_parts.append(f"Size: {metadata['page_size']}")
    
    # Add pagination indicator if more data available
    if metadata.get("total", len(results)) > len(results):
        summary_parts.append("⚠️ More data available - use pagination")
    
    summary_header = " | ".join(summary_parts)
    
    # Generate CSV data
    if not results:
        return f"{summary_header}\n\nNo data records found."
    
    # Limit records to prevent oversized responses
    records_to_process = results[:max_records_display]
    if len(results) > max_records_display:
        summary_header += f" | Showing first {max_records_display} of {len(results)} records"
    
    # Get all unique keys from all records to ensure complete headers
    all_keys = set()
    for record in records_to_process:
        if isinstance(record, dict):
            all_keys.update(record.keys())
    
    if not all_keys:
        return f"{summary_header}\n\nNo valid data structure found."
    
    # Sort keys for consistent column order
    headers = sorted(list(all_keys))
    
    # Generate CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write headers
    writer.writerow(headers)
    
    # Write data rows
    for record in records_to_process:
        if isinstance(record, dict):
            row = []
            for header in headers:
                value = record.get(header, "")
                # Handle nested objects/arrays by converting to string
                if isinstance(value, (dict, list)):
                    value = json.dumps(value, separators=(',', ':'))
                row.append(value)
            writer.writerow(row)
    
    csv_content = output.getvalue()
    output.close()
    
    return f"{summary_header}\n\n{csv_content.strip()}"


def format_large_response_with_csv_truncation(data: Dict[str, Any], max_size_chars: int = 25000) -> str:
    """
    Format response as CSV with size-based truncation to prevent MCP message size issues.
    CSV format is more compact, so we can allow larger sizes.
    Truncates at row boundaries to maintain valid CSV structure.
    
    Args:
        data: Raw API response data
        max_size_chars: Maximum characters in response (default: 25KB for better data capacity)
        
    Returns:
        Formatted CSV response, potentially truncated at row boundaries
    """
    formatted = format_response_as_csv(data)
    
    if len(formatted) <= max_size_chars:
        return formatted
    
    # Split into header and data sections
    lines = formatted.split('\n')
    if len(lines) < 3:  # Summary + empty line + at least header
        return formatted  # Too small to truncate meaningfully
    
    # Find where CSV data starts (after summary header and empty line)
    summary_header = lines[0]
    csv_start_idx = 1
    while csv_start_idx < len(lines) and not lines[csv_start_idx].strip():
        csv_start_idx += 1
    
    if csv_start_idx >= len(lines):
        return formatted  # No CSV data found
    
    # Reserve space for truncation message
    truncation_msg = (
        "\n\n⚠️ **RESPONSE TRUNCATED AT ROW BOUNDARY**\n"
        f"• Response too large, showing partial data\n"
        "• Use smaller page_size or date ranges for complete results\n"
        "• Consider pagination parameters for better data management"
    )
    available_space = max_size_chars - len(truncation_msg) - 50  # Extra buffer
    
    # Calculate cumulative length and find last complete row that fits
    current_length = len(summary_header) + 2  # +2 for newlines
    csv_header = lines[csv_start_idx]
    current_length += len(csv_header) + 1  # +1 for newline
    
    if current_length >= available_space:
        # Even header doesn't fit, fall back to hard truncation
        truncated = formatted[:max_size_chars-300]
        return truncated + "\n\n⚠️ **RESPONSE TRUNCATED** - Data too large for display"
    
    # Find how many data rows we can include
    included_lines = [summary_header, "", csv_header]  # Start with summary and header
    
    for i in range(csv_start_idx + 1, len(lines)):
        line = lines[i].strip()
        if not line:  # Skip empty lines
            continue
            
        line_length = len(line) + 1  # +1 for newline
        if current_length + line_length > available_space:
            break
            
        included_lines.append(line)
        current_length += line_length
    
    # Build the truncated response
    result = '\n'.join(included_lines)
    
    # Add truncation info
    results = data.get("results", [])
    original_row_count = len(results)
    included_row_count = len(included_lines) - 3  # Subtract summary, empty line, and header
    
    result += f"\n\n⚠️ **TRUNCATED**: Showing {included_row_count} of {original_row_count} rows"
    result += f"\n• Use smaller page_size or date ranges to get complete data"
    result += f"\n• Consider pagination parameters for better results"
    
    return result


# Important fields that should always be displayed regardless of length
FORCE_DISPLAY_FIELDS = {
    'url', 'thumbnail_url', 'video_url', 'tracking_code',
    'description', 'title', 'name', 'branding_text'
}


def format_response(data: Dict[str, Any], max_records_display: int = 10) -> str:
    """Render API response as raw JSON.

    Both single-item and collection responses pass through unchanged so the LLM
    sees full state including nested targeting blocks. Earlier heuristic display
    truncated nested fields and hid load-bearing data.
    """
    return json.dumps(data, indent=2, ensure_ascii=False)


def safe_get(data: Dict[str, Any], key: str, default: Any = "N/A") -> Any:
    """Safely get value from dictionary with default."""
    return data.get(key, default)


def validate_account_id(account_id: str) -> Tuple[bool, str]:
    """
    Validate account_id format and provide helpful errors.
    
    Args:
        account_id: The account ID string to validate
        
    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if account_id is valid, False otherwise
        - error_message: Empty string if valid, helpful error message if invalid
    """
    if not account_id:
        return False, "account_id is required"
    
    if account_id.isdigit():
        return False, (
            f"This appears to be a numeric account ID ({account_id}). Please use the search_accounts tool first "
            "to get the proper account_id field value. REQUIRED WORKFLOW: "
            f"1) search_accounts('{account_id}') 2) Extract 'account_id' field from response 3) Use that account_id value instead"
        )
    
    return True, "" 