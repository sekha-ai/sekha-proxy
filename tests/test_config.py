"""Tests for configuration management."""

import pytest

from config import Config, ControllerConfig, LLMConfig, MemoryConfig


def test_config_default_values() -> None:
    """Test that default configuration values are set correctly."""
    config = Config()

    assert config.proxy.host == "0.0.0.0"
    assert config.proxy.port == 8081
    assert config.llm.provider == "ollama"
    assert config.llm.url == "http://localhost:11434"
    assert config.llm.timeout == 120
    assert config.controller.url == "http://localhost:8080"
    assert config.controller.timeout == 30
    assert config.memory.auto_inject_context is True
    assert config.memory.context_token_budget == 2000
    assert config.memory.context_limit == 5
    assert config.memory.default_folder == "/auto-captured"


def test_config_from_env(monkeypatch) -> None:
    """Test loading configuration from environment variables."""
    # Set environment variables
    monkeypatch.setenv("PROXY_PORT", "9090")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_URL", "https://api.openai.com")
    monkeypatch.setenv("CONTROLLER_URL", "http://controller:8080")
    monkeypatch.setenv("CONTROLLER_API_KEY", "secret-key-123")
    monkeypatch.setenv("CONTEXT_TOKEN_BUDGET", "5000")
    monkeypatch.setenv("EXCLUDED_FOLDERS", "/private,/secret")

    config = Config.from_env()

    assert config.proxy.port == 9090
    assert config.llm.provider == "openai"
    assert config.llm.url == "https://api.openai.com"
    assert config.controller.url == "http://controller:8080"
    assert config.controller.api_key == "secret-key-123"
    assert config.memory.context_token_budget == 5000
    assert config.memory.excluded_folders == ["/private", "/secret"]


def test_config_validate_requires_api_key() -> None:
    """Test that validation requires controller API key."""
    config = Config()
    config.controller.api_key = ""  # Empty key

    with pytest.raises(ValueError, match="CONTROLLER_API_KEY is required"):
        config.validate()


def test_config_validate_llm_provider() -> None:
    """Test that validation checks LLM provider."""
    config = Config()
    config.controller.api_key = "test-key"
    config.llm.provider = "invalid-provider"

    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        config.validate()


def test_config_validate_context_budget() -> None:
    """Test that validation checks context token budget."""
    config = Config()
    config.controller.api_key = "test-key"
    config.memory.context_token_budget = 50  # Too low

    with pytest.raises(ValueError, match="context_token_budget must be at least 100"):
        config.validate()


def test_config_validate_context_limit() -> None:
    """Test that validation checks context limit."""
    config = Config()
    config.controller.api_key = "test-key"
    config.memory.context_limit = 0  # Too low

    with pytest.raises(ValueError, match="context_limit must be at least 1"):
        config.validate()


def test_config_validate_success() -> None:
    """Test that valid configuration passes validation."""
    config = Config()
    config.controller.api_key = "test-key"
    config.llm.provider = "ollama"
    config.memory.context_token_budget = 2000
    config.memory.context_limit = 5

    # Should not raise
    config.validate()


def test_config_custom_values() -> None:
    """Test creating config with custom values."""
    config = Config(
        llm=LLMConfig(
            provider="openai",
            url="https://api.openai.com",
            api_key="sk-test-123",
            timeout=60,
        ),
        controller=ControllerConfig(url="http://custom:8080", api_key="my-key", timeout=15),
        memory=MemoryConfig(
            auto_inject_context=False,
            context_token_budget=10000,
            context_limit=10,
            default_folder="/custom",
            excluded_folders=["/private", "/secret"],
        ),
    )

    assert config.llm.provider == "openai"
    assert config.llm.url == "https://api.openai.com"
    assert config.llm.api_key == "sk-test-123"
    assert config.controller.url == "http://custom:8080"
    assert config.controller.api_key == "my-key"
    assert config.memory.auto_inject_context is False
    assert config.memory.context_token_budget == 10000
    assert config.memory.excluded_folders == ["/private", "/secret"]


def test_config_boolean_parsing(monkeypatch) -> None:
    """Test that boolean environment variables are parsed correctly."""
    monkeypatch.setenv("AUTO_INJECT_CONTEXT", "false")
    monkeypatch.setenv("EXCLUDE_FROM_AI_CONTEXT", "true")
    monkeypatch.setenv("CONTROLLER_API_KEY", "test")

    config = Config.from_env()

    assert config.memory.auto_inject_context is False
    assert config.privacy.exclude_from_ai_context is True


def test_config_list_parsing(monkeypatch) -> None:
    """Test that list environment variables are parsed correctly."""
    monkeypatch.setenv("EXCLUDED_FOLDERS", "/a,/b,/c")
    monkeypatch.setenv("PREFERRED_LABELS", "label1,label2,label3")
    monkeypatch.setenv("CONTROLLER_API_KEY", "test")

    config = Config.from_env()

    assert config.memory.excluded_folders == ["/a", "/b", "/c"]
    assert config.memory.preferred_labels == ["label1", "label2", "label3"]


def test_config_empty_list_parsing(monkeypatch) -> None:
    """Test that empty list environment variables result in empty lists."""
    monkeypatch.setenv("EXCLUDED_FOLDERS", "")
    monkeypatch.setenv("CONTROLLER_API_KEY", "test")

    config = Config.from_env()

    assert config.memory.excluded_folders == []
