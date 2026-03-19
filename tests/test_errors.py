"""Unit tests for error classification utilities."""
import pytest
import sys
import pathlib
sys.path.append(str(pathlib.Path(__file__).parent.parent / "src"))
from unittest.mock import Mock
import httpx
from realize.tools.errors import ToolInputError, classify_api_error


class TestToolInputError:
    """Test ToolInputError exception class."""

    def test_is_exception(self):
        err = ToolInputError("missing param")
        assert isinstance(err, Exception)

    def test_message_preserved(self):
        err = ToolInputError("account_id is required")
        assert str(err) == "account_id is required"


class TestClassifyApiError:
    """Test classify_api_error function."""

    def test_4xx_proxied(self):
        for status in [400, 401, 403, 404, 422, 429]:
            response = Mock(status_code=status)
            exc = httpx.HTTPStatusError(
                f"{status} error", request=Mock(), response=response
            )
            result = classify_api_error(exc)
            assert str(exc) == result, f"4xx ({status}) should be proxied verbatim"

    def test_5xx_includes_status_code(self):
        for status in [500, 502, 503, 504]:
            response = Mock(status_code=status)
            exc = httpx.HTTPStatusError(
                f"{status} error", request=Mock(), response=response
            )
            result = classify_api_error(exc)
            assert f"Realize API returned {status}" in result
            assert "Please try again later" in result
            # Should NOT contain the original exception message
            assert f"{status} error" not in result

    def test_timeout(self):
        exc = httpx.ReadTimeout("read timed out")
        result = classify_api_error(exc)
        assert "timed out" in result
        assert "Realize API" in result
        # Should NOT leak the original message
        assert "read timed out" not in result

    def test_connect_error(self):
        exc = httpx.ConnectError("Connection refused")
        result = classify_api_error(exc)
        assert "unreachable" in result
        assert "Realize API" in result
        # Should NOT leak the original message
        assert "Connection refused" not in result

    def test_unexpected_error(self):
        for exc in [
            RuntimeError("something broke"),
            KeyError("missing_key"),
            TypeError("bad type"),
        ]:
            result = classify_api_error(exc)
            assert result == "An unexpected error occurred. Please try again later."
            # Should NOT leak the original message
            assert "something broke" not in result
            assert "missing_key" not in result

    def test_timeout_subclass(self):
        """TimeoutException subclasses should also be classified as timeouts."""
        exc = httpx.ConnectTimeout("connect timed out")
        result = classify_api_error(exc)
        assert "timed out" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
