"""Utility functions for tools."""
import json
import csv
import io
from typing import Dict, Any, Tuple, List


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


def format_response(data: Dict[str, Any], max_records_display: int = 10) -> str:
    """
    Format API response data for display with intelligent truncation and summary.
    Handles both collection responses (with results array) and single item responses.
    
    Args:
        data: Raw API response data
        max_records_display: Maximum number of detailed records to show
        
    Returns:
        Formatted string with summary, sample data, and pagination info
    """
    if not isinstance(data, dict):
        return json.dumps(data, indent=2, ensure_ascii=False)
    
    # Check if this is a collection response (has results array)
    results = data.get("results", [])
    metadata = data.get("metadata", {})
    
    # If no results array, treat this as a single item response
    if "results" not in data:
        formatted_parts = []
        formatted_parts.append(f"📋 **ITEM DETAILS:**")
        
        # Display key-value pairs for single item
        for key, value in data.items():
            if isinstance(value, (int, float, str, bool)) and len(str(value)) < 100:
                formatted_parts.append(f"   • {key}: {value}")
            elif isinstance(value, (dict, list)):
                # For complex nested data, show first few items or summarize
                if isinstance(value, list) and len(value) <= 3:
                    formatted_parts.append(f"   • {key}: {value}")
                elif isinstance(value, dict) and len(value) <= 5:
                    formatted_parts.append(f"   • {key}: {value}")
                else:
                    formatted_parts.append(f"   • {key}: [Complex data - {type(value).__name__}]")
        
        return "\n".join(formatted_parts)
    
    # Handle collection responses (with results array)
    formatted_parts = []
    
    # Summary section
    if results:
        formatted_parts.append(f"📊 **SUMMARY:**")
        formatted_parts.append(f"   • Total records in response: {len(results)}")
        
        if metadata:
            if "total" in metadata:
                formatted_parts.append(f"   • Total available: {metadata['total']}")
            if "page" in metadata:
                formatted_parts.append(f"   • Current page: {metadata['page']}")
            if "page_size" in metadata:
                formatted_parts.append(f"   • Page size: {metadata['page_size']}")
        
        # Data preview section
        formatted_parts.append(f"\n📈 **DATA PREVIEW ({min(len(results), max_records_display)} of {len(results)} records):**")
        
        for i, record in enumerate(results[:max_records_display]):
            formatted_parts.append(f"\n   Record {i+1}:")
            # Show key metrics for report data
            for key, value in record.items():
                if isinstance(value, (int, float, str)) and len(str(value)) < 100:
                    formatted_parts.append(f"     • {key}: {value}")
        
        if len(results) > max_records_display:
            formatted_parts.append(f"\n   ... and {len(results) - max_records_display} more records")
        
        # Pagination guidance
        if metadata.get("total", len(results)) > len(results):
            formatted_parts.append(f"\n🔄 **PAGINATION INFO:**")
            formatted_parts.append(f"   • More data available - use 'page' parameter to get additional records")
            formatted_parts.append(f"   • Increase 'page_size' (max: 1000) to get more records per request")
    else:
        formatted_parts.append("📊 **SUMMARY:** No records found")
    
    # Metadata section (if any additional info)
    if metadata and any(k not in ["total", "page", "page_size"] for k in metadata.keys()):
        formatted_parts.append(f"\n📋 **METADATA:**")
        for key, value in metadata.items():
            if key not in ["total", "page", "page_size"]:
                formatted_parts.append(f"   • {key}: {value}")
    
    return "\n".join(formatted_parts)


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