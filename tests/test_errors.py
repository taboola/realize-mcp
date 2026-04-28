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

    def _make_4xx(self, status, body=None, text=None):
        response = Mock(status_code=status)
        if body is not None:
            response.json = Mock(return_value=body)
            response.text = text if text is not None else ""
        else:
            response.json = Mock(side_effect=ValueError("no json"))
            response.text = text or ""
        return httpx.HTTPStatusError(f"{status} error", request=Mock(), response=response)

    def test_4xx_includes_status_code(self):
        for status in [400, 401, 403, 404, 422, 429]:
            exc = self._make_4xx(status, body={"message": "oops"})
            result = classify_api_error(exc)
            assert f"Realize API returned {status}" in result

    def test_4xx_includes_json_message(self):
        exc = self._make_4xx(400, body={"message": "Invalid enum value for spending_limit_model"})
        result = classify_api_error(exc)
        assert "400" in result
        assert "message=Invalid enum value for spending_limit_model" in result

    def test_4xx_includes_error_and_details(self):
        exc = self._make_4xx(422, body={
            "message": "validation failed",
            "error": "INVALID_FIELD",
            "details": {"field": "cpc", "reason": "required"},
        })
        result = classify_api_error(exc)
        assert "message=validation failed" in result
        assert "error=INVALID_FIELD" in result
        assert "details=" in result
        assert "cpc" in result

    def test_4xx_text_fallback_when_not_json(self):
        exc = self._make_4xx(400, body=None, text="plain text error body")
        result = classify_api_error(exc)
        assert "plain text error body" in result
        assert "400" in result

    def test_4xx_empty_body(self):
        exc = self._make_4xx(400, body=None, text="")
        result = classify_api_error(exc)
        assert "no response body" in result
        assert "400" in result

    def test_4xx_body_truncated(self):
        huge = "x" * 50_000
        exc = self._make_4xx(400, body={"message": huge})
        result = classify_api_error(exc)
        # Prefix ("Realize API returned 400: ") + 1000-char body cap
        assert len(result) < 1100

    def test_4xx_unknown_json_shape(self):
        exc = self._make_4xx(400, body=["a", "b", "c"])
        result = classify_api_error(exc)
        # Falls through to json.dumps of the list
        assert "400" in result
        assert '["a","b","c"]' in result

    def test_4xx_skips_empty_values(self):
        exc = self._make_4xx(400, body={"message": "real", "error": "", "details": None})
        result = classify_api_error(exc)
        assert "message=real" in result
        assert "error=" not in result
        assert "details=" not in result

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
