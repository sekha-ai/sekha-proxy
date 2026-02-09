# Remaining MyPy Fixes for v2.0 Tests

## Progress So Far ✅

### Fixed
1. ✅ `tests/test_config.py` - Updated to use `bridge_url` instead of `url/provider/api_key`
2. ✅ `proxy.py` - Added type hints for `context` and `sekha_metadata`
3. ✅ `tests/test_vision_detection.py` - Fixed async generator return type

### Remaining Issues

The following test files still reference **v1.0 architecture** (direct LLM connection) but need **v2.0 architecture** (bridge connection):

## 1. `tests/test_proxy.py`

### Issues
- Uses `llm_client` instead of `bridge_client`
- Uses `LLMConfig(url=..., provider=...)` instead of `LLMConfig(bridge_url=...)`

### MyPy Errors
```
tests/test_proxy.py:15: error: Unexpected keyword argument "url" for "LLMConfig"  [call-arg]
tests/test_proxy.py:15: error: Unexpected keyword argument "provider" for "LLMConfig"  [call-arg]
tests/test_proxy.py:51: error: "SekhaProxy" has no attribute "llm_client"  [attr-defined]
tests/test_proxy.py:61: error: "SekhaProxy" has no attribute "llm_client"  [attr-defined]
tests/test_proxy.py:94: error: "SekhaProxy" has no attribute "llm_client"  [attr-defined]
tests/test_proxy.py:109: error: "SekhaProxy" has no attribute "llm_client"  [attr-defined]
tests/test_proxy.py:134: error: Unexpected keyword argument "url" for "LLMConfig"  [call-arg]
tests/test_proxy.py:134: error: Unexpected keyword argument "provider" for "LLMConfig"  [call-arg]
tests/test_proxy.py:159: error: Unexpected keyword argument "url" for "LLMConfig"  [call-arg]
tests/test_proxy.py:159: error: Unexpected keyword argument "provider" for "LLMConfig"  [call-arg]
```

### Fix Pattern

**Before (v1.0):**
```python
config = Config(
    llm=LLMConfig(url="http://mock-llm:11434", provider="ollama", timeout=120),
    ...
)

proxy = SekhaProxy(config)
proxy.llm_client = AsyncMock()  # ❌ Wrong
```

**After (v2.0):**
```python
config = Config(
    llm=LLMConfig(bridge_url="http://mock-bridge:5001", timeout=120),
    ...
)

proxy = SekhaProxy(config)
proxy.bridge_client = AsyncMock()  # ✅ Correct
```

---

## 2. `tests/test_proxy_errors.py`

### Issues
- Same as test_proxy.py - uses v1.0 API
- All mocks reference `llm_client` instead of `bridge_client`

### MyPy Errors
```
tests/test_proxy_errors.py:19: error: Unexpected keyword argument "url" for "LLMConfig"  [call-arg]
tests/test_proxy_errors.py:19: error: Unexpected keyword argument "provider" for "LLMConfig"  [call-arg]
tests/test_proxy_errors.py:60: error: "SekhaProxy" has no attribute "llm_client"  [attr-defined]
... (12 more llm_client errors)
```

### Fix Pattern

**Before (v1.0):**
```python
proxy.llm_client.post = AsyncMock(side_effect=HTTPError("Connection failed"))
```

**After (v2.0):**
```python
proxy.bridge_client.post = AsyncMock(side_effect=HTTPError("Connection failed"))
```

---

## 3. Test Type Annotations

### Remaining Issues
```
tests/test_vision_detection.py:36: error: The return type of an async generator function should be "AsyncGenerator"
tests/test_vision_detection.py:227: error: Argument 1 to "_detect_images_in_messages" incompatible type "list[object]"
tests/test_vision_detection.py:262: error: Need type annotation for "messages"
tests/test_vision_detection.py:389: error: Argument 1 to "_detect_images_in_messages" incompatible type "list[object]"
```

### Fix Pattern

**Before:**
```python
@pytest.fixture
async def proxy(proxy_config: Config) -> SekhaProxy:  # ❌ Wrong for async generator
    instance = SekhaProxy(proxy_config)
    yield instance
    await instance.close()
```

**After:**
```python
from typing import AsyncGenerator

@pytest.fixture
async def proxy(proxy_config: Config) -> AsyncGenerator[SekhaProxy, None]:  # ✅ Correct
    instance = SekhaProxy(proxy_config)
    yield instance
    await instance.close()
```

**Add type hints to message lists:**
```python
messages: List[Dict[str, Any]] = [
    {"role": "user", "content": "test"},
]
```

---

## Quick Fix Commands

### Option 1: Manual Fix (Recommended)

1. **Update test_proxy.py:**
   - Replace all `LLMConfig(url=..., provider=...)` with `LLMConfig(bridge_url=...)`
   - Replace all `proxy.llm_client` with `proxy.bridge_client`
   - Remove old provider tests that no longer apply

2. **Update test_proxy_errors.py:**
   - Same changes as test_proxy.py
   - Update all mock setups

3. **Update test_vision_detection.py:**
   - Already mostly done, just need to update fixture return type
   - Add type hints to test message lists

### Option 2: Automated Fix Script

```bash
# In the sekha-proxy directory
cd tests

# Find and replace llm_client -> bridge_client
find . -name "test_*.py" -type f -exec sed -i 's/llm_client/bridge_client/g' {} +

# Find and replace LLMConfig old parameters (manual review recommended)
# This requires careful manual edits
```

---

## Testing After Fixes

```bash
# Run mypy
mypy . --ignore-missing-imports

# Should show: Success: no issues found in X source files

# Run tests
pytest tests/ -v

# Run vision tests specifically
pytest tests/test_vision_detection.py -v
```

---

## Architecture Changes: v1.0 → v2.0

### v1.0 (Old)
```
┌────────┐
│ Proxy  │
└────┬───┘
     │
     ▼
┌────────────┐
│ Ollama/OAI │  (Direct connection)
└────────────┘
```

### v2.0 (New)
```
┌────────┐
│ Proxy  │
└────┬───┘
     │
     ▼
┌────────────┐
│   Bridge   │  (Multi-provider routing)
└────┬───────┘
     │
     ├─► Ollama
     ├─► OpenAI
     ├─► Anthropic
     └─► Google
```

### Key API Changes

| v1.0                              | v2.0                                          |
|-----------------------------------|-----------------------------------------------|
| `LLMConfig.url`                   | `LLMConfig.bridge_url`                        |
| `LLMConfig.provider`              | _(removed, bridge handles routing)_           |
| `LLMConfig.api_key`               | _(removed, bridge manages keys)_              |
| `SekhaProxy.llm_client`           | `SekhaProxy.bridge_client`                    |
| `health_monitor(llm_provider=..)` | `health_monitor(llm_provider="bridge")`       |
| Direct model selection            | `preferred_chat_model` / `preferred_vision_model` (hints) |

---

## Summary

**Total MyPy Errors:** 46  
**Fixed:** ~18 (39%)  
**Remaining:** ~28 (61%)

**Primary Issue:** Test files written for v1.0 architecture need updating to v2.0

**Estimated Time:** 30-45 minutes to manually update remaining test files

**Next Steps:**
1. Update `test_proxy.py` for v2.0
2. Update `test_proxy_errors.py` for v2.0  
3. Add final type hints to `test_vision_detection.py`
4. Run full test suite
5. Verify with mypy

**Status:** In Progress - Core proxy implementation ✅, Tests need updates ⚠️
