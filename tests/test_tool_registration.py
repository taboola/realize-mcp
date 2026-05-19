"""Tool registration and discovery edge case tests."""
import pytest
import sys
import pathlib
sys.path.append(str(pathlib.Path(__file__).parent.parent / "src"))
from unittest.mock import patch, Mock
from realize.tools.registry import get_all_tools, get_tools_by_category, get_tool_categories, TOOL_REGISTRY


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
    
    @patch("realize.config.config")
    def test_tool_handlers_format_consistent(self, mock_config):
        """Test that tool handler paths follow consistent format."""
        mock_config.mcp_transport = "stdio"
        tools = get_all_tools()

        expected_patterns = [
            'auth_handlers.',
            'account_handlers.',
            'campaign_handlers.',
            'item_read_handlers.',
            'item_native_handlers.',
            'item_display_handlers.',
            'report_handlers.',
            'resources.',
            'discovery_handlers.',
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
    
    @patch("realize.config.config")
    def test_categories_comprehensive(self, mock_config):
        """Test that all categories are properly defined."""
        mock_config.mcp_transport = "stdio"
        categories = get_tool_categories()
        
        # Should have all expected categories
        expected_categories = ['authentication', 'accounts', 'campaigns', 'items', 'reports']
        
        for expected in expected_categories:
            assert expected in categories, f"Expected category {expected} not found"
        
        # Each category should have tools
        for category in categories:
            tools = get_tools_by_category(category)
            assert len(tools) > 0, f"Category {category} has no tools"
    
    @patch("realize.config.config")
    def test_category_filtering_works(self, mock_config):
        """Test that category filtering returns correct tools."""
        mock_config.mcp_transport = "stdio"
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
        categories = get_tool_categories()

        seen_tools = set()

        for category in categories:
            category_tools = get_tools_by_category(category)

            for tool_name in category_tools:
                assert tool_name not in seen_tools, f"Tool {tool_name} appears in multiple categories"
                seen_tools.add(tool_name)

        # Every registry entry should have been visited exactly once
        assert seen_tools == set(TOOL_REGISTRY.keys())


class TestToolHandlerImports:
    """Test that all tool handlers can be imported successfully."""
    
    def test_all_handlers_importable(self):
        """Test that all registered handlers can be imported."""
        tools = get_all_tools()
        
        for tool_name, tool_config in tools.items():
            handler_path = tool_config['handler']
            
            try:
                # Parse handler path: <module>.<function> under realize.tools.
                module_prefix, _, function_name = handler_path.partition('.')
                if not module_prefix or not function_name:
                    pytest.fail(f"Malformed handler path for tool {tool_name}: {handler_path}")
                module_name = f"realize.tools.{module_prefix}"
                
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
            'realize.tools.item_read_handlers',
            'realize.tools.item_native_handlers',
            'realize.tools.item_display_handlers',
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
        """Read-only tool descriptions must contain at least one read verb.

        The earlier check forbidding 'create'/'update' substrings was removed:
        read tools now intentionally cross-reference write tools by name (e.g.
        create_campaign, update_campaign_*) to point callers at the next step.
        Write semantics are tracked authoritatively via the readOnlyHint
        annotation, not via substring sniffing.
        """
        tools = get_all_tools()

        read_only_indicators = ['read-only', 'get', 'retrieve', 'fetch', 'search', 'view', 'list', 'authenticate', 'discover']

        for tool_name, tool_config in tools.items():
            # Skip write tools (readOnlyHint absent or false → mutates state).
            annotations = tool_config.get("annotations") or {}
            if annotations.get("readOnlyHint") is not True:
                continue

            description = tool_config['description'].lower()

            has_indicator = any(indicator in description for indicator in read_only_indicators)
            assert has_indicator, \
                f"Tool {tool_name} description doesn't clearly indicate read-only: {description}"
    
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


class TestToolTransportFiltering:
    """Test that auth tools are filtered based on transport mode."""

    @patch("realize.config.config")
    def test_stdio_includes_auth_tools(self, mock_config):
        """Auth tools should be present in stdio mode."""
        mock_config.mcp_transport = "stdio"
        tools = get_all_tools()

        auth_tools = {n for n, t in tools.items() if t["category"] == "authentication"}
        assert "get_auth_token" in auth_tools
        assert "get_token_details" in auth_tools

    @patch("realize.config.config")
    def test_streamable_http_excludes_auth_tools(self, mock_config):
        """Auth tools should be absent in streamable-http mode."""
        mock_config.mcp_transport = "streamable-http"
        tools = get_all_tools()

        auth_tools = {n for n, t in tools.items() if t["category"] == "authentication"}
        assert len(auth_tools) == 0
        assert "get_auth_token" not in tools
        assert "get_token_details" not in tools

    @patch("realize.config.config")
    def test_streamable_http_preserves_non_auth_tools(self, mock_config):
        """Non-auth tools should still be present in streamable-http mode."""
        mock_config.mcp_transport = "streamable-http"
        tools = get_all_tools()

        non_auth_count = sum(
            1 for t in TOOL_REGISTRY.values() if t["category"] != "authentication"
        )
        assert len(tools) == non_auth_count
        assert "search_accounts" in tools
        assert "list_campaigns" in tools


class TestItemAndDiscoveryAdditions:
    """Smoke checks for the item write + discovery tools."""

    def test_create_native_item_registered(self):
        assert "create_native_item" in TOOL_REGISTRY
        entry = TOOL_REGISTRY["create_native_item"]
        assert entry["category"] == "items"
        assert entry["handler"] == "item_native_handlers.create_native_item"
        assert entry["annotations"]["destructiveHint"] is False
        assert entry["annotations"]["idempotentHint"] is False

    def test_update_native_item_registered(self):
        assert "update_native_item" in TOOL_REGISTRY
        entry = TOOL_REGISTRY["update_native_item"]
        assert entry["category"] == "items"
        assert entry["handler"] == "item_native_handlers.update_native_item"
        assert entry["annotations"]["destructiveHint"] is True
        assert entry["annotations"]["idempotentHint"] is True

    def test_create_display_item_registered(self):
        assert "create_display_item" in TOOL_REGISTRY
        entry = TOOL_REGISTRY["create_display_item"]
        assert entry["category"] == "items"
        assert entry["handler"] == "item_display_handlers.create_display_item"
        assert entry["annotations"]["destructiveHint"] is False
        assert entry["annotations"]["idempotentHint"] is False
        # ad_tag and asset_url are mutually-exclusive discriminators enforced
        # by the handler, not the JSON Schema. dimensions is required only
        # when ad_tag is sent.
        assert set(entry["schema"]["required"]) == {
            "account_id", "campaign_id", "url", "creative_name"
        }

    def test_update_display_item_registered(self):
        assert "update_display_item" in TOOL_REGISTRY
        entry = TOOL_REGISTRY["update_display_item"]
        assert entry["category"] == "items"
        assert entry["handler"] == "item_display_handlers.update_display_item"
        assert entry["annotations"]["destructiveHint"] is True
        assert entry["annotations"]["idempotentHint"] is True
        assert set(entry["schema"]["required"]) == {
            "account_id", "campaign_id", "item_id"
        }

    def test_list_cta_types_registered(self):
        assert "list_cta_types" in TOOL_REGISTRY
        entry = TOOL_REGISTRY["list_cta_types"]
        assert entry["category"] == "resources"
        assert entry["handler"] == "resources.list_cta_types"

    def test_read_item_tools_repointed(self):
        assert TOOL_REGISTRY["list_items"]["handler"] == "item_read_handlers.list_items"
        assert TOOL_REGISTRY["get_item"]["handler"] == "item_read_handlers.get_item"


_WRITE_TOOL_NAMES = frozenset({
    "create_campaign",
    "update_campaign",
    "create_native_item",
    "update_native_item",
    "create_display_item",
    "update_display_item",
})

_CREATE_TOOL_NAMES = frozenset({
    "create_campaign",
    "create_native_item",
    "create_display_item",
})

_UPDATE_TOOL_NAMES = frozenset({
    "update_campaign",
    "update_native_item",
    "update_display_item",
})


class TestToolAnnotations:
    """Tool-annotation coverage for every entry in TOOL_REGISTRY.

    Annotations drive UX in every MCP host (Claude Code, Cursor, Continue, etc.)
    and are required by Anthropic's Connectors Directory.
    """

    def test_every_tool_has_non_empty_title(self):
        for tool_name, tool_config in TOOL_REGISTRY.items():
            assert "title" in tool_config, f"Tool {tool_name} missing 'title'"
            title = tool_config["title"]
            assert isinstance(title, str)
            assert len(title) > 0, f"Tool {tool_name} has empty title"
            assert len(title) <= 50, f"Tool {tool_name} title >50 chars: {title!r}"

    def test_every_tool_has_annotations(self):
        for tool_name, tool_config in TOOL_REGISTRY.items():
            assert "annotations" in tool_config, f"Tool {tool_name} missing 'annotations'"
            ann = tool_config["annotations"]
            assert isinstance(ann, dict)
            is_write = tool_name in _WRITE_TOOL_NAMES
            if is_write:
                # Writes must signal mutation: readOnlyHint must NOT be true.
                assert ann.get("readOnlyHint") is not True, (
                    f"Tool {tool_name} is a write but has readOnlyHint=True"
                )
                # destructiveHint must be explicitly set (true for updates, false for creates).
                assert "destructiveHint" in ann, (
                    f"Tool {tool_name} (write) must set destructiveHint explicitly"
                )
            else:
                assert ann.get("readOnlyHint") is True, (
                    f"Tool {tool_name} (read) must set readOnlyHint=True"
                )

    def test_read_tools_marked_read_only(self):
        for tool_name, tool_config in TOOL_REGISTRY.items():
            if tool_name in _WRITE_TOOL_NAMES:
                continue
            ann = tool_config["annotations"]
            assert ann.get("readOnlyHint") is True, f"{tool_name} should have readOnlyHint"
            assert ann.get("destructiveHint") is not True, (
                f"{tool_name} should not have destructiveHint"
            )

    def test_update_tools_marked_destructive(self):
        """Updates overwrite prior field values — destructiveHint True per MCP spec."""
        for tool_name in _UPDATE_TOOL_NAMES:
            ann = TOOL_REGISTRY[tool_name]["annotations"]
            assert ann.get("destructiveHint") is True, f"{tool_name} should have destructiveHint"
            assert ann.get("readOnlyHint") is not True, (
                f"{tool_name} should not have readOnlyHint"
            )

    def test_create_tools_additive(self):
        """Creates insert new records (additive) — destructiveHint False per MCP spec."""
        for tool_name in _CREATE_TOOL_NAMES:
            ann = TOOL_REGISTRY[tool_name]["annotations"]
            assert ann.get("destructiveHint") is False, (
                f"{tool_name} (create) should be additive (destructiveHint=False)"
            )
            assert ann.get("readOnlyHint") is not True, (
                f"{tool_name} should not have readOnlyHint"
            )

    def test_create_tools_not_idempotent(self):
        for tool_name in _CREATE_TOOL_NAMES:
            ann = TOOL_REGISTRY[tool_name]["annotations"]
            assert ann.get("idempotentHint") is False, (
                f"{tool_name} (create) should be non-idempotent"
            )

    def test_update_tools_idempotent(self):
        for tool_name in _UPDATE_TOOL_NAMES:
            ann = TOOL_REGISTRY[tool_name]["annotations"]
            assert ann.get("idempotentHint") is True, (
                f"{tool_name} (update) should be idempotent"
            )

    def test_titles_unique(self):
        titles = [tool_config["title"] for tool_config in TOOL_REGISTRY.values()]
        duplicates = {t for t in titles if titles.count(t) > 1}
        assert not duplicates, f"Duplicate titles in registry: {duplicates}"

    def test_handle_list_tools_round_trip(self):
        """handle_list_tools() round-trips title + annotations from registry to types.Tool."""
        import asyncio
        from realize.realize_server import handle_list_tools

        tools = asyncio.run(handle_list_tools())
        by_name = {t.name: t for t in tools}

        # Sample of read + write tools
        for name in ("search_accounts", "list_campaigns", "create_campaign", "update_native_item"):
            assert name in by_name, f"{name} missing from handle_list_tools output"
            tool = by_name[name]
            registry_title = TOOL_REGISTRY[name]["title"]
            # Tool.title (spec 2025-06-18+)
            assert tool.title == registry_title, f"{name} Tool.title mismatch"
            # annotations.title fallback (older MCP hosts)
            assert tool.annotations is not None, f"{name} missing annotations"
            assert tool.annotations.title == registry_title, f"{name} annotations.title mismatch"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])