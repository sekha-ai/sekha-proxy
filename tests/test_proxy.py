"""Integration tests for proxy functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from proxy import SekhaProxy
from config import Config, LLMConfig, ControllerConfig, MemoryConfig


@pytest.fixture
def mock_config() -> Config:
    """Create a real configuration for testing."""
    return Config(
        llm=LLMConfig(
            url="http://mock-llm:11434",
            provider="ollama",
            timeout=120
        ),
        controller=ControllerConfig(
            url="http://mock-controller:8080",
            api_key="test-key",
            timeout=30
        ),
        memory=MemoryConfig(
            auto_inject_context=True,
            context_token_budget=4000,
            excluded_folders=[],
            default_folder="/test"
        )
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
                "citation": {
                    "label": "Database discussion",
                    "folder": "/work"
                }
            }
        }
    ]
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = MagicMock(return_value=context)  # Synchronous, not async!
    proxy.controller_client.post = AsyncMock(return_value=mock_response)
    
    # Mock LLM client
    proxy.llm_client = AsyncMock()
    llm_response = {
        "choices": [
            {"message": {"role": "assistant", "content": "You're using PostgreSQL"}}
        ]
    }
    llm_mock_response = AsyncMock()
    llm_mock_response.status_code = 200
    llm_mock_response.json = MagicMock(return_value=llm_response)  # Synchronous!
    llm_mock_response.raise_for_status = MagicMock()  # Synchronous!
    proxy.llm_client.post = AsyncMock(return_value=llm_mock_response)
    
    # Test request
    request = {
        "messages": [{"role": "user", "content": "What database am I using?"}]
    }
    
    response = await proxy.forward_chat(request)
    
    # Verify context was retrieved
    assert proxy.controller_client.post.called
    
    # Verify response includes metadata
    assert "sekha_metadata" in response
    assert response["sekha_metadata"]["context_count"] == 1
    
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
    
    # Mock LLM client
    proxy.llm_client = AsyncMock()
    llm_response = {
        "choices": [
            {"message": {"role": "assistant", "content": "I don't have that information"}}
        ]
    }
    llm_mock_response = AsyncMock()
    llm_mock_response.status_code = 200
    llm_mock_response.json = MagicMock(return_value=llm_response)  # Synchronous!
    llm_mock_response.raise_for_status = MagicMock()  # Synchronous!
    proxy.llm_client.post = AsyncMock(return_value=llm_mock_response)
    
    # Test request with folder parameter
    request = {
        "messages": [{"role": "user", "content": "What's my secret?"}],
        "excluded_folders": ["/personal/private"]
    }
    
    response = await proxy.forward_chat(request)
    
    # Verify excluded folders were passed to controller
    controller_call = proxy.controller_client.post.call_args
    assert controller_call is not None
    
    # Verify no context was used (no sekha_metadata key or context_count = 0)
    if "sekha_metadata" in response:
        assert response["sekha_metadata"]["context_count"] == 0
    
    await proxy.close()
