"""Tests for health monitoring."""

from unittest.mock import AsyncMock

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

    # Mock HTTP clients
    controller_response = AsyncMock()
    controller_response.status_code = 200

    llm_response = AsyncMock()
    llm_response.status_code = 200

    monitor.controller_client.get = AsyncMock(return_value=controller_response)
    monitor.llm_client.get = AsyncMock(return_value=llm_response)

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
    monitor.controller_client.get = AsyncMock(
        side_effect=Exception("Connection refused")
    )

    # Mock LLM success
    llm_response = AsyncMock()
    llm_response.status_code = 200
    monitor.llm_client.get = AsyncMock(return_value=llm_response)

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
    monitor.controller_client.get = AsyncMock(return_value=controller_response)

    # Mock LLM failure
    monitor.llm_client.get = AsyncMock(side_effect=Exception("Connection refused"))

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
    monitor.controller_client.get = AsyncMock(
        side_effect=Exception("Connection refused")
    )
    monitor.llm_client.get = AsyncMock(side_effect=Exception("Connection refused"))

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
    monitor.controller_client.get = AsyncMock(return_value=controller_response)

    # Mock LLM success
    llm_response = AsyncMock()
    llm_response.status_code = 200
    monitor.llm_client.get = AsyncMock(return_value=llm_response)

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
    monitor.controller_client.get = AsyncMock(return_value=controller_response)

    llm_response = AsyncMock()
    llm_response.status_code = 200
    monitor.llm_client.get = AsyncMock(return_value=llm_response)

    status = await monitor.check_all()

    assert "url" in status["checks"]["controller"]
    assert status["checks"]["controller"]["url"] == "http://test-controller:8080"

    await monitor.close()
