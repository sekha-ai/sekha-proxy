"""Tests for health monitoring."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from health import HealthMonitor


@pytest.mark.asyncio
async def test_health_all_services_up() -> None:
    """Test health check when all services are healthy."""
    monitor = HealthMonitor(
        controller_url="http://localhost:8080",
        llm_url="http://localhost:11434",
        controller_api_key="test-key",
    )

    # Mock HTTP clients properly
    controller_response = AsyncMock()
    controller_response.status_code = 200

    llm_response = AsyncMock()
    llm_response.status_code = 200

    mock_controller_client = MagicMock()
    mock_controller_client.get = AsyncMock(return_value=controller_response)
    mock_controller_client.aclose = AsyncMock()  # Add aclose for cleanup
    monitor.controller_client = mock_controller_client  # type: ignore[assignment]

    mock_llm_client = MagicMock()
    mock_llm_client.get = AsyncMock(return_value=llm_response)
    mock_llm_client.aclose = AsyncMock()  # Add aclose for cleanup
    monitor.llm_client = mock_llm_client  # type: ignore[assignment]

    status = await monitor.check_all()

    assert status["status"] == "healthy"
    assert "checks" in status
    assert status["checks"]["controller"]["status"] == "ok"
    assert status["checks"]["llm"]["status"] in ["ok", "warning"]  # LLM might warn

    await monitor.close()


@pytest.mark.asyncio
async def test_health_controller_down() -> None:
    """Test health check when controller is down."""
    monitor = HealthMonitor(
        controller_url="http://localhost:8080",
        llm_url="http://localhost:11434",
        controller_api_key="test-key",
    )

    # Mock controller failure
    mock_controller_client = MagicMock()
    mock_controller_client.get = AsyncMock(
        side_effect=Exception("Connection refused")
    )
    mock_controller_client.aclose = AsyncMock()
    monitor.controller_client = mock_controller_client  # type: ignore[assignment]

    # Mock LLM success
    llm_response = AsyncMock()
    llm_response.status_code = 200
    mock_llm_client = MagicMock()
    mock_llm_client.get = AsyncMock(return_value=llm_response)
    mock_llm_client.aclose = AsyncMock()
    monitor.llm_client = mock_llm_client  # type: ignore[assignment]

    status = await monitor.check_all()

    assert status["status"] in ["degraded", "unhealthy"]
    assert status["checks"]["controller"]["status"] == "error"

    await monitor.close()


@pytest.mark.asyncio
async def test_health_llm_down() -> None:
    """Test health check when LLM is down."""
    monitor = HealthMonitor(
        controller_url="http://localhost:8080",
        llm_url="http://localhost:11434",
        controller_api_key="test-key",
    )

    # Mock controller success
    controller_response = AsyncMock()
    controller_response.status_code = 200
    mock_controller_client = MagicMock()
    mock_controller_client.get = AsyncMock(return_value=controller_response)
    mock_controller_client.aclose = AsyncMock()
    monitor.controller_client = mock_controller_client  # type: ignore[assignment]

    # Mock LLM failure
    mock_llm_client = MagicMock()
    mock_llm_client.get = AsyncMock(side_effect=Exception("Connection refused"))
    mock_llm_client.aclose = AsyncMock()
    monitor.llm_client = mock_llm_client  # type: ignore[assignment]

    status = await monitor.check_all()

    assert status["status"] in ["degraded", "unhealthy"]
    assert status["checks"]["llm"]["status"] == "error"

    await monitor.close()


@pytest.mark.asyncio
async def test_health_all_services_down() -> None:
    """Test health check when all services are down."""
    monitor = HealthMonitor(
        controller_url="http://localhost:8080",
        llm_url="http://localhost:11434",
        controller_api_key="test-key",
    )

    # Mock all failures
    mock_controller_client = MagicMock()
    mock_controller_client.get = AsyncMock(
        side_effect=Exception("Connection refused")
    )
    mock_controller_client.aclose = AsyncMock()
    monitor.controller_client = mock_controller_client  # type: ignore[assignment]

    mock_llm_client = MagicMock()
    mock_llm_client.get = AsyncMock(side_effect=Exception("Connection refused"))
    mock_llm_client.aclose = AsyncMock()
    monitor.llm_client = mock_llm_client  # type: ignore[assignment]

    status = await monitor.check_all()

    assert status["status"] == "unhealthy"
    assert status["checks"]["controller"]["status"] == "error"
    assert status["checks"]["llm"]["status"] == "error"

    await monitor.close()


@pytest.mark.asyncio
async def test_health_partial_response() -> None:
    """Test health check with partial/invalid responses."""
    monitor = HealthMonitor(
        controller_url="http://localhost:8080",
        llm_url="http://localhost:11434",
        controller_api_key="test-key",
    )

    # Mock controller with 500 error
    controller_response = AsyncMock()
    controller_response.status_code = 500
    mock_controller_client = MagicMock()
    mock_controller_client.get = AsyncMock(return_value=controller_response)
    mock_controller_client.aclose = AsyncMock()
    monitor.controller_client = mock_controller_client  # type: ignore[assignment]

    # Mock LLM success
    llm_response = AsyncMock()
    llm_response.status_code = 200
    mock_llm_client = MagicMock()
    mock_llm_client.get = AsyncMock(return_value=llm_response)
    mock_llm_client.aclose = AsyncMock()
    monitor.llm_client = mock_llm_client  # type: ignore[assignment]

    status = await monitor.check_all()

    assert status["status"] in ["degraded", "unhealthy"]
    assert status["checks"]["controller"]["status"] == "error"

    await monitor.close()


@pytest.mark.asyncio
async def test_health_returns_urls() -> None:
    """Test that health check returns service URLs."""
    monitor = HealthMonitor(
        controller_url="http://test-controller:8080",
        llm_url="http://test-llm:11434",
        controller_api_key="test-key",
    )

    # Mock responses
    controller_response = AsyncMock()
    controller_response.status_code = 200
    mock_controller_client = MagicMock()
    mock_controller_client.get = AsyncMock(return_value=controller_response)
    mock_controller_client.aclose = AsyncMock()
    monitor.controller_client = mock_controller_client  # type: ignore[assignment]

    llm_response = AsyncMock()
    llm_response.status_code = 200
    mock_llm_client = MagicMock()
    mock_llm_client.get = AsyncMock(return_value=llm_response)
    mock_llm_client.aclose = AsyncMock()
    monitor.llm_client = mock_llm_client  # type: ignore[assignment]

    status = await monitor.check_all()

    assert "url" in status["checks"]["controller"]
    assert status["checks"]["controller"]["url"] == "http://test-controller:8080"

    await monitor.close()
