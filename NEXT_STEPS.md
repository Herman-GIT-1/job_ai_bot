# Next Steps

Current state: MVP running locally for a single user.
Pipeline: Adzuna + JustJoin.it + Remotive + NoFluffJobs → scraper.py → database.py (SQLite) → ai_score.py + cover_letter.py (Groq) → bot.py (Telegram).

Branch `feat/chat-id` — in progress, not yet merged to main.

---

## Priority 1 — Replace temporary AI provider

### 1.1 Replace Groq → Claude API (`claude-haiku-4-5` or `claude-sonnet-4-6`)

**Files:** `ai_score.py`, `cover_letter.py`

`llama-3.1-8b-instant` is a free-tier compromise. Quality of scoring and cover letters
will significantly improve with Claude models.

Contracts to preserve:
- `evaluate(job: dict, resume: str) -> int` — returns integer 0–10
- `generate_letter(job: dict, resume: str) -> str` — returns plain text

**Migration:** swap Groq client for Anthropic client, update model name and API call syntax.
Add `ANTHROPIC_API_KEY` to `.env` and `.env.example`, remove `GROQ_API_KEY`.

---

## Priority 2 — Stage 2 (first external users)

### 2.1 Finish and merge `feat/chat-id` → main

**Branch:** `feat/chat-id` (already started)

Remaining before merge:
- Update `open_jobs.py` to pass `chat_id` to all DB calls (currently broken in the branch)
- Delete `jobs.db` to start fresh with the new schema (existing data has `chat_id = NULL`)
- Manual smoke test: `/scrape` → `/score` → `/jobs` end-to-end with the new schema

### 2.2 Store resume in DB, not in file

**Files:** `database.py`, `resume_parser.py`, `bot.py`

`resume.txt` is a single-user hack. Move it into `user_settings` table:
```sql
ALTER TABLE user_settings ADD COLUMN resume_text TEXT;
```
Redirect `load_resume()` and `save_resume()` to read/write `user_settings.resume_text`
by `chat_id`. This is the last file-system dependency per user.

### 2.3 Replace global `conn` + `cursor` with connection pool

**File:** `database.py`

The current module-level singleton breaks under concurrent users.
Replace with `threading.local()` or `queue.Queue`-based pool.
Required before deploying to any multi-user environment.

### 2.4 PostgreSQL migration

**File:** `database.py`

After 2.1–2.3 are done, only the engine needs to change.
Exact diffs needed:
- `sqlite3` → `psycopg2` (or `psycopg[binary]`)
- `?` placeholders → `%s`
- `INSERT OR IGNORE` → `INSERT ... ON CONFLICT DO NOTHING`
- `INTEGER PRIMARY KEY` → `BIGSERIAL PRIMARY KEY`
- Remove `check_same_thread=False` — psycopg2 is thread-safe
- Provide `DATABASE_URL` env var (Railway injects it automatically)

### 2.5 Deploy to Railway.app for 24/7 uptime

Minimum path:
- Push to GitHub
- Connect repo to Railway.app (free tier) + add PostgreSQL plugin
- Set env vars in Railway dashboard
- Add `Procfile`: `worker: python main.py --bot`

---

## Priority 3 — UX improvements

### 3.1 Notify on new high-score jobs

After `/scrape` + `/score`, automatically send a message if any new jobs scored ≥ 8 —
without the user having to run `/jobs` manually.

### 3.2 Export to CSV

`/export` — send all jobs (or only applied) as a CSV file.
Useful for tracking application status outside the bot.

---

## Done ✓

- ~~0.1 Replace SerpAPI with JustJoin.it~~ — single GET, no key, no quota
- ~~0.2 Migrate scraper from JustJoin.it to Adzuna API~~ — JustJoin closed public API
- ~~0.3 Add multiple job sources~~ — Adzuna + JustJoin.it (fallback) + Remotive + NoFluffJobs
- ~~1.1 Fix `_db_count()` — moved to `database.py` as `count_jobs()`~~
- ~~1.2 Fix deprecated `get_event_loop()` → `get_running_loop()`~~
- ~~2.1 Parallel scoring with `asyncio.Semaphore(5)`~~
- ~~2.2 Cache resume once per scoring run~~
- ~~3.1 Replace hardcoded skills in `ai_score.py` / `cover_letter.py` prompts~~
- ~~4.1 Block unknown users — `owner_only` decorator~~
- ~~4.2 Guided onboarding in `/start`~~
- ~~4.3 Configurable score threshold: `/jobs 6`~~
- ~~4.4 Notify user when scraper used fallback queries~~
- ~~4.5 `/rescore` command~~
- ~~Pass job description into AI prompts~~
- ~~Fix city hardcoded as "Warsaw" in scraper~~
- ~~Add multilingual support (EN/RU/PL)~~
- ~~Add `chat_id` to all DB functions (`feat/chat-id` branch)~~
