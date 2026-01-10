import pytest
import asyncio
from httpx import AsyncClient

# tests/test_health.py
@pytest.mark.asyncio
async def test_health_all_services_up():
    monitor = HealthMonitor(...)
    status = await monitor.check_all()
    assert status["status"] == "healthy"

@pytest.mark.asyncio
async def test_health_controller_down():
    # Mock controller as down
    pass

