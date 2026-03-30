# Next Steps

Current state: MVP running locally for a single user.
Pipeline: JustJoin.it API → scraper.py → database.py (SQLite) → ai_score.py + cover_letter.py (Groq) → bot.py (Telegram).

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

### 2.1 PostgreSQL + user_id per row

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

### 2.2 Store resume in DB, not in file

**File:** `resume_parser.py`

`resume.txt` is a single-user hack. When moving to PostgreSQL,
redirect `load_resume(chat_id)` and `save_resume(text, chat_id)` to `users.resume_text`.
`resume_parser.py` already has these functions — only the storage backend changes.

### 2.3 Deploy to Railway.app for 24/7 uptime

Minimum path:
- Push to GitHub
- Connect repo to Railway.app (free tier)
- Set env vars in Railway dashboard
- Add `Procfile`: `worker: python main.py --bot`

---

## Priority 3 — UX improvements

### 3.1 Export to CSV

`/export` — send all jobs (or only applied) as a CSV file.
Useful for tracking application status outside the bot.

### 3.2 Notify on new high-score jobs

After `/scrape` + `/score`, automatically send a message if any new jobs scored ≥ 8 —
without the user having to run `/jobs` manually.

---

## Done ✓

- ~~0.1 Replace SerpAPI with JustJoin.it~~ — single GET, no key, no quota
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
