---
paths:
  - "ai_score.py"
  - "cover_letter.py"
  - "scraper.py"
---

# rules/api.md

Read this before touching `ai_score.py`, `cover_letter.py`, or `scraper.py`.

---

## Prompt caching — do not remove

Both `ai_score.py` and `cover_letter.py` use prompt caching on the static resume block.
This reduces API cost ~5x on batches of 10+ jobs.

```python
# The cached block must ALWAYS be first in content[], marked with cache_control
messages=[{
    "role": "user",
    "content": [
        {
            "type": "text",
            "text": cached_prefix,          # static: instructions + resume
            "cache_control": {"type": "ephemeral"}
        },
        {
            "type": "text",
            "text": job_block,              # dynamic: per-job data
        },
    ],
}]
```

Rules:
- Static block must come FIRST — Anthropic caches from the start of the message
- Minimum cacheable size: 1024 tokens (Sonnet), 2048 tokens (Haiku)
- Never merge static and dynamic content into one string — caching breaks
- Never move `cache_control` to the dynamic block

---

## Model selection

| Task | Model | Reason |
|---|---|---|
| Job scoring | `claude-haiku-4-5-20251001` | Fast, cheap, returns 1 integer |
| Cover letter | `claude-sonnet-4-6` | Quality matters, used less often |
| Query builder | `claude-sonnet-4-6` | Runs once per scrape, not per job |

Do not swap models without checking cost impact.
Haiku is ~20x cheaper than Sonnet per token.

---

## evaluate() must return int

```python
try:
    return int(response.content[0].text.strip())
except Exception as e:
    print(f"[Score error] {e}")
    return 5   # neutral default — never crash the pipeline
```

If the model returns "7/10" or "Score: 8", `int()` will fail.
Add `.split()[0]` or regex if the model starts misbehaving.

---

## generate_letter() must return str

On any exception: return `"Cover letter generation failed."` — never raise.
The pipeline continues regardless; a missing letter is not a fatal error.

---

## Job sources — fail silently

Every `_fetch_*` function must:
1. Wrap everything in `try/except`
2. Print source name + error on failure
3. Return `[]` — never `None`, never raise

```python
def _fetch_mysource(city: str) -> list[dict]:
    try:
        r = requests.get(URL, timeout=15)
        r.raise_for_status()
        # parse...
        return jobs
    except Exception as e:
        print(f"[MySource] Error: {e}")
        return []
```

---

## Required job dict keys

Every job returned by any `_fetch_*` function must have all 7 keys:

```python
{
    "title": str,
    "company": str,
    "link": str,        # used as dedup key — must be unique and stable
    "tech_stack": str,  # comma-separated, empty string if unknown
    "remote": bool,
    "city": str,
    "description": str, # raw text, max ~1500 chars, empty string if unavailable
}
```

Missing keys will crash `save_job()`. Use `.get("key", "")` defensively when parsing.

---

## Adzuna query builder

`build_queries(resume_text, city)` calls Claude to generate 5 search terms.
Returns `(queries, used_fallback)`.

- `used_fallback = True` means AI failed — hardcoded terms were used
- Caller (`main.py`, `bot.py`) must notify user when `used_fallback = True`
- Never call `build_queries` with an empty resume — pass fallback directly

---

## Adding a new job source

1. Add `_fetch_sourcename(city: str) → list[dict]` to `scraper.py`
2. Call it inside `search_jobs()` with `raw.extend(_fetch_sourcename(city))`
3. Deduplication by `link` happens after all sources — no need to handle it per-source
4. Add source name to `[Scraper]` print log so failures are identifiable
