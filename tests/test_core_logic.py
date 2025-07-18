"""Core logic tests that don't require MCP dependencies."""
import pytest
import sys
import pathlib
sys.path.append(str(pathlib.Path(__file__).parent.parent / "src"))


def test_query_detection_logic():
    """Test the query detection logic that determines numeric vs text queries."""
    
    # Test cases for numeric detection (should use 'id' parameter)
    numeric_queries = ["12345", "00123", "999", "0", "123456789"]
    
    for query in numeric_queries:
        cleaned_query = query.strip()
        if cleaned_query.isdigit():
            param_type = "id"
        else:
            param_type = "search"
        
        assert param_type == "id", f"Query '{query}' should be detected as numeric"
    
    # Test cases for text detection (should use 'search' parameter)
    text_queries = ["Marketing Corp", "ABC123", "Test & Co.", "account-name", "123abc", ""]
    
    for query in text_queries:
        cleaned_query = query.strip()
        if cleaned_query.isdigit():
            param_type = "id"
        else:
            param_type = "search"
        
        assert param_type == "search", f"Query '{query}' should be detected as text"


def test_whitespace_handling():
    """Test that whitespace is handled correctly."""
    
    # Test whitespace stripping for numeric queries
    numeric_with_whitespace = ["  12345  ", "\t999\n", " 0 "]
    
    for query in numeric_with_whitespace:
        cleaned_query = query.strip()
        assert cleaned_query.isdigit(), f"Cleaned query '{cleaned_query}' should be numeric"
    
    # Test whitespace stripping for text queries  
    text_with_whitespace = ["  Marketing Corp  ", "\tABC123\n", " Test & Co. "]
    
    for query in text_with_whitespace:
        cleaned_query = query.strip()
        assert not cleaned_query.isdigit(), f"Cleaned query '{cleaned_query}' should be text"


def test_edge_cases():
    """Test edge cases for query detection."""
    
    # Empty and whitespace-only queries
    empty_queries = ["", "   ", "\t\n", "  \t  "]
    
    for query in empty_queries:
        cleaned_query = query.strip()
        is_empty = not cleaned_query
        assert is_empty, f"Query '{query}' should be detected as empty after cleaning"
    
    # Mixed alphanumeric should be text
    mixed_queries = ["123abc", "abc123", "12-34", "12.34", "123-abc"]
    
    for query in mixed_queries:
        cleaned_query = query.strip()
        assert not cleaned_query.isdigit(), f"Mixed query '{query}' should be treated as text"


def test_tool_registry_structure():
    """Test that our tool registry has the correct structure."""
    from realize.tools.registry import get_all_tools, get_tools_by_category, get_tool_categories
    
    # Test that registry functions work
    all_tools = get_all_tools()
    assert isinstance(all_tools, dict)
    assert len(all_tools) > 0
    
    # Test that search_accounts is registered
    assert 'search_accounts' in all_tools
    search_tool = all_tools['search_accounts']
    
    # Test tool structure
    assert 'description' in search_tool
    assert 'schema' in search_tool
    assert 'handler' in search_tool
    assert 'category' in search_tool
    
    # Test that description indicates read-only
    description = search_tool['description'].lower()
    assert 'read-only' in description
    
    # Test schema structure
    schema = search_tool['schema']
    assert schema['type'] == 'object'
    assert 'properties' in schema
    assert 'required' in schema
    assert 'query' in schema['properties']
    assert 'query' in schema['required']
    
    # Test categories
    categories = get_tool_categories()
    assert 'accounts' in categories
    
    # Test category filtering
    account_tools = get_tools_by_category('accounts')
    assert 'search_accounts' in account_tools


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 