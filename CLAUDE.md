# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

AI-powered job search automation for IT internships and junior positions in Poland.
The bot scrapes vacancies, scores them against a candidate's resume, generates personalized
cover letters, and notifies the user via Telegram.

**Current stage:** PostgreSQL-backed, multi-user schema, ready for Railway deployment.
**Target:** Multi-user SaaS product with web interface and paid API integrations.

---

## Current Stack

| Component | Tool | Note |
|---|---|---|
| Job sources | Adzuna + NoFluffJobs + Remotive | Adzuna needs keys; NoFluffJobs and Remotive are keyless. JustJoin.it is dead (API removed). Each source fails silently |
| AI — scoring | `claude-haiku-4-5-20251001` | Scores jobs 0–10; prompt caching on resume block |
| AI — cover letter | `claude-sonnet-4-6` | Generates 100–120 word cover letters; prompt caching on resume block |
| AI — query builder | `claude-haiku-4-5-20251001` (via Groq `llama-3.1-8b-instant`) | Builds Adzuna search queries from resume |
| Database | PostgreSQL via `psycopg2` | `ThreadedConnectionPool(2, 10)`; `DATABASE_URL` env var; all ops scoped to `chat_id` |
| Notifications | Telegram Bot (`python-telegram-bot`) | Single user guard via `owner_only` decorator + `TELEGRAM_CHAT_ID` |
| i18n | `strings.py` | EN / RU / PL; `t(lang, "key", **kwargs)` helper |
| Env management | `python-dotenv` | |

---

## Setup

```bash
pip install -r requirements.txt
```

Create `.env` in project root:
```
ANTHROPIC_API_KEY=   # console.anthropic.com
DATABASE_URL=        # postgresql://user:password@host:5432/dbname
                     # Railway injects this automatically when PostgreSQL plugin is added
ADZUNA_APP_ID=       # developer.adzuna.com — free tier
ADZUNA_APP_KEY=      # developer.adzuna.com — free tier
TELEGRAM_BOT_TOKEN=  # from @BotFather on Telegram
TELEGRAM_CHAT_ID=    # your personal Telegram chat ID
```

Local development requires a running PostgreSQL instance. Quickest option:
```bash
docker run -e POSTGRES_PASSWORD=pass -p 5432:5432 postgres:16
DATABASE_URL=postgresql://postgres:pass@localhost:5432/job_bot
```

---

## Commands

```bash
python main.py --scrape   # Fetch jobs (Adzuna + NoFluffJobs + Remotive) → save to DB
python main.py --score    # Score unscored jobs with AI + generate cover letters
python main.py --apply    # Open top-scored jobs (score >= 7) in browser
python main.py --bot      # Start Telegram bot
python main.py --all      # Run scrape + score + apply sequentially
```

Telegram bot commands:
`/start` `/language` `/resume` `/scrape` `/score` `/rescore` `/jobs [min_score]` `/stats` `/stop`
+ document upload (`.txt` / `.pdf` / `.docx`)

---

## Architecture

```
Adzuna API   ─┐
NoFluffJobs   ├─→ scraper.py → database.py (PostgreSQL, pool)
Remotive      ┘                      ↓
                     ai_score.py + cover_letter.py (Claude API, prompt caching)
                                      ↓
                         bot.py (Telegram, EN/RU/PL) / open_jobs.py (browser)
```

| Module | Role |
|---|---|
| `main.py` | CLI entry point (`argparse`), orchestrates pipeline stages; uses `CLI_CHAT_ID = 0` |
| `scraper.py` | Fetches from 3 sources via `_fetch_adzuna()`, `_fetch_nofluffjobs()`, `_fetch_remotive()`; Groq builds Adzuna queries; results deduplicated by `link` |
| `database.py` | PostgreSQL wrapper with `ThreadedConnectionPool`; all public functions scoped to `chat_id`; `%s` placeholders |
| `ai_score.py` | Haiku scores each job 0–10; prompt caching on the static resume+instructions block |
| `cover_letter.py` | Sonnet generates 100–120 word cover letters; prompt caching on the static resume+instructions block |
| `resume_parser.py` | Parses TXT/PDF/DOCX → plain text; `load_resume(chat_id)` / `save_resume(text, chat_id)` → DB |
| `strings.py` | All UI strings in EN/RU/PL; `t(lang, "key", **kwargs)` with English fallback |
| `open_jobs.py` | Opens jobs with score ≥ 7 in browser, marks applied after confirmation; uses `CLI_CHAT_ID` |
| `bot.py` | Telegram bot with inline buttons, multilingual UI, `owner_only` guard |

---

## Key Details

- **Resume storage** — stored in `user_settings.resume_text` per `chat_id`. `load_resume(chat_id)` reads from DB; `save_resume(text, chat_id)` writes to DB. No `resume.txt` file is used.
- **Language storage** — stored in `user_settings.language` per `chat_id`. Default `"en"`. Changed via `/language` inline buttons. `get_user_lang(chat_id)` / `set_user_lang(chat_id, lang)`.
- **Job sources** — 3 sources in `scraper.py`. `_fetch_nofluffjobs()` uses POST API with `?salaryCurrency=PLN&salaryPeriod=month` as query params (not body). `_fetch_adzuna()` uses Groq-built queries. All sources fail silently and return `[]`.
- **Database schema** — `jobs`: `id BIGSERIAL, chat_id BIGINT, title, company, link, tech_stack, remote, city, score, cover_letter, applied, description`. UNIQUE on `(link, chat_id)`. `applied`: 0=pending, 1=applied, 2=skipped. `user_settings`: `chat_id BIGINT PK, language, resume_text`.
- **Connection pool** — `psycopg2.pool.ThreadedConnectionPool(minconn=2, maxconn=10)`. Each function acquires a connection via `_get_conn()` context manager. All queries use `%s` placeholders (not `?`).
- **Prompt caching** — `ai_score.py` and `cover_letter.py` mark the static resume+instructions block with `"cache_control": {"type": "ephemeral"}`. After the first job in a batch, Anthropic serves the cached block at 10% of normal token cost.
- **CLI sentinel** — `CLI_CHAT_ID = 0` (exported from `database.py`) is used by `main.py` and `open_jobs.py` so the CLI pipeline works with the same scoped schema as the bot.
- **Inline buttons** — city quick-picks in `/scrape`, language picker in `/language` and first `/start`, "Score now" after scrape, "View jobs" after score, "View jobs / Re-score" in `/stats`. Job cards have Apply/Skip/Letter buttons with translated labels.
- **No test suite** — manual testing only.

---

## Scaling Plan

### Stage 1 — MVP ✓ (complete)
- Single user, runs locally
- Claude API for scoring and letter generation (Haiku + Sonnet)
- Telegram bot with multilingual UI (EN/RU/PL)
- PostgreSQL database; all data scoped by `chat_id`
- Resume stored in `user_settings.resume_text`

### Stage 2 — Multi-user Beta
**Trigger:** first external users onboarding (next step is Railway deploy)

Remaining work:
- Deploy to **Railway.app** — `Procfile: worker: python main.py --bot`, PostgreSQL plugin auto-injects `DATABASE_URL`
- Replace `owner_only` with a whitelist (`ALLOWED_CHAT_IDS`) for closed beta
- Add per-user settings (default city, min score) to `user_settings`
- Rate limiting per user (one `/scrape` per hour, stored as `last_scrape_at`)
- Guided onboarding `ConversationHandler`: language → resume upload → city → auto-scrape

### Stage 3 — Web Product
**Trigger:** stable multi-user flow validated on Railway

Planned:
- **FastAPI backend** — `/api/jobs`, `/api/stats`, `/api/resume` endpoints
- **Simple HTML frontend** — job list with score bars, apply/skip, resume upload
- **Auth** — Telegram Login Widget
- **Subscription model** — free tier (20 scrapes/month) + paid tier (unlimited)

---

## Git Workflow

**After every change — commit. No exceptions.**

Claude Code must create a git commit after completing any task that modifies files.

### Commit format
```
<type>: <short description in English>
```

Types:
- `fix` — bug fix
- `feat` — new feature or module
- `refactor` — restructuring without behavior change
- `docs` — documentation only (README, CLAUDE.md)
- `chore` — dependencies, .env.example, config

### Rules
- One logical change = one commit. Don't bundle unrelated changes.
- Never commit `.env` or `jobs.db` — these are in `.gitignore`.
- If a task touches multiple modules, still one commit per logical unit.

---

## Multi-User Architecture Rules

Every public function in `database.py` takes `chat_id: int` as its first or second parameter.
All queries include `WHERE chat_id = %s`. This is non-negotiable.

```python
# ❌ Wrong
def get_jobs():
    cur.execute("SELECT * FROM jobs")

# ✅ Correct
def get_jobs(chat_id: int) -> list:
    cur.execute("SELECT * FROM jobs WHERE chat_id = %s", (chat_id,))
```

### What Claude Code must never do
- Write a DB query without `WHERE chat_id = %s` when user context exists
- Use `?` as a placeholder — this codebase uses PostgreSQL (`%s`)
- Store resume as a global file — resume is per `chat_id` in `user_settings.resume_text`
- Hardcode `CHAT_ID` inside functions or module-level logic

---

## Module Replacement Guide

**Replacing the AI model (`ai_score.py`, `cover_letter.py`):**
- `evaluate(job: dict, resume: str = None) → int` — must return integer 0–10
- `generate_letter(job: dict, resume: str = None) → str` — must return plain text
- Model, client, and API key are internal to each module
- Preserve the `cache_control: ephemeral` block on the resume+instructions prefix

**Extending job sources (`scraper.py`):**
- Add `_fetch_sourcename(city: str) → list[dict]`; call it in `search_jobs()`
- `search_jobs(city: str) → tuple[list[dict], bool]` interface must stay unchanged
- Each dict must have keys: `title, company, link, tech_stack, remote, city, description`
- Source must fail silently — wrap everything in `try/except`, return `[]` on error

**Extending the database (`database.py`):**
- Public interface must stay identical — internals (pool, driver) are implementation details
- All new functions must take `chat_id: int` and include it in every query
- Use `%s` placeholders, never `?`
- Use `ON CONFLICT (...) DO NOTHING` / `DO UPDATE SET`, never `INSERT OR IGNORE`

**Adding a new UI string (`strings.py`):**
- Add the key to all three languages: `"en"`, `"ru"`, `"pl"`
- Use `{named}` format placeholders, not positional `{0}`
- Call via `t(lang_code, "key", var=value)` — never hardcode strings in `bot.py`
