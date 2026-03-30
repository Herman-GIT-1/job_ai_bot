# Next Steps

Current state: MVP running locally for a single user.
Pipeline: SerpAPI → scraper.py → database.py (SQLite) → ai_score.py + cover_letter.py (Groq) → bot.py (Telegram).

---

## Priority 0 — Unblock daily use (do first)

### 0.1 Replace SerpAPI with JustJoin.it API

**Why now, not Stage 2:** SerpAPI gives 100 free requests/month — roughly 12–15 `/scrape` runs.
The bot is already nearly unusable for active job search.

JustJoin.it has a public REST API (no key, no quota) returning all Polish IT jobs in one GET request.
This is independent of multi-user migration — it unblocks the core use case immediately.

**Contract to preserve** (`scraper.py`):
```python
def search_jobs(city: str = "Warsaw, Poland") -> list[dict]:
    # must return list of dicts with keys:
    # title, company, link, tech_stack, remote, city, description
```

**Implementation sketch:**
```python
# GET https://justjoin.it/api/offers
# returns a list of offers — filter by city, seniority ("junior"/"intern")
# map fields: offer["title"], offer["companyName"], offer["offerUrls"][0]["url"],
#             offer["skills"] → tech_stack, offer["workplaceType"] == "remote",
#             offer["city"], offer.get("body", "")[:1500] → description
```

`build_queries()` in `scraper.py` can be removed or repurposed as a filter/ranker —
the JustJoin API doesn't need search strings, only city + seniority filters.

Remove `SERPAPI_KEY` from `.env` and `.env.example` after migration.

---

## Priority 1 — Bugs that will break things later

### 1.1 Fix `_db_count()` — it bypasses the database module interface

**File:** `bot.py:83–85`

```python
def _db_count():
    from database import conn          # ← directly accesses internal state
    return conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
```

This breaks as soon as `database.py` switches to PostgreSQL (no global `conn`).
Move this to `database.py` as `count_jobs() -> int` and call it from `bot.py`.

### 1.2 Fix deprecated `asyncio.get_event_loop()` in async context

**File:** `bot.py:38`, `bot.py:64`

```python
loop = asyncio.get_event_loop()   # deprecated in Python 3.10+, warns in 3.12
```

Replace with:
```python
loop = asyncio.get_running_loop()
```

### 1.3 Fix hardcoded `city="Warsaw"` bug in scraper

**File:** `scraper.py:115` — `city` parameter passed to `search_jobs()` is used in
`build_queries()` but ignored when building the job dict: `"city": city` actually
takes the value from the outer scope correctly. Double-check after JustJoin migration (0.1)
since `build_queries` may be removed.

---

## Priority 2 — Performance

### 2.1 Parallel scoring with concurrency limit

**File:** `bot.py:39–43`

Currently jobs are scored sequentially — 50 jobs = 50–100 seconds of waiting.

Replace the `for` loop with bounded `asyncio.gather`:
```python
sem = asyncio.Semaphore(5)  # max 5 concurrent Groq calls

async def score_one(job_id, job):
    async with sem:
        loop = asyncio.get_running_loop()
        s, letter = await loop.run_in_executor(None, lambda: (evaluate(job), generate_letter(job)))
        update_job(job_id, s, letter)

await asyncio.gather(*[score_one(jid, j) for jid, j in jobs_to_score])
```

Expected: ~10× faster for large batches.

### 2.2 Pass resume once per scoring batch, not per job

**Files:** `ai_score.py:11`, `cover_letter.py:11`

Both call `load_resume()` on every single `evaluate()` / `generate_letter()` call.
With 50 jobs that's 100 file reads.

Change signatures:
```python
def evaluate(job: dict, resume: str) -> int
def generate_letter(job: dict, resume: str) -> str
```

Load once in `bot.py:score()` and `main.py:run_score()`, pass as argument.

---

## Priority 3 — Replace temporary AI provider

### 3.1 Replace Groq → Claude API (`claude-haiku-4-5` or `claude-sonnet-4-6`)

**Files:** `ai_score.py`, `cover_letter.py`, `scraper.py`

`llama-3.1-8b-instant` is a free-tier compromise. Quality of scoring and cover letters
will significantly improve with Claude models.

Contracts to preserve:
- `evaluate(job: dict) -> int` — returns integer 0–10
- `generate_letter(job: dict) -> str` — returns plain text
- `build_queries(resume_text: str, city: str) -> tuple[list[str], list[str]]` — only needed
  if keeping query-based scraping after 0.1

**Migration:** swap Groq client for Anthropic client, update model name and API call syntax.
Add `ANTHROPIC_API_KEY` to `.env` and `.env.example`, remove `GROQ_API_KEY`.

---

## Priority 4 — UX improvements

### 4.1 Guard bot access — block unknown users

**File:** `bot.py`

Any user who finds the bot token can use it. Add a check in every handler:
```python
if update.effective_chat.id != CHAT_ID:
    await update.message.reply_text("Access denied.")
    return
```

Or centralize as a decorator / middleware rather than repeating in each handler.

### 4.2 Guided onboarding via `/start`

**File:** `bot.py:93–103`

Currently `/start` dumps a command list. Replace with a guided flow:
```
/start → "Send me your resume (.txt, .pdf, .docx) to get started."
<file>  → "Resume saved. Now use /scrape to find jobs."
/scrape → ...
```

Use `ConversationHandler` (same pattern as `scrape_conv`) or a simple state stored in
`context.user_data`.

### 4.3 Configurable score threshold in `/jobs`

**File:** `bot.py:144`, `database.py:58`

Threshold `>= 7` is hardcoded in SQL in `get_jobs_to_apply()`.

Allow: `/jobs 6` to show jobs with score ≥ 6.
Parse optional arg from `context.args[0]` in the handler, pass to `get_jobs_to_apply(min_score: int = 7)`.

### 4.4 Notify user when scraper fell back to generic queries

**File:** `scraper.py:41`, `bot.py:60–74`

When `build_queries()` catches an exception and returns fallback queries,
the user in Telegram has no idea results may be low quality.

`build_queries()` should return a flag: `(queries, tech_keywords, used_fallback: bool)`.
`bot.py:scrape_run()` should check the flag and send a warning message if True.

### 4.5 `/rescore` command — re-evaluate after resume update

When the resume is updated, old scores are stale. Add a `/rescore` command that:
1. Sets `score = NULL, cover_letter = NULL` for all non-applied jobs (`applied = 0`)
2. Runs the same scoring loop as `/score`

Add `reset_scores()` to `database.py`:
```python
def reset_scores():
    cursor.execute("UPDATE jobs SET score=NULL, cover_letter=NULL WHERE applied=0")
    conn.commit()
```

---

## Priority 5 — Stage 2 (first external users)

### 5.1 PostgreSQL + user_id per row

**File:** `database.py`

Public interface must stay identical — only internals change.
Add `chat_id` to every table. Schema:
```sql
CREATE TABLE users (
    chat_id BIGINT PRIMARY KEY,
    username TEXT,
    resume_text TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

ALTER TABLE jobs ADD COLUMN chat_id BIGINT REFERENCES users(chat_id);
```

All `get_*` and `save_*` functions gain a `chat_id: int` parameter.
`WHERE` clauses must always include `WHERE chat_id = ?`.

### 5.2 Store resume in DB, not in file

**File:** `resume_parser.py`

`resume.txt` is a single-user hack. When moving to PostgreSQL,
redirect `load_resume(chat_id)` and `save_resume(text, chat_id)` to `users.resume_text`.
`resume_parser.py` already has these functions — only the storage backend changes.

### 5.3 Deploy to Railway.app for 24/7 uptime

Switch bot to webhook mode instead of `run_polling()` — more efficient on a server.
Railway.app: free tier, deploy via GitHub push, env vars via UI.
Alternative: Hetzner VPS (~4€/month) + systemd service or Docker.

---

## Technical debt (quick fixes, minutes each)

| Problem | Location | Fix |
|---|---|---|
| `import os` unused | `bot.py:2` | Remove the import |
| Global SQLite connection with `check_same_thread=False` is not safe under concurrent writes | `database.py:6` | Add `threading.Lock` around writes, or use connection-per-call pattern |
| `scraper.py` silently swallows non-JSON Groq responses | `scraper.py:35` | Log the raw response before `json.loads` so fallback reason is visible |
