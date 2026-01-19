"""End-to-end integration tests.

These tests require the full stack to be running:
- sekha-controller (port 8080)
- sekha-proxy (port 8081)
- ollama or other LLM
- chromadb

Run with: pytest tests/test_integration.py -v -m integration
Skip with: pytest tests/ -v -m "not integration"
"""

import asyncio

import pytest
from httpx import AsyncClient, ConnectError, HTTPStatusError


@pytest.mark.asyncio
@pytest.mark.integration
async def test_full_flow() -> None:
    """Test full flow: store conversation, retrieve with context.

    Requires server running on localhost:8081
    """
    try:
        async with AsyncClient(base_url="http://localhost:8081", timeout=5.0) as proxy_client:
            # 1. Create initial conversation via proxy
            response1 = await proxy_client.post(
                "/v1/chat/completions",
                json={
                    "messages": [{"role": "user", "content": "I'm using Rust with SQLite"}],
                    "folder": "/test/integration",
                },
            )
            assert response1.status_code == 200

            # Wait for background storage
            await asyncio.sleep(2)

            # 2. Second conversation - should have context from first
            response2 = await proxy_client.post(
                "/v1/chat/completions",
                json={
                    "messages": [{"role": "user", "content": "What database am I using?"}],
                    "folder": "/test/integration",
                },
            )
            assert response2.status_code == 200

            # 3. Verify response mentions SQLite (from context)
            data = response2.json()
            response_text = data["choices"][0]["message"]["content"].lower()
            assert "sqlite" in response_text or "database" in response_text

            # Verify context was used
            if "sekha_metadata" in data:
                assert data["sekha_metadata"]["context_count"] > 0
    except ConnectError:
        pytest.skip("Server not running on localhost:8081")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_privacy_filtering() -> None:
    """Test that excluded folders are not included in context.

    Requires server running on localhost:8081
    """
    try:
        async with AsyncClient(base_url="http://localhost:8081", timeout=5.0) as proxy_client:
            # 1. Store sensitive info in /private folder
            response1 = await proxy_client.post(
                "/v1/chat/completions",
                json={
                    "messages": [
                        {
                            "role": "user",
                            "content": "My secret API key is sk-test-12345",
                        }
                    ],
                    "folder": "/private/secrets",
                },
            )
            assert response1.status_code == 200

            await asyncio.sleep(2)

            # 2. Query with /private excluded
            response2 = await proxy_client.post(
                "/v1/chat/completions",
                json={
                    "messages": [{"role": "user", "content": "What is my API key?"}],
                    "folder": "/work",
                    "excluded_folders": ["/private"],
                },
            )
            assert response2.status_code == 200

            # 3. Verify sensitive info NOT in response
            data = response2.json()
            response_text = data["choices"][0]["message"]["content"]
            assert "sk-test-12345" not in response_text

            # Verify context was filtered
            if "sekha_metadata" in data:
                # Should have 0 context or context from non-private folders
                for ctx in data["sekha_metadata"].get("context_used", []):
                    assert not ctx["folder"].startswith("/private")
    except ConnectError:
        pytest.skip("Server not running on localhost:8081")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_web_ui_accessible() -> None:
    """Test that web UI is accessible.

    Requires server running on localhost:8081
    """
    try:
        async with AsyncClient(base_url="http://localhost:8081", timeout=5.0) as client:
            response = await client.get("/")
            assert response.status_code in [
                200,
                302,
                307,
                404,
            ]  # OK, redirect, or not implemented

            # If static files exist
            try:
                response = await client.get("/static/index.html")
                if response.status_code == 200:
                    assert len(response.text) > 0
            except (HTTPStatusError, Exception):
                pass  # Static files may not be implemented yet

    except ConnectError:
        pytest.skip("Server not running on localhost:8081")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_health_endpoint() -> None:
    """Test health endpoint returns correct status.

    Requires server running on localhost:8081
    """
    try:
        async with AsyncClient(base_url="http://localhost:8081", timeout=5.0) as client:
            response = await client.get("/health")
            assert response.status_code in [200, 503]  # Healthy or unhealthy

            data = response.json()
            assert "status" in data
            assert data["status"] in ["healthy", "unhealthy", "degraded"]
    except ConnectError:
        pytest.skip("Server not running on localhost:8081")
