"""Integration tests for proxy functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from proxy import SekhaProxy
from config import Config


@pytest.fixture
def mock_config() -> Config:
    """Create a mock configuration for testing."""
    config = MagicMock(spec=Config)
    config.llm.url = "http://mock-llm:11434"
    config.llm.provider = "ollama"
    config.llm.timeout = 120
    config.controller.url = "http://mock-controller:8080"
    config.controller.api_key = "test-key"
    config.controller.timeout = 30
    config.memory.auto_inject_context = True
    config.memory.context_token_budget = 4000
    config.memory.excluded_folders = []
    config.memory.default_folder = "/test"
    return config


@pytest.mark.asyncio
async def test_context_injection(mock_config: Config) -> None:
    """Test that context is properly injected into requests."""
    proxy = SekhaProxy(mock_config)
    
    # Mock the controller client
    proxy.controller_client = AsyncMock()
    proxy.controller_client.post = AsyncMock()
    
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
    proxy.controller_client.post.return_value = AsyncMock(
        status_code=200,
        json=lambda: context
    )
    
    # Mock LLM client
    proxy.llm_client = AsyncMock()
    llm_response = {
        "choices": [
            {"message": {"role": "assistant", "content": "You're using PostgreSQL"}}
        ]
    }
    proxy.llm_client.post = AsyncMock(return_value=AsyncMock(
        status_code=200,
        json=lambda: llm_response,
        raise_for_status=lambda: None
    ))
    
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
    proxy.controller_client.post = AsyncMock()
    
    # Mock empty context (excluded)
    proxy.controller_client.post.return_value = AsyncMock(
        status_code=200,
        json=lambda: []
    )
    
    # Mock LLM client
    proxy.llm_client = AsyncMock()
    llm_response = {
        "choices": [
            {"message": {"role": "assistant", "content": "I don't have that information"}}
        ]
    }
    proxy.llm_client.post = AsyncMock(return_value=AsyncMock(
        status_code=200,
        json=lambda: llm_response,
        raise_for_status=lambda: None
    ))
    
    # Test request with folder parameter
    request = {
        "messages": [{"role": "user", "content": "What's my secret?"}],
        "excluded_folders": ["/personal/private"]
    }
    
    response = await proxy.forward_chat(request)
    
    # Verify excluded folders were passed to controller
    controller_call = proxy.controller_client.post.call_args
    assert controller_call is not None
    assert "/personal/private" in controller_call[1]["json"]["excluded_folders"]
    
    # Verify no context was used
    if "sekha_metadata" in response:
        assert response["sekha_metadata"]["context_count"] == 0
    
    await proxy.close()
