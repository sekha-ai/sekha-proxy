"""Tests for context injection functionality."""

import pytest

from context_injection import ContextInjector


@pytest.fixture
def injector():
    """Create a ContextInjector instance."""
    return ContextInjector()


@pytest.fixture
def sample_context():
    """Sample context messages with citations."""
    return [
        {
            "role": "user",
            "content": "We decided to use PostgreSQL for the database.",
            "metadata": {
                "citation": {
                    "label": "Database Discussion",
                    "folder": "/work/project-alpha",
                    "timestamp": "2026-01-09T10:30:00",
                }
            },
        },
        {
            "role": "assistant",
            "content": "Great choice. PostgreSQL offers strong ACID compliance and excellent JSON support.",
            "metadata": {
                "citation": {
                    "label": "Database Discussion",
                    "folder": "/work/project-alpha",
                    "timestamp": "2026-01-09T10:31:00",
                }
            },
        },
    ]


@pytest.fixture
def user_messages():
    """Sample user messages."""
    return [{"role": "user", "content": "What database should I use?"}]


def test_extract_last_user_message(injector):
    """Test extraction of last user message."""
    messages = [
        {"role": "system", "content": "You are helpful"},
        {"role": "user", "content": "First question"},
        {"role": "assistant", "content": "First answer"},
        {"role": "user", "content": "Second question"},
    ]

    result = injector.extract_last_user_message(messages)
    assert result == "Second question"


def test_extract_last_user_message_empty(injector):
    """Test extraction with no user messages."""
    messages = [
        {"role": "system", "content": "You are helpful"},
        {"role": "assistant", "content": "Hello"},
    ]

    result = injector.extract_last_user_message(messages)
    assert result == ""


def test_inject_context_basic(injector, user_messages, sample_context):
    """Test basic context injection."""
    result = injector.inject_context(user_messages, sample_context)

    # Should have system message + user message
    assert len(result) == 2
    assert result[0]["role"] == "system"
    assert result[1]["role"] == "user"

    # System message should contain context
    system_content = result[0]["content"]
    assert "PostgreSQL" in system_content
    assert "Database Discussion" in system_content
    assert "/work/project-alpha" in system_content


def test_inject_context_with_existing_system(injector, sample_context):
    """Test context injection preserves existing system message."""
    messages = [
        {"role": "system", "content": "You are an expert developer."},
        {"role": "user", "content": "What database?"},
    ]

    result = injector.inject_context(messages, sample_context)

    # Should have original system + context system + user
    assert len(result) == 3
    assert result[0]["role"] == "system"
    assert result[0]["content"] == "You are an expert developer."
    assert result[1]["role"] == "system"
    assert "PostgreSQL" in result[1]["content"]
    assert result[2]["role"] == "user"


def test_inject_context_empty_context(injector, user_messages):
    """Test injection with no context."""
    result = injector.inject_context(user_messages, [])

    # Should return original messages unchanged
    assert result == user_messages


def test_format_context_for_llm(injector, sample_context):
    """Test context formatting for LLM."""
    result = injector.format_context_for_llm(sample_context)

    # Should contain all key elements
    assert "Database Discussion" in result
    assert "/work/project-alpha" in result
    assert "2026-01-09" in result
    assert "PostgreSQL" in result
    assert "[Past Conversation 1]" in result


def test_format_context_multiple_conversations(injector):
    """Test formatting with multiple different conversations."""
    context = [
        {
            "content": "First conversation content",
            "metadata": {
                "citation": {
                    "label": "Topic A",
                    "folder": "/folder1",
                    "timestamp": "2026-01-09T10:00:00",
                }
            },
        },
        {
            "content": "Second conversation content",
            "metadata": {
                "citation": {
                    "label": "Topic B",
                    "folder": "/folder2",
                    "timestamp": "2026-01-09T11:00:00",
                }
            },
        },
    ]

    result = injector.format_context_for_llm(context)

    assert "[Past Conversation 1]" in result
    assert "[Past Conversation 2]" in result
    assert "Topic A" in result
    assert "Topic B" in result


def test_generate_label_from_first_message(injector):
    """Test label generation from first user message."""
    messages = [
        {"role": "user", "content": "How do I implement pagination in Rust?"},
        {"role": "assistant", "content": "Here's how..."},
    ]

    label = injector.generate_label(messages)
    assert label == "How do I implement pagination in Rust?"


def test_generate_label_truncates_long_content(injector):
    """Test label truncation for long messages."""
    long_content = "a" * 100
    messages = [
        {"role": "user", "content": long_content},
    ]

    label = injector.generate_label(messages)
    assert len(label) <= 53  # 50 chars + "..."
    assert label.endswith("...")


def test_generate_label_no_user_messages(injector):
    """Test label generation with no user messages."""
    messages = [{"role": "assistant", "content": "Hello"}]

    label = injector.generate_label(messages)
    assert label == "Untitled Conversation"


def test_generate_label_skips_system_messages(injector):
    """Test that label generation skips system messages."""
    messages = [
        {"role": "system", "content": "You are helpful"},
        {"role": "user", "content": "My actual question"},
    ]

    label = injector.generate_label(messages)
    assert label == "My actual question"


def test_build_metadata(injector):
    """Test metadata building."""
    context_used = [
        {"metadata": {"citation": {"label": "Conv 1"}}},
        {"metadata": {"citation": {"label": "Conv 2"}}},
    ]

    metadata = injector.build_metadata(context_used=context_used, llm_provider="ollama")

    assert metadata["auto_captured"] is True
    assert metadata["context_used_count"] == 2
    assert metadata["llm_provider"] == "ollama"


def test_build_metadata_no_context(injector):
    """Test metadata with no context."""
    metadata = injector.build_metadata(context_used=[], llm_provider="openai")

    assert metadata["auto_captured"] is True
    assert metadata["context_used_count"] == 0
    assert metadata["llm_provider"] == "openai"


def test_inject_context_preserves_message_order(injector, user_messages, sample_context):
    """Test that message order is preserved correctly."""
    result = injector.inject_context(user_messages, sample_context)

    # Last message should still be the user query
    assert result[-1]["role"] == "user"
    assert result[-1]["content"] == "What database should I use?"


def test_format_context_handles_missing_citation(injector):
    """Test formatting when citation metadata is missing."""
    context = [{"content": "Some content", "metadata": {}}]  # No citation

    result = injector.format_context_for_llm(context)

    # Should handle gracefully
    assert "Some content" in result
    assert "Unknown" in result  # Default values


def test_format_context_handles_partial_citation(injector):
    """Test formatting with partial citation data."""
    context = [
        {
            "content": "Some content",
            "metadata": {
                "citation": {
                    "label": "Test",
                    # Missing folder and timestamp
                }
            },
        }
    ]

    result = injector.format_context_for_llm(context)

    assert "Test" in result
    assert "Some content" in result
