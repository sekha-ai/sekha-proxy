import pytest
import asyncio
from httpx import AsyncClient

# tests/test_config.py
def test_config_validates_required_fields():
    with pytest.raises(ValueError):
        Config.from_env()  # Missing API key

def test_config_loads_defaults():
    config = Config.from_env()
    assert config.memory.context_token_budget == 4000