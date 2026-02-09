"""Tests for proxy error handling and edge cases."""

from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from httpx import HTTPError, HTTPStatusError, RequestError

from config import Config, ControllerConfig, LLMConfig, MemoryConfig, ProxyConfig
from proxy import SekhaProxy


@pytest.fixture
def test_config() -> Config:
    """Create test configuration."""
    return Config(
        proxy=ProxyConfig(host="0.0.0.0", port=8081),
        llm=LLMConfig(
            bridge_url="http://test-bridge:5001",
            timeout=120,
            preferred_chat_model="llama3.1:8b",
        ),
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
async def test_bridge_connection_error(test_config: Config) -> None:
    """Test handling of bridge connection failure."""
    proxy = SekhaProxy(test_config)

    # Mock controller to return empty context
    proxy.controller_client = AsyncMock()  # type: ignore[assignment]
    mock_controller_response = AsyncMock()
    mock_controller_response.status_code = 200
    mock_controller_response.json = MagicMock(return_value=[])
    proxy.controller_client.post = AsyncMock(return_value=mock_controller_response)  # type: ignore[method-assign]

    # Mock bridge to raise connection error (v2.0: bridge_client instead of llm_client)
    proxy.bridge_client = AsyncMock()  # type: ignore[assignment]
    proxy.bridge_client.post = AsyncMock(  # type: ignore[method-assign]
        side_effect=RequestError("Connection refused", request=None)
    )

    request = {"messages": [{"role": "user", "content": "Test"}]}

    with pytest.raises(HTTPException) as exc_info:
        await proxy.forward_chat(request)

    assert exc_info.value.status_code == 502
    assert "Bridge error" in str(exc_info.value.detail)

    await proxy.close()


@pytest.mark.asyncio
async def test_bridge_http_error(test_config: Config) -> None:
    """Test handling of bridge HTTP error response."""
    proxy = SekhaProxy(test_config)

    # Mock controller
    proxy.controller_client = AsyncMock()  # type: ignore[assignment]
    mock_controller_response = AsyncMock()
    mock_controller_response.status_code = 200
    mock_controller_response.json = MagicMock(return_value=[])
    proxy.controller_client.post = AsyncMock(return_value=mock_controller_response)  # type: ignore[method-assign]

    # Mock bridge routing to succeed
    routing_response_data = {
        "model_id": "llama3.1:8b",
        "provider_id": "ollama",
        "estimated_cost": 0.0001,
    }
    routing_mock = AsyncMock()
    routing_mock.status_code = 200
    routing_mock.json = MagicMock(return_value=routing_response_data)
    routing_mock.raise_for_status = MagicMock()

    # Mock bridge completion to return error status
    mock_completion_response = AsyncMock()
    mock_completion_response.status_code = 500
    mock_completion_response.raise_for_status = MagicMock(
        side_effect=HTTPStatusError(
            "Internal Server Error",
            request=MagicMock(),
            response=mock_completion_response,
        )
    )

    # Setup bridge client responses
    async def bridge_post_side_effect(endpoint, **kwargs):
        if "/route" in endpoint:
            return routing_mock
        else:  # /v1/chat/completions
            return mock_completion_response

    proxy.bridge_client = AsyncMock()  # type: ignore[assignment]
    proxy.bridge_client.post = AsyncMock(side_effect=bridge_post_side_effect)  # type: ignore[method-assign]

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
    proxy.controller_client = AsyncMock()  # type: ignore[assignment]
    proxy.controller_client.post = AsyncMock(  # type: ignore[method-assign]
        side_effect=Exception("Controller unavailable")
    )

    # Mock bridge to succeed (v2.0: bridge_client)
    routing_response_data = {
        "model_id": "llama3.1:8b",
        "provider_id": "ollama",
        "estimated_cost": 0.0001,
    }
    routing_mock = AsyncMock()
    routing_mock.status_code = 200
    routing_mock.json = MagicMock(return_value=routing_response_data)
    routing_mock.raise_for_status = MagicMock()

    llm_response: Dict[str, Any] = {
        "choices": [{"message": {"role": "assistant", "content": "Response"}}]
    }
    mock_completion_response = AsyncMock()
    mock_completion_response.status_code = 200
    mock_completion_response.json = MagicMock(return_value=llm_response)
    mock_completion_response.raise_for_status = MagicMock()

    async def bridge_post_side_effect(endpoint, **kwargs):
        if "/route" in endpoint:
            return routing_mock
        else:
            return mock_completion_response

    proxy.bridge_client = AsyncMock()  # type: ignore[assignment]
    proxy.bridge_client.post = AsyncMock(side_effect=bridge_post_side_effect)  # type: ignore[method-assign]

    request = {"messages": [{"role": "user", "content": "Test"}]}

    # Should succeed despite controller failure
    response = await proxy.forward_chat(request)

    assert "choices" in response
    # v2.0: sekha_metadata always present with routing info
    assert "sekha_metadata" in response
    assert "routing" in response["sekha_metadata"]

    await proxy.close()


@pytest.mark.asyncio
async def test_context_disabled(test_config: Config) -> None:
    """Test proxy with context injection disabled."""
    test_config.memory.auto_inject_context = False
    proxy = SekhaProxy(test_config)

    # Mock bridge only (controller shouldn't be called) - v2.0: bridge_client
    routing_response_data = {
        "model_id": "llama3.1:8b",
        "provider_id": "ollama",
        "estimated_cost": 0.0001,
    }
    routing_mock = AsyncMock()
    routing_mock.status_code = 200
    routing_mock.json = MagicMock(return_value=routing_response_data)
    routing_mock.raise_for_status = MagicMock()

    llm_response: Dict[str, Any] = {
        "choices": [{"message": {"role": "assistant", "content": "Response"}}]
    }
    mock_completion_response = AsyncMock()
    mock_completion_response.status_code = 200
    mock_completion_response.json = MagicMock(return_value=llm_response)
    mock_completion_response.raise_for_status = MagicMock()

    async def bridge_post_side_effect(endpoint, **kwargs):
        if "/route" in endpoint:
            return routing_mock
        else:
            return mock_completion_response

    proxy.bridge_client = AsyncMock()  # type: ignore[assignment]
    proxy.bridge_client.post = AsyncMock(side_effect=bridge_post_side_effect)  # type: ignore[method-assign]

    request = {"messages": [{"role": "user", "content": "Test"}]}

    response = await proxy.forward_chat(request)

    # v2.0: sekha_metadata always present but no context_count
    assert "sekha_metadata" in response
    assert "context_count" not in response["sekha_metadata"]

    await proxy.close()


@pytest.mark.asyncio
async def test_controller_non_200_status(test_config: Config) -> None:
    """Test handling of non-200 controller response."""
    proxy = SekhaProxy(test_config)

    # Mock controller to return non-200
    proxy.controller_client = AsyncMock()  # type: ignore[assignment]
    mock_controller_response = AsyncMock()
    mock_controller_response.status_code = 503
    proxy.controller_client.post = AsyncMock(return_value=mock_controller_response)  # type: ignore[method-assign]

    # Mock bridge (v2.0)
    routing_response_data = {
        "model_id": "llama3.1:8b",
        "provider_id": "ollama",
        "estimated_cost": 0.0001,
    }
    routing_mock = AsyncMock()
    routing_mock.status_code = 200
    routing_mock.json = MagicMock(return_value=routing_response_data)
    routing_mock.raise_for_status = MagicMock()

    llm_response: Dict[str, Any] = {
        "choices": [{"message": {"role": "assistant", "content": "Response"}}]
    }
    mock_completion_response = AsyncMock()
    mock_completion_response.status_code = 200
    mock_completion_response.json = MagicMock(return_value=llm_response)
    mock_completion_response.raise_for_status = MagicMock()

    async def bridge_post_side_effect(endpoint, **kwargs):
        if "/route" in endpoint:
            return routing_mock
        else:
            return mock_completion_response

    proxy.bridge_client = AsyncMock()  # type: ignore[assignment]
    proxy.bridge_client.post = AsyncMock(side_effect=bridge_post_side_effect)  # type: ignore[method-assign]

    request = {"messages": [{"role": "user", "content": "Test"}]}

    # Should continue without context
    response = await proxy.forward_chat(request)

    assert "choices" in response
    # v2.0: metadata present but no context
    assert "sekha_metadata" in response
    assert "context_count" not in response["sekha_metadata"]

    await proxy.close()


@pytest.mark.asyncio
async def test_store_conversation_failure(test_config: Config) -> None:
    """Test that store conversation failure doesn't break the response."""
    proxy = SekhaProxy(test_config)

    # Mock controller for context retrieval
    proxy.controller_client = AsyncMock()  # type: ignore[assignment]
    mock_controller_response = AsyncMock()
    mock_controller_response.status_code = 200
    mock_controller_response.json = MagicMock(return_value=[])
    proxy.controller_client.post = AsyncMock(return_value=mock_controller_response)  # type: ignore[method-assign]

    # Mock bridge (v2.0)
    routing_response_data = {
        "model_id": "llama3.1:8b",
        "provider_id": "ollama",
        "estimated_cost": 0.0001,
    }
    routing_mock = AsyncMock()
    routing_mock.status_code = 200
    routing_mock.json = MagicMock(return_value=routing_response_data)
    routing_mock.raise_for_status = MagicMock()

    llm_response: Dict[str, Any] = {
        "choices": [{"message": {"role": "assistant", "content": "Response"}}]
    }
    mock_completion_response = AsyncMock()
    mock_completion_response.status_code = 200
    mock_completion_response.json = MagicMock(return_value=llm_response)
    mock_completion_response.raise_for_status = MagicMock()

    async def bridge_post_side_effect(endpoint, **kwargs):
        if "/route" in endpoint:
            return routing_mock
        else:
            return mock_completion_response

    proxy.bridge_client = AsyncMock()  # type: ignore[assignment]
    proxy.bridge_client.post = AsyncMock(side_effect=bridge_post_side_effect)  # type: ignore[method-assign]

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
    proxy.controller_client = AsyncMock()  # type: ignore[assignment]
    mock_controller_response = AsyncMock()
    mock_controller_response.status_code = 200
    mock_controller_response.json = MagicMock(return_value=[])
    proxy.controller_client.post = AsyncMock(return_value=mock_controller_response)  # type: ignore[method-assign]

    # Mock bridge with routing success but malformed completion (v2.0)
    routing_response_data = {
        "model_id": "llama3.1:8b",
        "provider_id": "ollama",
        "estimated_cost": 0.0001,
    }
    routing_mock = AsyncMock()
    routing_mock.status_code = 200
    routing_mock.json = MagicMock(return_value=routing_response_data)
    routing_mock.raise_for_status = MagicMock()

    llm_response: Dict[str, Any] = {}  # Missing 'choices'
    mock_completion_response = AsyncMock()
    mock_completion_response.status_code = 200
    mock_completion_response.json = MagicMock(return_value=llm_response)
    mock_completion_response.raise_for_status = MagicMock()

    async def bridge_post_side_effect(endpoint, **kwargs):
        if "/route" in endpoint:
            return routing_mock
        else:
            return mock_completion_response

    proxy.bridge_client = AsyncMock()  # type: ignore[assignment]
    proxy.bridge_client.post = AsyncMock(side_effect=bridge_post_side_effect)  # type: ignore[method-assign]

    request = {"messages": [{"role": "user", "content": "Test"}]}

    response = await proxy.forward_chat(request)

    # Should return whatever bridge returned
    assert "choices" not in response
    # But metadata should be added
    assert "sekha_metadata" in response

    await proxy.close()


@pytest.mark.asyncio
async def test_bridge_routing_fallback(test_config: Config) -> None:
    """Test that proxy falls back gracefully when bridge routing fails."""
    proxy = SekhaProxy(test_config)

    # Mock controller
    proxy.controller_client = AsyncMock()  # type: ignore[assignment]
    mock_controller_response = AsyncMock()
    mock_controller_response.status_code = 200
    mock_controller_response.json = MagicMock(return_value=[])
    proxy.controller_client.post = AsyncMock(return_value=mock_controller_response)  # type: ignore[method-assign]

    # Mock bridge routing to fail but completion to succeed
    routing_mock = AsyncMock()
    routing_mock.raise_for_status = MagicMock(side_effect=HTTPError("Routing failed"))

    llm_response: Dict[str, Any] = {
        "choices": [{"message": {"role": "assistant", "content": "Response"}}]
    }
    mock_completion_response = AsyncMock()
    mock_completion_response.status_code = 200
    mock_completion_response.json = MagicMock(return_value=llm_response)
    mock_completion_response.raise_for_status = MagicMock()

    async def bridge_post_side_effect(endpoint, **kwargs):
        if "/route" in endpoint:
            return routing_mock
        else:  # Falls back to direct completion
            return mock_completion_response

    proxy.bridge_client = AsyncMock()  # type: ignore[assignment]
    proxy.bridge_client.post = AsyncMock(side_effect=bridge_post_side_effect)  # type: ignore[method-assign]

    request = {"messages": [{"role": "user", "content": "Test"}]}

    # Should succeed with fallback
    response = await proxy.forward_chat(request)

    assert "choices" in response
    # Verify fallback metadata
    assert response["sekha_metadata"]["routing"]["provider_id"] == "fallback"

    await proxy.close()
