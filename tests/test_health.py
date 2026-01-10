"""Tests for health monitoring."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from health import HealthMonitor
from config import Config, ControllerConfig, LLMConfig


@pytest.fixture
def mock_config() -> Config:
    """Create configuration for testing."""
    return Config(
        controller=ControllerConfig(
            url="http://localhost:8080",
            api_key="test-key",
            timeout=30
        ),
        llm=LLMConfig(
            url="http://localhost:11434",
            provider="ollama",
            timeout=120
        )
    )


@pytest.mark.asyncio
async def test_health_all_services_up(mock_config: Config) -> None:
    """Test health check when all services are healthy."""
    monitor = HealthMonitor(mock_config)
    
    # Mock HTTP client
    monitor.client = AsyncMock()
    
    # Mock controller health
    controller_response = AsyncMock()
    controller_response.status_code = 200
    controller_response.json = AsyncMock(return_value={"status": "healthy"})
    
    # Mock LLM health
    llm_response = AsyncMock()
    llm_response.status_code = 200
    llm_response.json = AsyncMock(return_value={"status": "ok"})
    
    async def mock_get(url, **kwargs):
        if "8080" in url:
            return controller_response
        return llm_response
    
    monitor.client.get = mock_get
    
    status = await monitor.check_all()
    
    assert status["status"] == "healthy"
    assert "controller" in status
    assert "llm" in status
    assert status["controller"] == "healthy"
    assert status["llm"] == "healthy"


@pytest.mark.asyncio
async def test_health_controller_down(mock_config: Config) -> None:
    """Test health check when controller is down."""
    monitor = HealthMonitor(mock_config)
    
    # Mock HTTP client
    monitor.client = AsyncMock()
    
    # Mock controller failure
    async def mock_get(url, **kwargs):
        if "8080" in url:
            raise Exception("Connection refused")
        # LLM is up
        llm_response = AsyncMock()
        llm_response.status_code = 200
        llm_response.json = AsyncMock(return_value={"status": "ok"})
        return llm_response
    
    monitor.client.get = mock_get
    
    status = await monitor.check_all()
    
    assert status["status"] == "degraded"
    assert status["controller"] == "unhealthy"
    assert status["llm"] == "healthy"


@pytest.mark.asyncio
async def test_health_llm_down(mock_config: Config) -> None:
    """Test health check when LLM is down."""
    monitor = HealthMonitor(mock_config)
    
    # Mock HTTP client
    monitor.client = AsyncMock()
    
    # Mock LLM failure
    async def mock_get(url, **kwargs):
        if "11434" in url or "ollama" in url:
            raise Exception("Connection refused")
        # Controller is up
        controller_response = AsyncMock()
        controller_response.status_code = 200
        controller_response.json = AsyncMock(return_value={"status": "healthy"})
        return controller_response
    
    monitor.client.get = mock_get
    
    status = await monitor.check_all()
    
    assert status["status"] == "degraded"
    assert status["controller"] == "healthy"
    assert status["llm"] == "unhealthy"


@pytest.mark.asyncio
async def test_health_all_services_down(mock_config: Config) -> None:
    """Test health check when all services are down."""
    monitor = HealthMonitor(mock_config)
    
    # Mock HTTP client
    monitor.client = AsyncMock()
    
    # Mock all failures
    async def mock_get(url, **kwargs):
        raise Exception("Connection refused")
    
    monitor.client.get = mock_get
    
    status = await monitor.check_all()
    
    assert status["status"] == "unhealthy"
    assert status["controller"] == "unhealthy"
    assert status["llm"] == "unhealthy"


@pytest.mark.asyncio
async def test_health_timeout_handling(mock_config: Config) -> None:
    """Test health check timeout handling."""
    monitor = HealthMonitor(mock_config)
    
    # Mock HTTP client with timeout
    monitor.client = AsyncMock()
    
    async def mock_get_timeout(url, **kwargs):
        import asyncio
        await asyncio.sleep(10)  # Longer than timeout
        return AsyncMock()
    
    monitor.client.get = mock_get_timeout
    
    # Should timeout and mark as unhealthy
    status = await monitor.check_all()
    
    # At least one service should timeout
    assert status["status"] in ["degraded", "unhealthy"]


@pytest.mark.asyncio
async def test_health_partial_response(mock_config: Config) -> None:
    """Test health check with partial/invalid responses."""
    monitor = HealthMonitor(mock_config)
    
    # Mock HTTP client
    monitor.client = AsyncMock()
    
    # Mock controller with bad response
    controller_response = AsyncMock()
    controller_response.status_code = 500
    controller_response.json = AsyncMock(return_value={"error": "Internal error"})
    
    # Mock LLM with good response
    llm_response = AsyncMock()
    llm_response.status_code = 200
    llm_response.json = AsyncMock(return_value={"status": "ok"})
    
    async def mock_get(url, **kwargs):
        if "8080" in url:
            return controller_response
        return llm_response
    
    monitor.client.get = mock_get
    
    status = await monitor.check_all()
    
    assert status["status"] == "degraded"
    assert status["controller"] == "unhealthy"
    assert status["llm"] == "healthy"
