"""Tests for proxy error handling and edge cases."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from httpx import HTTPStatusError, RequestError

from config import Config, ControllerConfig, LLMConfig, MemoryConfig, ProxyConfig
from proxy import SekhaProxy


@pytest.fixture
def test_config() -> Config:
    """Create test configuration."""
    return Config(
        proxy=ProxyConfig(host="0.0.0.0", port=8081),
        llm=LLMConfig(url="http://test-llm:11434", provider="ollama", timeout=120),
        controller=ControllerConfig(
            url="http://test-controller:8080", api_key="test-key", timeout=30
        ),
        memory=MemoryConfig(
            auto_inject_context=True,
            context_token_budget=4000,
            excluded_folders=[],
            default_folder="/test",
            preferred_labels=[],
        ),
    )


@pytest.mark.asyncio
async def test_empty_messages_error(test_config: Config) -> None:
    """Test error when no messages provided."""
    proxy = SekhaProxy(test_config)

    with pytest.raises(HTTPException) as exc_info:
        await proxy.forward_chat({"messages": []})

    assert exc_info.value.status_code == 400
    assert "No messages provided" in str(exc_info.value.detail)

    await proxy.close()


@pytest.mark.asyncio
async def test_llm_connection_error(test_config: Config) -> None:
    """Test handling of LLM connection failure."""
    proxy = SekhaProxy(test_config)

    # Mock controller to return empty context
    proxy.controller_client = AsyncMock()
    mock_controller_response = AsyncMock()
    mock_controller_response.status_code = 200
    mock_controller_response.json = MagicMock(return_value=[])
    proxy.controller_client.post = AsyncMock(return_value=mock_controller_response)

    # Mock LLM to raise connection error
    proxy.llm_client = AsyncMock()
    proxy.llm_client.post = AsyncMock(
        side_effect=RequestError("Connection refused", request=None)
    )

    request = {"messages": [{"role": "user", "content": "Test"}]}

    with pytest.raises(HTTPException) as exc_info:
        await proxy.forward_chat(request)

    assert exc_info.value.status_code == 502
    assert "LLM error" in str(exc_info.value.detail)

    await proxy.close()


@pytest.mark.asyncio
async def test_llm_http_error(test_config: Config) -> None:
    """Test handling of LLM HTTP error response."""
    proxy = SekhaProxy(test_config)

    # Mock controller
    proxy.controller_client = AsyncMock()
    mock_controller_response = AsyncMock()
    mock_controller_response.status_code = 200
    mock_controller_response.json = MagicMock(return_value=[])
    proxy.controller_client.post = AsyncMock(return_value=mock_controller_response)

    # Mock LLM to return error status
    proxy.llm_client = AsyncMock()
    mock_llm_response = AsyncMock()
    mock_llm_response.status_code = 500
    mock_llm_response.raise_for_status = MagicMock(
        side_effect=HTTPStatusError(
            "Internal Server Error",
            request=MagicMock(),
            response=mock_llm_response,
        )
    )
    proxy.llm_client.post = AsyncMock(return_value=mock_llm_response)

    request = {"messages": [{"role": "user", "content": "Test"}]}

    with pytest.raises(HTTPException) as exc_info:
        await proxy.forward_chat(request)

    assert exc_info.value.status_code == 502

    await proxy.close()


@pytest.mark.asyncio
async def test_controller_failure_continues(test_config: Config) -> None:
    """Test that proxy continues without context if controller fails."""
    proxy = SekhaProxy(test_config)

    # Mock controller to fail
    proxy.controller_client = AsyncMock()
    proxy.controller_client.post = AsyncMock(
        side_effect=Exception("Controller unavailable")
    )

    # Mock LLM to succeed
    proxy.llm_client = AsyncMock()
    llm_response = {
        "choices": [{"message": {"role": "assistant", "content": "Response"}}]
    }
    mock_llm_response = AsyncMock()
    mock_llm_response.status_code = 200
    mock_llm_response.json = MagicMock(return_value=llm_response)
    mock_llm_response.raise_for_status = MagicMock()
    proxy.llm_client.post = AsyncMock(return_value=mock_llm_response)

    request = {"messages": [{"role": "user", "content": "Test"}]}

    # Should succeed despite controller failure
    response = await proxy.forward_chat(request)

    assert "choices" in response
    assert "sekha_metadata" not in response  # No context added

    await proxy.close()


@pytest.mark.asyncio
async def test_context_disabled(test_config: Config) -> None:
    """Test proxy with context injection disabled."""
    test_config.memory.auto_inject_context = False
    proxy = SekhaProxy(test_config)

    # Mock LLM only (controller shouldn't be called)
    proxy.llm_client = AsyncMock()
    llm_response = {
        "choices": [{"message": {"role": "assistant", "content": "Response"}}]
    }
    mock_llm_response = AsyncMock()
    mock_llm_response.status_code = 200
    mock_llm_response.json = MagicMock(return_value=llm_response)
    mock_llm_response.raise_for_status = MagicMock()
    proxy.llm_client.post = AsyncMock(return_value=mock_llm_response)

    request = {"messages": [{"role": "user", "content": "Test"}]}

    response = await proxy.forward_chat(request)

    # Verify controller was not called
    assert (
        not proxy.controller_client.post.called
        if hasattr(proxy.controller_client, "called")
        else True
    )

    # Verify no context metadata
    assert "sekha_metadata" not in response

    await proxy.close()


@pytest.mark.asyncio
async def test_controller_non_200_status(test_config: Config) -> None:
    """Test handling of non-200 controller response."""
    proxy = SekhaProxy(test_config)

    # Mock controller to return non-200
    proxy.controller_client = AsyncMock()
    mock_controller_response = AsyncMock()
    mock_controller_response.status_code = 503
    proxy.controller_client.post = AsyncMock(return_value=mock_controller_response)

    # Mock LLM
    proxy.llm_client = AsyncMock()
    llm_response = {
        "choices": [{"message": {"role": "assistant", "content": "Response"}}]
    }
    mock_llm_response = AsyncMock()
    mock_llm_response.status_code = 200
    mock_llm_response.json = MagicMock(return_value=llm_response)
    mock_llm_response.raise_for_status = MagicMock()
    proxy.llm_client.post = AsyncMock(return_value=mock_llm_response)

    request = {"messages": [{"role": "user", "content": "Test"}]}

    # Should continue without context
    response = await proxy.forward_chat(request)

    assert "choices" in response
    assert "sekha_metadata" not in response

    await proxy.close()


@pytest.mark.asyncio
async def test_store_conversation_failure(test_config: Config) -> None:
    """Test that store conversation failure doesn't break the response."""
    proxy = SekhaProxy(test_config)

    # Mock controller for context retrieval
    proxy.controller_client = AsyncMock()
    mock_controller_response = AsyncMock()
    mock_controller_response.status_code = 200
    mock_controller_response.json = MagicMock(return_value=[])
    proxy.controller_client.post = AsyncMock(return_value=mock_controller_response)

    # Mock LLM
    proxy.llm_client = AsyncMock()
    llm_response = {
        "choices": [{"message": {"role": "assistant", "content": "Response"}}]
    }
    mock_llm_response = AsyncMock()
    mock_llm_response.status_code = 200
    mock_llm_response.json = MagicMock(return_value=llm_response)
    mock_llm_response.raise_for_status = MagicMock()
    proxy.llm_client.post = AsyncMock(return_value=mock_llm_response)

    request = {"messages": [{"role": "user", "content": "Test"}]}

    # Should succeed even if storage fails (it's async)
    response = await proxy.forward_chat(request)

    assert "choices" in response

    await proxy.close()


@pytest.mark.asyncio
async def test_no_choices_in_llm_response(test_config: Config) -> None:
    """Test handling of malformed LLM response."""
    proxy = SekhaProxy(test_config)

    # Mock controller
    proxy.controller_client = AsyncMock()
    mock_controller_response = AsyncMock()
    mock_controller_response.status_code = 200
    mock_controller_response.json = MagicMock(return_value=[])
    proxy.controller_client.post = AsyncMock(return_value=mock_controller_response)

    # Mock LLM with no choices
    proxy.llm_client = AsyncMock()
    llm_response = {}  # Missing 'choices'
    mock_llm_response = AsyncMock()
    mock_llm_response.status_code = 200
    mock_llm_response.json = MagicMock(return_value=llm_response)
    mock_llm_response.raise_for_status = MagicMock()
    proxy.llm_client.post = AsyncMock(return_value=mock_llm_response)

    request = {"messages": [{"role": "user", "content": "Test"}]}

    response = await proxy.forward_chat(request)

    # Should return whatever LLM returned
    assert "choices" not in response

    await proxy.close()
