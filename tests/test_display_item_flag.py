"""Tests for the ENABLE_DISPLAY_ITEM_TOOLS feature flag."""
import pytest

from realize.realize_server import handle_call_tool
from realize.tools.registry import TOOL_REGISTRY, get_all_tools


_DISPLAY_TOOLS = {"create_display_item", "update_display_item"}


@pytest.fixture
def _stub_config(monkeypatch):
    """Override only the flag on the real config; keep other attrs intact."""
    from realize import config as config_module

    monkeypatch.setattr(config_module.config, "enable_display_item_tools", False)
    yield config_module.config


class TestDisplayItemFlagDefault:
    def test_display_tools_registered_in_static_registry(self):
        """Registry itself always contains the tools — gating happens in get_all_tools()."""
        assert _DISPLAY_TOOLS.issubset(TOOL_REGISTRY.keys())

    def test_display_tools_hidden_by_default(self, _stub_config):
        _stub_config.enable_display_item_tools = False
        tools = get_all_tools()
        assert _DISPLAY_TOOLS.isdisjoint(tools.keys())

    def test_native_item_tools_still_present_when_display_off(self, _stub_config):
        _stub_config.enable_display_item_tools = False
        tools = get_all_tools()
        assert "create_native_item" in tools
        assert "update_native_item" in tools
        assert "list_items" in tools
        assert "get_item" in tools

    def test_display_tools_shown_when_flag_true(self, _stub_config):
        _stub_config.enable_display_item_tools = True
        tools = get_all_tools()
        assert _DISPLAY_TOOLS.issubset(tools.keys())


class TestDisplayItemFlagDispatcher:
    @pytest.mark.asyncio
    async def test_create_display_item_rejected_when_flag_off(self, _stub_config):
        _stub_config.enable_display_item_tools = False
        with pytest.raises(ValueError, match="Unknown tool: create_display_item"):
            await handle_call_tool("create_display_item", {
                "account_id": "acme-inc",
                "campaign_id": "49184816",
                "url": "https://example.com/landing",
                "ad_tag": "<script/>",
                "dimensions": [{"width": 300, "height": 250}],
                "creative_name": "Acme 300x250",
            })

    @pytest.mark.asyncio
    async def test_update_display_item_rejected_when_flag_off(self, _stub_config):
        _stub_config.enable_display_item_tools = False
        with pytest.raises(ValueError, match="Unknown tool: update_display_item"):
            await handle_call_tool("update_display_item", {
                "account_id": "acme-inc",
                "campaign_id": "49184816",
                "item_id": "987654321",
                "is_active": False,
            })


class TestDisplayItemFlagConfigParsing:
    def test_env_var_default_false(self, monkeypatch):
        from realize.config import Config

        # conftest defaults the env var to "true" for the test session; clear it
        # to verify the model's own default is False.
        monkeypatch.delenv("ENABLE_DISPLAY_ITEM_TOOLS", raising=False)
        cfg = Config(realize_client_id="x", realize_client_secret="y", _env_file=None)
        assert cfg.enable_display_item_tools is False

    @pytest.mark.parametrize("env_value,expected", [
        ("true", True),
        ("True", True),
        ("1", True),
        ("false", False),
        ("0", False),
    ])
    def test_env_var_parsed(self, monkeypatch, env_value, expected):
        from realize.config import Config

        monkeypatch.setenv("ENABLE_DISPLAY_ITEM_TOOLS", env_value)
        cfg = Config(realize_client_id="x", realize_client_secret="y", _env_file=None)
        assert cfg.enable_display_item_tools is expected
