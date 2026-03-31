# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

AI-powered job search automation for IT internships and junior positions in Poland.
The bot scrapes vacancies, scores them against a candidate's resume, generates personalized
cover letters, and notifies the user via Telegram.

**Current stage:** MVP / local prototype — single user, free-tier APIs, no server.
**Target:** Multi-user SaaS product with web interface and paid API integrations.

---

## Current Stack (MVP / Testing only)

| Component | Tool | Note |
|---|---|---|
| Job sources | Adzuna + JustJoin.it + Remotive + NoFluffJobs | Adzuna needs keys; others are keyless. Each fails silently |
| AI model | Anthropic Claude API (`claude-sonnet-4-6`) | Uses OpenAI-compatible endpoint via `client.chat.completions` |
| Database | SQLite (`jobs.db`) | Local only; connection pool (WAL, size=5); all ops scoped to `chat_id` |
| Notifications | Telegram Bot (python-telegram-bot) | Single user (owner guard via `TELEGRAM_CHAT_ID`) |
| Env management | python-dotenv | |

---

## Setup

```bash
pip install -r requirements.txt
```

Create `.env` in project root:
```
ANTHROPIC_API_KEY=   # console.anthropic.com
ADZUNA_APP_ID=       # developer.adzuna.com — free tier
ADZUNA_APP_KEY=      # developer.adzuna.com — free tier
TELEGRAM_BOT_TOKEN=  # from @BotFather on Telegram
TELEGRAM_CHAT_ID=    # your personal Telegram chat ID
```

---

## Commands

```bash
python main.py --scrape   # Fetch jobs (Adzuna + JustJoin + Remotive + NoFluffJobs) → save to jobs.db
python main.py --score    # Score jobs with AI + generate cover letters
python main.py --apply    # Open top-scored jobs (score >= 7) in browser
python main.py --bot      # Start Telegram bot
python main.py --all      # Run scrape + score + apply sequentially
```

Telegram bot commands: `/start` `/resume` `/scrape` `/score` `/jobs` `/stats` `/stop` + document upload (`.txt`/`.pdf`/`.docx`).

---

## Architecture (Current)

```
Adzuna API ─┐
JustJoin.it ├─→ scraper.py → database.py (SQLite, pool)
Remotive    │                       ↓
NoFluffJobs ┘       ai_score.py + cover_letter.py (Claude API)
                                    ↓
                    bot.py (Telegram) / open_jobs.py (browser)
```

| Module | Role |
|---|---|
| `main.py` | CLI entry point (`argparse`), orchestrates pipeline stages; uses `CLI_CHAT_ID = 0` |
| `scraper.py` | Fetches from 4 sources; Claude builds Adzuna queries; results deduplicated by link |
| `database.py` | SQLite wrapper with WAL connection pool; all public functions scoped to `chat_id` |
| `ai_score.py` | AI scores each job 0–10 by comparing resume to job requirements |
| `cover_letter.py` | AI generates 100–120 word tailored cover letters per job |
| `resume_parser.py` | Parses TXT/PDF/DOCX → plain text; `load_resume(chat_id)` / `save_resume(text, chat_id)` → DB |
| `open_jobs.py` | Opens jobs with score ≥ 7 in browser, marks applied after confirmation; uses `CLI_CHAT_ID` |
| `bot.py` | Telegram bot: /scrape /score /jobs /stats /resume /stop + file upload |

---

## Key Details

- **Resume storage** — resume text is stored in `user_settings.resume_text` per `chat_id`. `load_resume(chat_id)` reads from DB; `save_resume(text, chat_id)` writes to DB. Uploading a new resume via bot takes effect immediately without restart. No `resume.txt` file is used.
- **Job sources** — 4 sources in `scraper.py`, each as a separate `_fetch_*()` function. All fail silently and return `[]` on error. Results are deduplicated by `link` at the end of `search_jobs()`. Adzuna requires `ADZUNA_APP_ID`/`ADZUNA_APP_KEY`; JustJoin.it, Remotive, NoFluffJobs are keyless.
- **Database schema** — `jobs` table: `id, chat_id, title, company, link, tech_stack, remote, city, score, cover_letter, applied, description`. UNIQUE on `(link, chat_id)`. `applied`: 0=pending, 1=applied, 2=skipped. `user_settings` table: `chat_id, language, resume_text`.
- **Connection pool** — `database.py` keeps 5 SQLite connections in a `queue.Queue`. Each public function acquires a connection via `_get_conn()` context manager and returns it after use. WAL mode is enabled on all connections.
- **CLI sentinel** — `CLI_CHAT_ID = 0` (exported from `database.py`) is used by `main.py` and `open_jobs.py` so the CLI pipeline works with the same scoped schema as the bot.
- **No test suite** — manual testing only.

---

## Scaling Plan

This section describes the intended evolution of the project.
When making changes, avoid decisions that block the transitions below.

### Stage 1 — MVP (now)
- Single user, runs locally
- Claude API for scoring and letter generation
- Telegram bot for notifications
- SQLite database with connection pool; all data scoped by `chat_id`
- Resume stored in `user_settings.resume_text` (DB, not file)

### Stage 2 — Multi-user Beta
**Trigger:** first external users onboarding

Planned changes:
- Replace **SQLite → PostgreSQL** (one DB, `chat_id` per row — schema is already ready)
- Remove `CLI_CHAT_ID` sentinel when CLI tools are deprecated
- Add **FastAPI backend** for user registration and resume upload
- Add **Celery + Redis** for async per-user job processing
- Deploy to **Railway.app** or VPS (bot runs 24/7)

### Stage 3 — Web Product
**Trigger:** stable multi-user flow validated

Planned changes:
- Web interface (React or simple HTML) for account management and job dashboard
- User onboarding via Telegram `/start` → resume upload flow
- Subscription model (free tier + paid)
- Analytics per user (jobs found, applied, response rate)

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

### Examples
```
feat: add Telegram bot with inline apply/skip buttons
fix: pass CLI_CHAT_ID to get_jobs_to_apply and mark_applied in open_jobs.py
refactor: replace singleton conn/cursor with WAL connection pool
docs: update CLAUDE.md with current architecture
chore: add ANTHROPIC_API_KEY to .env.example
```

### Rules
- One logical change = one commit. Don't bundle unrelated changes.
- Never commit `.env` or `jobs.db` — these are in `.gitignore`.
- If a task touches multiple modules, still one commit per logical unit.
- If unsure about commit message — ask, don't skip the commit.

---

## Multi-User Architecture Rules

The bot is currently single-user (hardcoded `CHAT_ID`), but must be built
user-aware from the start to avoid painful rewrites later.

### Core rule
**Never treat `CHAT_ID` as a global constant in logic.** Always pass it as a
parameter or read it from a user object.

```python
# ❌ Wrong — hardcoded, breaks with multiple users
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
await bot.send_message(CHAT_ID, text)

# ✅ Correct — user-aware, scales to any number of users
await bot.send_message(user.chat_id, text)
```

### User identity
Every user is identified by `chat_id` (Telegram's unique ID per chat).
When the database moves to PostgreSQL, the schema is already ready — every table
has `chat_id` as a scoping key:

```
user_settings (chat_id PK, language, resume_text)
jobs          (id, chat_id, title, company, ...)  — UNIQUE (link, chat_id)
```

### Onboarding flow (when opening to external users)
```
/start → bot asks to upload resume (.txt or .pdf)
       → saves chat_id + resume to user_settings
       → confirms: "Scout is ready. Use /jobs to see matches."
```

### Access control stages
- **Now (MVP):** single user via `CHAT_ID` in `.env` — acceptable for personal use
- **Beta:** whitelist of `chat_id` values, manual approval
- **Launch:** open registration via `/start` with resume upload

### What Claude Code must never do
- Hardcode `CHAT_ID` inside functions or module-level logic
- Store resume as a single global file — resume is now per `chat_id` in DB
- Write DB queries without `WHERE chat_id = ?` when user context exists

---

## Module Replacement Guide

When replacing temporary modules, follow these contracts:

**Replacing the AI model (`ai_score.py`, `cover_letter.py`):**
- `evaluate(job: dict, resume: str = None) → int` must return integer 0–10
- `generate_letter(job: dict, resume: str = None) → str` must return plain text string
- Model, client and API key are internal to each module

**Replacing/extending job sources (`scraper.py`):**
- Add a new `_fetch_*(city) → list[dict]` function; call it inside `search_jobs()`
- `search_jobs(city: str) → tuple[list[dict], bool]` interface must stay unchanged
- Each dict must have keys: `title, company, link, tech_stack, remote, city, description`

**Replacing SQLite (`database.py`):**
- Public interface must stay identical:
  `save_job()`, `get_jobs()`, `get_jobs_to_apply()`, `mark_applied()`, `update_job()`,
  `get_job_link()`, `get_cover_letter()`, `get_stats()`, `count_jobs()`, `reset_scores()`,
  `get_user_lang()`, `set_user_lang()`, `get_resume()`, `set_resume()`
- Internals (pool, connections) are implementation details

> Keeping these interfaces stable means swapping one module never breaks others.
