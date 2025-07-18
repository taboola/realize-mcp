"""Tool registration and discovery edge case tests."""
import pytest
import sys
import pathlib
sys.path.append(str(pathlib.Path(__file__).parent.parent / "src"))
from unittest.mock import patch, Mock
from realize.tools.registry import get_all_tools, get_tools_by_category, get_tool_categories


class TestToolRegistryEdgeCases:
    """Test edge cases in tool registration and discovery."""
    
    def test_registry_returns_immutable_data(self):
        """Test that registry returns data that doesn't affect internal state."""
        # Get tools twice
        tools1 = get_all_tools()
        tools2 = get_all_tools()
        
        # Should be equal but potentially different objects
        assert tools1.keys() == tools2.keys()
        
        # Modifying returned dict shouldn't affect internal state
        original_count = len(tools1)
        tools1['fake_tool'] = {'description': 'fake'}
        
        tools3 = get_all_tools()
        assert len(tools3) == original_count
        assert 'fake_tool' not in tools3
    
    def test_all_tools_have_required_fields(self):
        """Test that all registered tools have required fields."""
        tools = get_all_tools()
        
        required_fields = ['description', 'schema', 'handler', 'category']
        
        for tool_name, tool_config in tools.items():
            for field in required_fields:
                assert field in tool_config, f"Tool {tool_name} missing required field: {field}"
            
            # Test specific field types
            assert isinstance(tool_config['description'], str)
            assert len(tool_config['description']) > 0
            assert isinstance(tool_config['schema'], dict)
            assert isinstance(tool_config['handler'], str)
            assert isinstance(tool_config['category'], str)
    
    def test_tool_schemas_valid_structure(self):
        """Test that all tool schemas have valid structure."""
        tools = get_all_tools()
        
        for tool_name, tool_config in tools.items():
            schema = tool_config['schema']
            
            # Must be object type
            assert schema.get('type') == 'object', f"Tool {tool_name} schema must be object type"
            
            # Should have properties
            assert 'properties' in schema, f"Tool {tool_name} schema missing properties"
            assert isinstance(schema['properties'], dict)
            
            # Should have required array
            assert 'required' in schema, f"Tool {tool_name} schema missing required array"
            assert isinstance(schema['required'], list)
            
            # All required fields must be in properties
            for req_field in schema['required']:
                assert req_field in schema['properties'], \
                    f"Tool {tool_name} required field {req_field} not in properties"
    
    def test_tool_handlers_format_consistent(self):
        """Test that tool handler paths follow consistent format."""
        tools = get_all_tools()
        
        expected_patterns = [
            'auth_handlers.',
            'account_handlers.',
            'campaign_handlers.',
            'report_handlers.'
        ]
        
        for tool_name, tool_config in tools.items():
            handler = tool_config['handler']
            
            # Should match one of the expected patterns
            matches_pattern = any(handler.startswith(pattern) for pattern in expected_patterns)
            assert matches_pattern, f"Tool {tool_name} handler {handler} doesn't match expected patterns"
            
            # Should have function name after module
            assert '.' in handler, f"Tool {tool_name} handler {handler} should include function name"
            parts = handler.split('.')
            assert len(parts) >= 2, f"Tool {tool_name} handler {handler} should have module.function format"
    
    def test_categories_comprehensive(self):
        """Test that all categories are properly defined."""
        categories = get_tool_categories()
        
        # Should have all expected categories
        expected_categories = ['authentication', 'accounts', 'campaigns', 'campaign_items', 'reports']
        
        for expected in expected_categories:
            assert expected in categories, f"Expected category {expected} not found"
        
        # Each category should have tools
        for category in categories:
            tools = get_tools_by_category(category)
            assert len(tools) > 0, f"Category {category} has no tools"
    
    def test_category_filtering_works(self):
        """Test that category filtering returns correct tools."""
        all_tools = get_all_tools()
        categories = get_tool_categories()
        
        for category in categories:
            category_tools = get_tools_by_category(category)
            
            # All returned tools should belong to this category
            for tool_name in category_tools:
                assert tool_name in all_tools, f"Tool {tool_name} in category {category} not in all_tools"
                assert all_tools[tool_name]['category'] == category, \
                    f"Tool {tool_name} has wrong category"
        
        # Sum of category tools should equal total tools
        total_from_categories = sum(len(get_tools_by_category(cat)) for cat in categories)
        assert total_from_categories == len(all_tools), "Category totals don't match all tools"
    
    def test_no_tool_name_conflicts(self):
        """Test that there are no tool name conflicts across categories."""
        all_tools = get_all_tools()
        categories = get_tool_categories()
        
        seen_tools = set()
        
        for category in categories:
            category_tools = get_tools_by_category(category)
            
            for tool_name in category_tools:
                assert tool_name not in seen_tools, f"Tool {tool_name} appears in multiple categories"
                seen_tools.add(tool_name)
        
        # Should have seen all tools
        assert len(seen_tools) == len(all_tools)


class TestToolHandlerImports:
    """Test that all tool handlers can be imported successfully."""
    
    def test_all_handlers_importable(self):
        """Test that all registered handlers can be imported."""
        tools = get_all_tools()
        
        for tool_name, tool_config in tools.items():
            handler_path = tool_config['handler']
            
            try:
                # Parse handler path
                if handler_path.startswith('auth_handlers.'):
                    module_name = 'realize.tools.auth_handlers'
                    function_name = handler_path.split('.', 1)[1]
                elif handler_path.startswith('account_handlers.'):
                    module_name = 'realize.tools.account_handlers'
                    function_name = handler_path.split('.', 1)[1]
                elif handler_path.startswith('campaign_handlers.'):
                    module_name = 'realize.tools.campaign_handlers'
                    function_name = handler_path.split('.', 1)[1]
                elif handler_path.startswith('report_handlers.'):
                    module_name = 'realize.tools.report_handlers'
                    function_name = handler_path.split('.', 1)[1]
                else:
                    pytest.fail(f"Unknown handler pattern for tool {tool_name}: {handler_path}")
                
                # Try to import the module and function
                import importlib
                module = importlib.import_module(module_name)
                
                assert hasattr(module, function_name), \
                    f"Function {function_name} not found in module {module_name} for tool {tool_name}"
                
                handler_func = getattr(module, function_name)
                assert callable(handler_func), \
                    f"Handler {function_name} in {module_name} is not callable for tool {tool_name}"
                
            except ImportError as e:
                pytest.fail(f"Failed to import handler for tool {tool_name}: {e}")
    
    def test_handler_modules_exist(self):
        """Test that all handler modules exist and can be imported."""
        expected_modules = [
            'realize.tools.auth_handlers',
            'realize.tools.account_handlers', 
            'realize.tools.campaign_handlers',
            'realize.tools.report_handlers'
        ]
        
        for module_name in expected_modules:
            try:
                import importlib
                module = importlib.import_module(module_name)
                assert module is not None
            except ImportError as e:
                pytest.fail(f"Failed to import required module {module_name}: {e}")


class TestToolDescriptions:
    """Test tool descriptions for quality and consistency."""
    
    def test_all_descriptions_indicate_read_only(self):
        """Test that all tool descriptions clearly indicate read-only nature."""
        tools = get_all_tools()
        
        read_only_indicators = ['read-only', 'get', 'retrieve', 'fetch', 'search', 'view', 'list']
        
        for tool_name, tool_config in tools.items():
            description = tool_config['description'].lower()
            
            # Should contain at least one read-only indicator
            has_indicator = any(indicator in description for indicator in read_only_indicators)
            assert has_indicator, \
                f"Tool {tool_name} description doesn't clearly indicate read-only: {description}"
            
            # Should not contain write indicators
            write_indicators = ['create', 'update', 'delete', 'modify', 'edit', 'write', 'post', 'put']
            has_write = any(indicator in description for indicator in write_indicators)
            assert not has_write, \
                f"Tool {tool_name} description contains write indicators: {description}"
    
    def test_descriptions_are_informative(self):
        """Test that descriptions are informative and helpful."""
        tools = get_all_tools()
        
        for tool_name, tool_config in tools.items():
            description = tool_config['description']
            
            # Should be reasonably long
            assert len(description) >= 20, \
                f"Tool {tool_name} description too short: {description}"
            
            # Should contain the tool purpose
            assert tool_name.replace('_', ' ').lower() in description.lower() or \
                   any(word in description.lower() for word in tool_name.split('_')), \
                f"Tool {tool_name} description doesn't relate to tool name: {description}"
    
    def test_schema_descriptions_exist(self):
        """Test that schema properties have descriptions."""
        tools = get_all_tools()
        
        for tool_name, tool_config in tools.items():
            schema = tool_config['schema']
            
            if 'properties' in schema:
                for prop_name, prop_config in schema['properties'].items():
                    # Each property should have a description
                    assert 'description' in prop_config, \
                        f"Tool {tool_name} property {prop_name} missing description"
                    assert isinstance(prop_config['description'], str), \
                        f"Tool {tool_name} property {prop_name} description should be string"
                    assert len(prop_config['description']) > 0, \
                        f"Tool {tool_name} property {prop_name} description is empty"


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 