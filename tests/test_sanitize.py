"""Tests for OAuth register input sanitizer."""
import pathlib
import sys
sys.path.append(str(pathlib.Path(__file__).parent.parent / "src"))

import pytest

from realize.oauth.sanitize import sanitize, sanitize_str, MAX_LEN, MAX_DEPTH, SanitizeError


class TestSanitizeStr:
    def test_strips_crlf(self):
        assert sanitize_str("foo\r\nbar") == "foobar"

    def test_strips_ansi_csi(self):
        assert sanitize_str("\x1b[31mred\x1b[0m") == "red"

    def test_strips_jndi(self):
        assert sanitize_str("${jndi:ldap://x/a}") == ""

    def test_strips_nested_jndi_bypass(self):
        assert sanitize_str("${${lower:j}ndi:ldap://x}") == ""

    def test_strips_unicode_nfkc_bypass(self):
        assert sanitize_str("\uff04\uff5bjndi:ldap://x\uff5d") == ""

    def test_strips_all_control_chars(self):
        assert sanitize_str("a\x00b\x01c\x1fd\x7fe") == "abcde"

    def test_strips_c1_control_chars(self):
        """C1 controls (U+0080–U+009F) can act as CSI/escape on some terminals."""
        assert sanitize_str("a\x80b\x9bc\x9fd") == "abcd"

    def test_preserves_printable_ascii(self):
        s = "Hello, World! 123 ~!@#$%^&*()"
        assert sanitize_str(s) == s

    def test_preserves_non_substitution_dollar_sign(self):
        assert sanitize_str("price: $10.00") == "price: $10.00"

    def test_truncates_to_max_len(self):
        assert len(sanitize_str("x" * (MAX_LEN + 1000))) == MAX_LEN


class TestSanitize:
    def test_recurses_into_list(self):
        assert sanitize(["a\r\n", "b\x00c"]) == ["a", "bc"]

    def test_recurses_into_dict_values(self):
        assert sanitize({"k": "v\r\n"}) == {"k": "v"}

    def test_sanitizes_dict_string_keys(self):
        assert sanitize({"k\r\nbad": "v"}) == {"kbad": "v"}

    def test_passes_through_non_string_scalars(self):
        assert sanitize({"k": 123, "n": None, "b": True}) == {"k": 123, "n": None, "b": True}

    def test_handles_nested_structures(self):
        inp = {"outer": [{"inner": "x\r\ny"}, "${jndi:x}"]}
        assert sanitize(inp) == {"outer": [{"inner": "xy"}, ""]}

    def test_accepts_at_max_depth(self):
        """Exactly MAX_DEPTH levels of dict nesting must not raise."""
        obj = "leaf"
        for _ in range(MAX_DEPTH):
            obj = {"n": obj}
        sanitize(obj)

    def test_raises_on_deep_dict(self):
        obj = "leaf"
        for _ in range(MAX_DEPTH + 1):
            obj = {"n": obj}
        with pytest.raises(SanitizeError):
            sanitize(obj)

    def test_raises_on_deep_list(self):
        obj: list = []
        cur = obj
        for _ in range(MAX_DEPTH + 1):
            new: list = []
            cur.append(new)
            cur = new
        with pytest.raises(SanitizeError):
            sanitize(obj)
