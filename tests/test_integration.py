async def test_full_flow():
    # Start all services (controller, proxy, ollama)
    
    # 1. Create initial conversation via proxy
    response1 = await proxy_client.post("/v1/chat/completions", json={
        "messages": [{"role": "user", "content": "I'm using Rust with SQLite"}]
    })
    
    # Wait for background storage
    await asyncio.sleep(1)
    
    # 2. Second conversation - should have context from first
    response2 = await proxy_client.post("/v1/chat/completions", json={
        "messages": [{"role": "user", "content": "What database am I using?"}]
    })
    
    # 3. Verify response mentions SQLite (from context)
    assert "SQLite" in response2["choices"][0]["message"]["content"]
    assert response2["sekha_metadata"]["context_count"] > 0
