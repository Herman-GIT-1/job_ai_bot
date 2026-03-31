# Next Steps

Current state: MVP running locally for a single user.
Pipeline: Adzuna + JustJoin.it + Remotive + NoFluffJobs → scraper.py → database.py (SQLite, WAL pool) → ai_score.py + cover_letter.py (Claude API) → bot.py (Telegram).

Branch `feat/chat-id` — all sub-tasks complete, ready to merge into main.

---

## Priority 1 — PostgreSQL migration

**File:** `database.py`
**Trigger:** first external users onboarding

The schema is already multi-user ready (`chat_id` on every row, connection pool in place).
Only the engine needs to change:

- `sqlite3` → `psycopg2` (or `psycopg[binary]`)
- `?` placeholders → `%s`
- `INSERT OR IGNORE` → `INSERT ... ON CONFLICT DO NOTHING`
- `INTEGER PRIMARY KEY` → `BIGSERIAL PRIMARY KEY`
- Remove `check_same_thread=False` and the `Queue` pool — psycopg2 is thread-safe; use `psycopg2.pool.ThreadedConnectionPool` or SQLAlchemy
- Provide `DATABASE_URL` env var (Railway injects it automatically)
- Remove `CLI_CHAT_ID` sentinel when CLI tools are deprecated

---

## Priority 2 — Deploy to Railway.app for 24/7 uptime

Minimum path:
- Push merged `main` to GitHub
- Connect repo to Railway.app (free tier) + add PostgreSQL plugin
- Set env vars in Railway dashboard (`ANTHROPIC_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `ADZUNA_APP_ID`, `ADZUNA_APP_KEY`)
- Add `Procfile`: `worker: python main.py --bot`

---

## Priority 4 — UX improvements

### 4.1 Notify on new high-score jobs

After `/scrape` + `/score`, automatically send a message if any new jobs scored ≥ 8 —
without the user having to run `/jobs` manually.

### 4.2 Export to CSV

`/export` — send all jobs (or only applied) as a CSV file.
Useful for tracking application status outside the bot.

---

## Done ✓

- ~~Replace SerpAPI with JustJoin.it~~ — single GET, no key, no quota
- ~~Migrate scraper from JustJoin.it to Adzuna API~~ — JustJoin closed public API
- ~~Add multiple job sources~~ — Adzuna + JustJoin.it (fallback) + Remotive + NoFluffJobs
- ~~Fix `_db_count()` — moved to `database.py` as `count_jobs()`~~
- ~~Fix deprecated `get_event_loop()` → `get_running_loop()`~~
- ~~Parallel scoring with `asyncio.Semaphore(5)`~~
- ~~Cache resume once per scoring run~~
- ~~Replace hardcoded skills in `ai_score.py` / `cover_letter.py` prompts~~
- ~~Block unknown users — `owner_only` decorator~~
- ~~Guided onboarding in `/start`~~
- ~~Configurable score threshold: `/jobs 6`~~
- ~~Notify user when scraper used fallback queries~~
- ~~`/rescore` command~~
- ~~Pass job description into AI prompts~~
- ~~Fix city hardcoded as "Warsaw" in scraper~~
- ~~Add multilingual support (EN/RU/PL)~~
- ~~Add `chat_id` to all DB functions and queries (`feat/chat-id` branch)~~
- ~~Fix `open_jobs.py` — pass `CLI_CHAT_ID` to `get_jobs_to_apply` and `mark_applied`~~
- ~~Store resume in DB (`user_settings.resume_text`) — remove `resume.txt` file dependency~~
- ~~Replace singleton `conn`/`cursor` with WAL connection pool (`queue.Queue`, size=5)~~
- ~~Replace Groq → Anthropic Claude API (`claude-sonnet-4-6`)~~
