"""Tests for OAuth context variable isolation."""
import pathlib
import sys
sys.path.append(str(pathlib.Path(__file__).parent.parent / "src"))

import asyncio
import pytest

from realize.oauth.context import (
    set_session_token,
    get_session_token,
    clear_session_token,
)
from realize.auth import SSETokenAuth


class TestContextIsolation:
    """Tests for context variable token isolation."""

    @pytest.mark.asyncio
    async def test_basic_set_and_get(self):
        """Test basic set and get of session token."""
        set_session_token("test-token")
        assert get_session_token() == "test-token"
        clear_session_token()
        assert get_session_token() is None

    @pytest.mark.asyncio
    async def test_context_isolation_between_concurrent_tasks(self):
        """Test that tokens are isolated between concurrent async tasks."""
        results = {}

        async def client_a():
            set_session_token("token_A")
            await asyncio.sleep(0.1)  # Simulate work, allow interleaving
            results['a'] = get_session_token()

        async def client_b():
            set_session_token("token_B")
            await asyncio.sleep(0.1)  # Simulate work
            results['b'] = get_session_token()

        await asyncio.gather(client_a(), client_b())

        assert results['a'] == "token_A", f"Expected token_A, got {results['a']}"
        assert results['b'] == "token_B", f"Expected token_B, got {results['b']}"

    @pytest.mark.asyncio
    async def test_context_isolation_with_multiple_tasks(self):
        """Test token isolation with many concurrent tasks."""
        num_tasks = 10
        results = {}

        async def client_task(task_id: int):
            token = f"token_{task_id}"
            set_session_token(token)
            # Yield to other tasks to test isolation
            await asyncio.sleep(0.05)
            results[task_id] = get_session_token()

        tasks = [client_task(i) for i in range(num_tasks)]
        await asyncio.gather(*tasks)

        for i in range(num_tasks):
            assert results[i] == f"token_{i}", f"Task {i}: expected token_{i}, got {results[i]}"

    @pytest.mark.asyncio
    async def test_clear_only_affects_current_context(self):
        """Test that clearing token in one context doesn't affect others."""
        results = {}

        async def client_a():
            set_session_token("token_A")
            await asyncio.sleep(0.05)
            clear_session_token()  # Clear in this context
            results['a_after_clear'] = get_session_token()

        async def client_b():
            set_session_token("token_B")
            await asyncio.sleep(0.1)  # Wait longer to check after A clears
            results['b_after_a_clear'] = get_session_token()

        await asyncio.gather(client_a(), client_b())

        assert results['a_after_clear'] is None
        assert results['b_after_a_clear'] == "token_B"

    @pytest.mark.asyncio
    async def test_child_tasks_inherit_context(self):
        """Test that child tasks inherit parent context via create_task."""
        parent_token = "parent_token"
        child_result = {}

        async def child_task():
            # Child should inherit parent's context
            child_result['token'] = get_session_token()

        async def parent_task():
            set_session_token(parent_token)
            # Create child task - it should inherit the context
            task = asyncio.create_task(child_task())
            await task

        await parent_task()

        assert child_result['token'] == parent_token


class TestSSETokenAuthWithContext:
    """Tests for SSETokenAuth using context variables."""

    @pytest.mark.asyncio
    async def test_sse_auth_reads_from_context(self):
        """Test that SSETokenAuth reads token from current context."""
        auth = SSETokenAuth()

        # No token set
        header = await auth.get_auth_header()
        assert header is None

        # Set token in context
        set_session_token("context-token")

        header = await auth.get_auth_header()
        assert header == {"Authorization": "Bearer context-token"}

        # Clear token
        clear_session_token()
        header = await auth.get_auth_header()
        assert header is None

    @pytest.mark.asyncio
    async def test_sse_auth_isolation_between_contexts(self):
        """Test SSETokenAuth returns correct token per context."""
        auth = SSETokenAuth()
        results = {}

        async def client_a():
            set_session_token("token_A")
            await asyncio.sleep(0.05)
            header = await auth.get_auth_header()
            results['a'] = header

        async def client_b():
            set_session_token("token_B")
            await asyncio.sleep(0.05)
            header = await auth.get_auth_header()
            results['b'] = header

        await asyncio.gather(client_a(), client_b())

        assert results['a'] == {"Authorization": "Bearer token_A"}
        assert results['b'] == {"Authorization": "Bearer token_B"}

    @pytest.mark.asyncio
    async def test_sse_auth_uses_context_token(self):
        """Test that SSETokenAuth always reads from async context."""
        auth = SSETokenAuth()
        set_session_token("my-token")

        header = await auth.get_auth_header()
        assert header == {"Authorization": "Bearer my-token"}

        clear_session_token()
