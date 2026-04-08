# CLAUDE.md

AI-powered job search bot · Telegram · PostgreSQL · Claude API · multi-user · EN/RU/PL · Mini App swipe UI.

## Rules (read before changing anything)


| File | When to read |
|---|---|
| `rules/database.md` | Any change to `database.py` or queries |
| `rules/api.md` | Any change to `ai_score.py`, `cover_letter.py`, `scraper.py` |
| `rules/bot.md` | Any change to `bot.py` or `strings.py` |
| `rules/git.md` | Before every commit |

## Stack

| Component | Tool |
|---|---|
| Scoring | `claude-haiku-4-5-20251001` → int 0–10 |
| Cover letter | `claude-sonnet-4-6` → str 100–120 words |
| Query builder | `claude-sonnet-4-6` → list[str] |
| Database | PostgreSQL · psycopg2 · ThreadedConnectionPool(2,10) |
| Bot | python-telegram-bot · owner_only guard |
| i18n | strings.py · t(lang, "key", **kwargs) |
| Mini App server | FastAPI + uvicorn · daemon thread · same Railway process |
| Mini App auth | Telegram initData HMAC-SHA256 (`Authorization: tma <initData>`) |

## Module contracts

| Module | Function | Signature |
|---|---|---|
| `ai_score.py` | `evaluate` | `(job: dict, resume: str = None) → int` |
| `cover_letter.py` | `generate_letter` | `(job: dict, resume: str = None) → str` |
| `scraper.py` | `search_jobs` | `(city: str = "Warsaw") → tuple[list[dict], bool]` |
| `resume_parser.py` | `load_resume` | `(chat_id: int) → str` |
| `database.py` | all functions | first param always `chat_id: int` |
| `webapp.py` | FastAPI `app` | imported by `main.py`; routes: `/app`, `/api/jobs`, `/api/skip`, `/api/save`, `/api/apply` |

## Schema

```
jobs:          id, chat_id, title, company, link, tech_stack,
               remote, city, score, cover_letter, applied, description,
               source, salary_min, salary_max, salary_currency,
               applied_at, job_status, created_at
               UNIQUE (link, chat_id)
               applied: 0=pending 1=applied 2=skipped 3=interested(saved)
               job_status: 'pending'|'applied'|'skipped'|'interested'|'interviewing'|'rejected'|'offer'

user_settings: chat_id PK, language DEFAULT 'en', resume_text, last_scrape_at
```

## Environment variables

| Var | Required | Notes |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | console.anthropic.com |
| `DATABASE_URL` | Yes | Railway injects; local: `postgresql://postgres:pass@localhost:5432/job_bot` |
| `TELEGRAM_BOT_TOKEN` | Bot mode | @BotFather; also used by `webapp.py` for HMAC verification |
| `TELEGRAM_CHAT_ID` | Bot mode | @userinfobot |
| `ADZUNA_APP_ID` | No | Without it Adzuna source is skipped silently |
| `ADZUNA_APP_KEY` | No | Same |
| `WEBAPP_URL` | No | Full URL of the deployed service (e.g. `https://xyz.railway.app`). When set, `/jobs` opens Mini App instead of chat cards |
| `PORT` | No | HTTP port for uvicorn (Railway injects automatically, default 8000) |