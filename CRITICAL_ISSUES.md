# Critical Issues

Issues that need to be addressed for correct system operation.

---

## 1. STT Response Cache is Global, Not Per-Topic

**Priority:** High
**Status:** Open
**Created:** 2026-01-17

### Problem

The STT response cache (`orac/cache/stt_response_cache.py`) stores command mappings globally without tracking which topic they belong to. This is incorrect because:

- Each topic can have a different backend (e.g., Home Assistant, custom API)
- The JSON output format is backend-specific
- A cached response for topic A would be incorrect if used for topic B

### Current Behavior

Cache stores:
- `stt_text` (normalized phrase)
- `json_output` (LLM response)
- `entity_id`
- `success_count`, timestamps

**Missing:** `topic_id`

### Example of the Bug

1. User says "turn on the light" to **topic A** (Home Assistant backend)
2. Cache stores: `"turn on the light"` → `{"service": "light.turn_on", "entity_id": "light.lounge"}`
3. User says "turn on the light" to **topic B** (different backend expecting different JSON format)
4. Cache HIT returns Home Assistant JSON to the wrong backend → **Command fails or behaves incorrectly**

### Required Fix

1. Add `topic_id` field to cache entry structure
2. Update `store()` method to include topic_id
3. Update `get()` method to filter by topic_id
4. Update API endpoints to accept/filter by topic
5. Update cache GUI to show/filter by topic
6. Migrate existing cache entries (or clear cache on upgrade)

### Files to Modify

- `orac/cache/stt_response_cache.py` - Add topic_id to entry structure and methods
- `orac/services/generation_service.py` - Pass topic_id to cache methods
- `orac/api/routes/cache.py` - Add topic filtering to endpoints
- `orac/templates/cache.html` - Add topic filter to GUI

### Workaround

Currently only one topic (computa/general) actively uses the cache, so the bug doesn't manifest. Multi-topic deployments should clear the cache when switching between topics.

---

## 2. Cache Stores Commands Without Verifying State Change

**Priority:** High
**Status:** Open
**Created:** 2026-01-17

### Problem

The STT response cache stores command mappings based solely on Home Assistant returning HTTP 200 success. This is incorrect because:

- HA returns 200 even if the device is already in the requested state (no-op)
- User says "turn on the lounge lights" but it gets transcribed as "turn on the lounge cabinet"
- Cabinet is already ON, so HA returns success (no visible change)
- User doesn't notice the error (cabinet was already on)
- Incorrect mapping gets cached
- Cache fills with wrong STT→JSON mappings

### Current Behavior

```
User: "turn on the lounge lights"
  → Whisper transcribes as "turn on the lounge cabinet" (error)
  → LLM generates: {"device": "cabinet", "action": "on", "location": "lounge"}
  → HA executes switch.museum turn_on
  → Cabinet was already ON → HA returns 200 (success, but no change)
  → Cache STORE: "turn on the lounge cabinet" → cabinet
  → User doesn't notice (cabinet was already on)

Next time: Cache HIT returns wrong device forever
```

### Required Fix

Only cache if there was an **actual state change**:

1. Before executing command: Get current state of target entity
2. Execute command via HA API
3. After executing: Get new state of target entity
4. Only cache if `old_state != new_state`

This gives the user a window to notice the error and use "computer error" to remove it.

### Implementation Options

**Option A: Pre/Post State Check (Recommended)**
```python
# Before command
old_state = await ha_client.get_state(entity_id)

# Execute command
result = await ha_client.call_service(...)

# After command
new_state = await ha_client.get_state(entity_id)

# Only cache if state changed
if old_state != new_state:
    cache.store(stt_text, json_output, entity_id)
```

**Option B: Delayed Caching**
- Don't cache immediately
- Wait N seconds for user to say "error"
- If no error within window, then cache
- Downside: Adds complexity, delay before cache benefit

### Files to Modify

- `orac/services/generation_service.py` - Add state change verification before caching
- `orac/dispatchers/homeassistant.py` - Add get_state method or return state info
- `orac/homeassistant/client.py` - May need state query method

### Notes

- HA API for state: `GET /api/states/{entity_id}`
- State object has `state` field (e.g., "on", "off", "unavailable")
- Need to handle entities that don't have simple on/off states

---
