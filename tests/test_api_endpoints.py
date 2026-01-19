"""Unit tests for FastAPI endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def mock_proxy_instance():
    """Mock proxy instance for testing endpoints."""
    mock = MagicMock()
    mock.config = MagicMock()
    mock.config.llm.provider = "ollama"
    mock.config.memory.auto_inject_context = True
    mock.config.memory.context_token_budget = 4000
    mock.health_monitor = MagicMock()
    return mock


@pytest.mark.asyncio
async def test_info_endpoint(mock_proxy_instance) -> None:
    """Test /api/info endpoint."""
    with patch("proxy.proxy_instance", mock_proxy_instance):
        from proxy import app

        transport = ASGITransport(app=app)  # type: ignore[arg-type]
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/info")

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Sekha Proxy"
    assert data["version"] == "1.0.0"
    assert "endpoints" in data
    assert "config" in data


@pytest.mark.asyncio
async def test_health_endpoint_healthy(mock_proxy_instance) -> None:
    """Test /health endpoint when healthy."""
    mock_proxy_instance.health_monitor.check_all = AsyncMock(
        return_value={"status": "healthy", "controller": "ok", "llm": "ok"}
    )

    with patch("proxy.proxy_instance", mock_proxy_instance):
        from proxy import app

        transport = ASGITransport(app=app)  # type: ignore[arg-type]
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_health_endpoint_unhealthy(mock_proxy_instance) -> None:
    """Test /health endpoint when unhealthy."""
    mock_proxy_instance.health_monitor.check_all = AsyncMock(
        return_value={"status": "unhealthy", "controller": "error", "llm": "ok"}
    )

    with patch("proxy.proxy_instance", mock_proxy_instance):
        from proxy import app

        transport = ASGITransport(app=app)  # type: ignore[arg-type]
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "unhealthy"


@pytest.mark.asyncio
async def test_health_endpoint_error(mock_proxy_instance) -> None:
    """Test /health endpoint when check fails."""
    mock_proxy_instance.health_monitor.check_all = AsyncMock(
        side_effect=Exception("Health check failed")
    )

    with patch("proxy.proxy_instance", mock_proxy_instance):
        from proxy import app

        transport = ASGITransport(app=app)  # type: ignore[arg-type]
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")

    assert response.status_code == 500
    data = response.json()
    assert data["status"] == "error"


@pytest.mark.asyncio
async def test_chat_completions_success(mock_proxy_instance) -> None:
    """Test successful /v1/chat/completions request."""
    mock_response = {
        "choices": [{"message": {"role": "assistant", "content": "Test response"}}]
    }
    mock_proxy_instance.forward_chat = AsyncMock(return_value=mock_response)

    with patch("proxy.proxy_instance", mock_proxy_instance):
        from proxy import app

        transport = ASGITransport(app=app)  # type: ignore[arg-type]
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/v1/chat/completions",
                json={"messages": [{"role": "user", "content": "Test"}]},
            )

    assert response.status_code == 200
    data = response.json()
    assert "choices" in data
    assert mock_proxy_instance.forward_chat.called


@pytest.mark.asyncio
async def test_chat_completions_proxy_not_initialized() -> None:
    """Test chat completions when proxy not initialized."""
    with patch("proxy.proxy_instance", None):
        from proxy import app

        transport = ASGITransport(app=app)  # type: ignore[arg-type]
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/v1/chat/completions",
                json={"messages": [{"role": "user", "content": "Test"}]},
            )

    assert response.status_code == 503
    assert "not initialized" in response.json()["detail"]


@pytest.mark.asyncio
async def test_chat_completions_invalid_json(mock_proxy_instance) -> None:
    """Test chat completions with invalid JSON.
    
    Note: FastAPI/Starlette returns 500 for JSON decode errors,
    not 422 (which is for validation errors on valid JSON).
    """
    with patch("proxy.proxy_instance", mock_proxy_instance):
        from proxy import app

        transport = ASGITransport(app=app)  # type: ignore[arg-type]
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/v1/chat/completions",
                content="invalid json",
                headers={"Content-Type": "application/json"},
            )

    # FastAPI returns 500 for JSON decode errors (before validation)
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_chat_completions_internal_error(mock_proxy_instance) -> None:
    """Test chat completions with internal error."""
    mock_proxy_instance.forward_chat = AsyncMock(
        side_effect=Exception("Internal error")
    )

    with patch("proxy.proxy_instance", mock_proxy_instance):
        from proxy import app

        transport = ASGITransport(app=app)  # type: ignore[arg-type]
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/v1/chat/completions",
                json={"messages": [{"role": "user", "content": "Test"}]},
            )

    assert response.status_code == 500


@pytest.mark.asyncio
async def test_root_redirect() -> None:
    """Test root endpoint redirects to UI."""
    from proxy import app

    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=False) as client:
        response = await client.get("/")

    assert response.status_code in [307, 302]  # Redirect
    assert "/static/index.html" in response.headers.get("location", "")


@pytest.mark.asyncio
async def test_chat_with_all_parameters(mock_proxy_instance) -> None:
    """Test chat completions with all optional parameters."""
    mock_response = {
        "choices": [{"message": {"role": "assistant", "content": "Response"}}],
        "sekha_metadata": {"context_count": 2},
    }
    mock_proxy_instance.forward_chat = AsyncMock(return_value=mock_response)

    with patch("proxy.proxy_instance", mock_proxy_instance):
        from proxy import app

        transport = ASGITransport(app=app)  # type: ignore[arg-type]
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/v1/chat/completions",
                json={
                    "messages": [{"role": "user", "content": "Test"}],
                    "model": "llama3.1:8b",
                    "folder": "/work/project",
                    "excluded_folders": ["/private"],
                    "context_budget": 8000,
                    "stream": False,
                },
            )

    assert response.status_code == 200
    data = response.json()
    assert "sekha_metadata" in data
    assert data["sekha_metadata"]["context_count"] == 2
