# tests/test_proxy.py
async def test_context_injection():
    proxy = SekhaProxy(config)
    context = [
        {"content": "We decided on PostgreSQL", "metadata": {...}},
        {"content": "Using SQLAlchemy ORM", "metadata": {...}}
    ]
    
    messages = [{"role": "user", "content": "What database?"}]
    enhanced = proxy._inject_context(messages, context)
    
    assert len(enhanced) == 2  # System message + user message
    assert "PostgreSQL" in enhanced[0]["content"]
    assert "SQLAlchemy" in enhanced[0]["content"]

async def test_privacy_exclusion():
    proxy = SekhaProxy(config)
    proxy.config.excluded_folders = ["/personal/private"]
    
    context = await proxy._get_context_from_controller(
        query="test",
        preferred_labels=[],
        context_budget=2000
    )
    
    # Verify no messages from /personal/private in context
    for msg in context:
        assert not msg["folder"].startswith("/personal/private")
