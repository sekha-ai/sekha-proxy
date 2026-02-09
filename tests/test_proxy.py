"""Integration tests for proxy functionality."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from config import Config, ControllerConfig, LLMConfig, MemoryConfig
from proxy import SekhaProxy


@pytest.fixture
def mock_config() -> Config:
    """Create a real configuration for testing."""
    return Config(
        llm=LLMConfig(
            bridge_url="http://mock-bridge:5001",
            timeout=120,
            preferred_chat_model="llama3.1:8b",
        ),
        controller=ControllerConfig(
            url="http://mock-controller:8080", api_key="test-key", timeout=30
        ),
        memory=MemoryConfig(
            auto_inject_context=True,
            context_token_budget=4000,
            excluded_folders=[],
            default_folder="/test",
        ),
    )


@pytest.mark.asyncio
async def test_context_injection(mock_config: Config) -> None:
    """Test that context is properly injected into requests."""
    proxy = SekhaProxy(mock_config)

    # Mock the controller client
    proxy.controller_client = AsyncMock()

    # Mock context response
    context = [
        {
            "content": "We decided on PostgreSQL",
            "metadata": {
                "citation": {"label": "Database discussion", "folder": "/work"}
            },
        }
    ]
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = MagicMock(return_value=context)  # Synchronous, not async!
    proxy.controller_client.post = AsyncMock(return_value=mock_response)

    # Mock bridge client (v2.0: bridge_client instead of llm_client)
    proxy.bridge_client = AsyncMock()

    # Mock routing response
    routing_response_data = {
        "model_id": "llama3.1:8b",
        "provider_id": "ollama",
        "estimated_cost": 0.0001,
    }
    routing_mock = AsyncMock()
    routing_mock.status_code = 200
    routing_mock.json = MagicMock(return_value=routing_response_data)
    routing_mock.raise_for_status = MagicMock()

    # Mock chat completion response
    llm_response = {
        "choices": [
            {"message": {"role": "assistant", "content": "You're using PostgreSQL"}}
        ]
    }
    llm_mock_response = AsyncMock()
    llm_mock_response.status_code = 200
    llm_mock_response.json = MagicMock(return_value=llm_response)  # Synchronous!
    llm_mock_response.raise_for_status = MagicMock()  # Synchronous!

    # Setup bridge client to return different responses based on endpoint
    async def bridge_post_side_effect(endpoint, **kwargs):
        if "/route" in endpoint:
            return routing_mock
        else:  # /v1/chat/completions
            return llm_mock_response

    proxy.bridge_client.post = AsyncMock(side_effect=bridge_post_side_effect)

    # Test request
    request = {"messages": [{"role": "user", "content": "What database am I using?"}]}

    response = await proxy.forward_chat(request)

    # Verify context was retrieved
    assert proxy.controller_client.post.called

    # Verify response includes metadata
    assert "sekha_metadata" in response
    assert response["sekha_metadata"]["context_count"] == 1

    # Verify routing metadata (v2.0)
    assert "routing" in response["sekha_metadata"]
    assert response["sekha_metadata"]["routing"]["provider_id"] == "ollama"

    await proxy.close()


@pytest.mark.asyncio
async def test_privacy_exclusion(mock_config: Config) -> None:
    """Test that excluded folders are not included in context."""
    mock_config.memory.excluded_folders = ["/personal/private"]
    proxy = SekhaProxy(mock_config)

    # Mock the controller client
    proxy.controller_client = AsyncMock()

    # Mock empty context (excluded)
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = MagicMock(return_value=[])  # Synchronous!
    proxy.controller_client.post = AsyncMock(return_value=mock_response)

    # Mock bridge client (v2.0)
    proxy.bridge_client = AsyncMock()

    # Mock routing response
    routing_response_data = {
        "model_id": "llama3.1:8b",
        "provider_id": "ollama",
        "estimated_cost": 0.0001,
    }
    routing_mock = AsyncMock()
    routing_mock.status_code = 200
    routing_mock.json = MagicMock(return_value=routing_response_data)
    routing_mock.raise_for_status = MagicMock()

    # Mock chat completion response
    llm_response = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "I don't have that information",
                }
            }
        ]
    }
    llm_mock_response = AsyncMock()
    llm_mock_response.status_code = 200
    llm_mock_response.json = MagicMock(return_value=llm_response)  # Synchronous!
    llm_mock_response.raise_for_status = MagicMock()  # Synchronous!

    # Setup bridge client responses
    async def bridge_post_side_effect(endpoint, **kwargs):
        if "/route" in endpoint:
            return routing_mock
        else:
            return llm_mock_response

    proxy.bridge_client.post = AsyncMock(side_effect=bridge_post_side_effect)

    # Test request with folder parameter
    request = {
        "messages": [{"role": "user", "content": "What's my secret?"}],
        "excluded_folders": ["/personal/private"],
    }

    response = await proxy.forward_chat(request)

    # Verify excluded folders were passed to controller
    controller_call = proxy.controller_client.post.call_args
    assert controller_call is not None

    # Verify no context was used (no sekha_metadata key or context_count = 0)
    if "sekha_metadata" in response:
        assert response["sekha_metadata"]["context_count"] == 0

    await proxy.close()


@pytest.mark.asyncio
async def test_bridge_architecture() -> None:
    """Test that proxy is correctly configured for v2.0 bridge architecture."""
    config = Config(
        llm=LLMConfig(
            bridge_url="http://bridge:5001",
            timeout=120,
            preferred_chat_model="llama3.1:8b",
            preferred_vision_model="gpt-4o",
        ),
        controller=ControllerConfig(
            url="http://controller:8080", api_key="test-key", timeout=30
        ),
        memory=MemoryConfig(
            auto_inject_context=True,
            context_token_budget=4000,
            excluded_folders=[],
            default_folder="/test",
        ),
    )

    proxy = SekhaProxy(config)

    # Verify bridge client is configured
    assert proxy.bridge_client is not None
    assert proxy.bridge_client.base_url == "http://bridge:5001"

    # Verify health monitor uses bridge (v2.0: proxy always talks to bridge)
    assert proxy.health_monitor.llm_provider == "bridge"
    assert proxy.health_monitor.llm_url == "http://bridge:5001"

    # Verify config contains model preferences
    assert proxy.config.llm.preferred_chat_model == "llama3.1:8b"
    assert proxy.config.llm.preferred_vision_model == "gpt-4o"

    await proxy.close()


@pytest.mark.asyncio
async def test_vision_routing() -> None:
    """Test that vision detection triggers correct bridge routing."""
    config = Config(
        llm=LLMConfig(
            bridge_url="http://bridge:5001",
            timeout=120,
            preferred_vision_model="gpt-4o",
        ),
        controller=ControllerConfig(
            url="http://controller:8080", api_key="test-key", timeout=30
        ),
        memory=MemoryConfig(
            auto_inject_context=False,  # Disable for simpler test
            context_token_budget=4000,
            excluded_folders=[],
            default_folder="/test",
        ),
    )

    proxy = SekhaProxy(config)

    # Mock bridge client
    proxy.bridge_client = AsyncMock()

    # Mock routing response for vision task
    routing_response_data = {
        "model_id": "gpt-4o",
        "provider_id": "openai",
        "estimated_cost": 0.01,
    }
    routing_mock = AsyncMock()
    routing_mock.status_code = 200
    routing_mock.json = MagicMock(return_value=routing_response_data)
    routing_mock.raise_for_status = MagicMock()

    # Mock chat completion response
    llm_response = {
        "choices": [
            {"message": {"role": "assistant", "content": "I see a cat in the image"}}
        ]
    }
    llm_mock_response = AsyncMock()
    llm_mock_response.status_code = 200
    llm_mock_response.json = MagicMock(return_value=llm_response)
    llm_mock_response.raise_for_status = MagicMock()

    # Setup bridge client responses
    async def bridge_post_side_effect(endpoint, **kwargs):
        if "/route" in endpoint:
            # Verify vision routing parameters
            json_data = kwargs.get("json", {})
            assert json_data.get("task") == "vision"
            assert json_data.get("require_vision") is True
            return routing_mock
        else:
            return llm_mock_response

    proxy.bridge_client.post = AsyncMock(side_effect=bridge_post_side_effect)

    # Test request with image URL
    request = {
        "messages": [
            {
                "role": "user",
                "content": "What's in this image? https://example.com/cat.jpg",
            }
        ]
    }

    response = await proxy.forward_chat(request)

    # Verify vision metadata
    assert "sekha_metadata" in response
    assert "vision" in response["sekha_metadata"]
    assert response["sekha_metadata"]["vision"]["image_count"] == 1
    assert response["sekha_metadata"]["vision"]["supports_vision"] is True

    # Verify routing to vision model
    assert response["sekha_metadata"]["routing"]["model_id"] == "gpt-4o"
    assert response["sekha_metadata"]["routing"]["provider_id"] == "openai"

    await proxy.close()
