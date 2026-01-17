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
