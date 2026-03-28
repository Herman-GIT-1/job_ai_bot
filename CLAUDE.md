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
| Job source | SerpAPI (Google Jobs) | Free tier: 100 req/month — prototype only |
| AI model | Groq `llama-3.1-8b-instant` | Free — prototype only, lower quality than Claude/GPT |
| Database | SQLite (`jobs.db`) | Local only, single user |
| Notifications | Telegram Bot (python-telegram-bot) | Single user (hardcoded chat_id) |
| Env management | python-dotenv | |

> ⚠️ **Groq and SerpAPI are temporary.** They exist only to validate the pipeline without cost.
> Before any public launch, both must be replaced (see Scaling Plan below).

---

## Setup

```bash
pip install -r requirements.txt
```

Create `.env` in project root:
```
GROQ_API_KEY=        # console.groq.com — free
SERPAPI_KEY=         # serpapi.com — free 100 req/month
TELEGRAM_BOT_TOKEN=  # from @BotFather on Telegram
TELEGRAM_CHAT_ID=    # your personal Telegram chat ID
```

---

## Commands

```bash
python main.py --scrape   # Fetch jobs via SerpAPI → save to jobs.db
python main.py --score    # Score jobs with AI + generate cover letters
python main.py --apply    # Open top-scored jobs (score >= 7) in browser
python main.py --bot      # Start Telegram bot
python main.py --all      # Run scrape + score + apply sequentially
```

---

## Architecture (Current)

```
SerpAPI → scraper.py → database.py (SQLite)
                              ↓
                    ai_score.py + cover_letter.py (Groq)
                              ↓
                    bot.py (Telegram) / open_jobs.py (browser)
```

| Module | Role |
|---|---|
| `main.py` | CLI entry point (`argparse`), orchestrates pipeline stages |
| `scraper.py` | Calls Groq to build city-aware queries from resume, fetches via SerpAPI |
| `database.py` | SQLite wrapper: schema with score, cover_letter, applied columns |
| `ai_score.py` | AI scores each job 0–10 by comparing resume to job requirements |
| `cover_letter.py` | AI generates 100–120 word tailored cover letters per job |
| `resume_parser.py` | Parses TXT/PDF/DOCX → plain text; `load_resume()` / `save_resume()` |
| `open_jobs.py` | Opens jobs with score ≥ 7 in browser, marks applied after confirmation |
| `bot.py` | Telegram bot: /scrape /score /jobs /stats /resume /stop + file upload |

---

## Key Details

- **Resume context** — `resume.txt` is read fresh on every call inside `ai_score.py`, `cover_letter.py`, and `scraper.py` via `resume_parser.load_resume()`. Uploading a new resume via bot takes effect immediately without restart.
- **Search queries** — generated dynamically by Groq from resume content on each `/scrape`. Falls back to 3 generic queries if resume is missing or Groq fails.
- **Database schema** — `jobs` table: `id, title, company, link, tech_stack, remote, city, score, cover_letter, applied`. `link` has UNIQUE constraint. No migrations system — schema changes require `ALTER TABLE` or deleting `jobs.db`.
- **SerpAPI quota** — 100 free requests/month. Each `--scrape` run consumes N requests equal to the number of generated queries (~6–8).
- **No test suite** — manual testing only.

---

## Scaling Plan

This section describes the intended evolution of the project.
When making changes, avoid decisions that block the transitions below.

### Stage 1 — MVP (now)
- Single user, runs locally
- Free APIs: Groq + SerpAPI
- Telegram bot for notifications
- SQLite database

### Stage 2 — Multi-user Beta
**Trigger:** first external users onboarding

Planned changes:
- Replace **SQLite → PostgreSQL** (one DB, user_id per row)
- Replace **Groq → Anthropic Claude API** (`claude-sonnet`) for scoring and letter generation
- Replace **SerpAPI → JustJoin.it public API** or another reliable job source without quota limits
- Add **FastAPI backend** for user registration and resume upload
- Add **Celery + Redis** for async per-user job processing
- Each user has own `resume.txt` stored server-side
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
fix: add cover_letter column to jobs table schema
refactor: move resume path resolution to use __file__
docs: update CLAUDE.md with scaling plan
chore: add TELEGRAM_BOT_TOKEN to .env.example
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
When the database moves to PostgreSQL, every table that is currently
single-user must gain a `user_id` or `chat_id` foreign key:

```
users (chat_id, username, resume_text, created_at)
jobs  (id, chat_id → users, title, company, ...)
```

### Onboarding flow (when opening to external users)
```
/start → bot asks to upload resume (.txt or .pdf)
       → saves chat_id + resume to DB
       → confirms: "Scout is ready. Use /jobs to see matches."
```

### Access control stages
- **Now (MVP):** single user via `CHAT_ID` in `.env` — acceptable for personal use
- **Beta:** whitelist of `chat_id` values, manual approval
- **Launch:** open registration via `/start` with resume upload

### What Claude Code must never do
- Hardcode `CHAT_ID` inside functions or module-level logic
- Store resume as a single global file when adding multi-user features
- Write DB queries without `WHERE chat_id = ?` when user context exists

---

## Module Replacement Guide

When replacing temporary modules, follow these contracts:

**Replacing Groq (`ai_score.py`, `cover_letter.py`):**
- `evaluate(job: dict) → int` must return integer 0–10
- `generate_letter(job: dict) → str` must return plain text string
- Model, client and API key are internal to each module

**Replacing SerpAPI (`scraper.py`):**
- `search_jobs(city: str) → list[dict]` must return list of dicts with keys:
  `title, company, link, tech_stack, remote, city`

**Replacing SQLite (`database.py`):**
- Public interface must stay identical:
  `save_job()`, `get_jobs()`, `get_jobs_to_apply()`, `mark_applied()`, `update_job()`, `get_job_link()`, `get_stats()`
- Internals (connection, cursor) are implementation details

> Keeping these interfaces stable means swapping one module never breaks others.