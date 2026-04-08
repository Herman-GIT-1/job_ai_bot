# Job AI Bot

AI-powered Telegram bot for finding internships and junior positions in Poland.

Scrapes vacancies from multiple sources, scores them with Claude AI against your resume, generates cover letters, and provides a swipe interface via Telegram Mini App.

---

## Features

- **Job search** — Adzuna, NoFluffJobs, Remotive; Claude builds personalised queries from your resume
- **AI scoring** — every vacancy gets a 0–10 score (Haiku, fast and cheap)
- **Cover letter** — auto-generated per vacancy + resume (Sonnet)
- **Swipe Mini App** — cards inside Telegram: swipe left = skip, swipe right = save, button = apply
- **Application tracker** — `/tracker` with date grouping and statuses (interviewing / rejected / offer)
- **AI resume feedback** — `/feedback` analyses weak spots
- **Multilingual** — EN / RU / PL, `/language` to switch
- **Multi-user** — all data is isolated by `chat_id`

---

## Stack

| Layer | Technology |
|---|---|
| Bot | python-telegram-bot 20+ |
| Web / Mini App | FastAPI + uvicorn (daemon thread) |
| Database | PostgreSQL · psycopg2 · ThreadedConnectionPool |
| AI — scoring | `claude-haiku-4-5-20251001` |
| AI — letters, queries | `claude-sonnet-4-6` |
| Deploy | Railway (single process: bot + web server) |

---

## Architecture

```
Telegram (user)
    │
    ├── Commands (/scrape, /score, /jobs, ...)
    │       └── bot.py ──► scraper.py    ──► Adzuna / NoFluffJobs / Remotive
    │                  ──► ai_score.py   ──► Claude Haiku
    │                  ──► cover_letter.py ──► Claude Sonnet
    │                  ──► database.py   ──► PostgreSQL
    │
    └── /jobs → WebAppInfo button
            └── Mini App (Telegram browser)
                    ├── GET  /app          → static/index.html
                    ├── GET  /api/jobs     → JSON vacancies (HMAC auth)
                    ├── POST /api/skip     → applied=2
                    ├── POST /api/save     → applied=3 (saved)
                    └── POST /api/apply    → applied=1

main.py --bot
    ├── thread: uvicorn webapp.py (port $PORT)
    └── bot.main() — Telegram polling
```

---

## Local Setup

### 1. Clone and install dependencies

```bash
git clone https://github.com/Herman-GIT-1/job_ai_bot
cd job_ai_bot
pip install -r requirements.txt
```

### 2. Create `.env`

```env
ANTHROPIC_API_KEY=sk-ant-...
DATABASE_URL=postgresql://postgres:pass@localhost:5432/job_bot
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...

# Optional
ADZUNA_APP_ID=...
ADZUNA_APP_KEY=...
WEBAPP_URL=https://your-service.railway.app
```

### 3. Run

```bash
# Telegram bot only (+ Mini App server on localhost:8000)
python main.py --bot

# CLI mode (without Telegram)
python main.py --scrape --city Warsaw
python main.py --score
python main.py --all
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | [console.anthropic.com](https://console.anthropic.com) → API Keys |
| `DATABASE_URL` | Yes | Railway injects automatically; locally — psycopg2 connection string |
| `TELEGRAM_BOT_TOKEN` | Bot mode | @BotFather |
| `TELEGRAM_CHAT_ID` | Bot mode | @userinfobot — numeric ID (admin) |
| `ADZUNA_APP_ID` | No | [developer.adzuna.com](https://developer.adzuna.com) — source is silently skipped without it |
| `ADZUNA_APP_KEY` | No | Same |
| `WEBAPP_URL` | No | Full service URL (e.g. `https://xyz.railway.app`). When set, `/jobs` opens the Mini App instead of chat cards |
| `PORT` | No | uvicorn port (Railway injects automatically, default 8000) |

---

## Bot Commands

| Command | Action |
|---|---|
| `/start` | Welcome message; prompts to upload resume |
| `<file>` | Upload resume (.txt / .pdf / .docx) |
| `/resume` | Show current resume |
| `/feedback` | AI resume analysis: missing skills, weak sections |
| `/scrape` | Find vacancies (will ask for city) |
| `/score` | AI scoring + cover letter generation |
| `/rescore` | Reset scores and re-score all pending vacancies |
| `/jobs` | Open Mini App (if `WEBAPP_URL` is set) or show cards in chat |
| `/tracker` | Application tracker grouped by date: today / this week / 2+ weeks |
| `/stats` | Statistics: found, scored, applied, skipped, saved |
| `/language` | Change language (EN / RU / PL) |
| `/stop` | Stop the bot (admin only) |

---

## Telegram Mini App

`/jobs` → **🃏 View vacancies** button opens the Telegram browser with a card-based interface.

**Gestures:**
- Swipe left — skip vacancy
- Swipe right — save to "My List"
- **✅ Apply** button — opens the vacancy link and marks it as applied

**Authentication:** the Mini App sends `initData` in the `Authorization: tma <initData>` header. The server verifies the signature via `HMAC-SHA256(key="WebAppData", msg=BOT_TOKEN)`.

---

## Vacancy Statuses

| `applied` | `job_status` | Meaning |
|---|---|---|
| 0 | `pending` | New, awaiting scoring or review |
| 1 | `applied` | Applied |
| 2 | `skipped` | Skipped |
| 3 | `interested` | Saved to "My List" (Mini App) |
| 1 | `interviewing` | Interview scheduled |
| 1 | `rejected` | Rejected |
| 1 | `offer` | Offer received |

---

## Deploy on Railway

1. Connect the repository in Railway
2. Add a PostgreSQL service (Railway Dashboard → Add Service)
3. Set environment variables (see table above)
4. Railway uses `Procfile`:
   ```
   web: python main.py --bot
   ```
5. After deploy, copy the public service URL into `WEBAPP_URL`

---

## Project Structure

```
job_ai_bot/
├── main.py            # CLI + bot startup + uvicorn thread
├── bot.py             # Telegram handlers
├── webapp.py          # FastAPI Mini App server
├── static/
│   └── index.html     # Mini App frontend (swipe UI)
├── database.py        # PostgreSQL layer (all functions take chat_id)
├── scraper.py         # Scrapers: Adzuna, NoFluffJobs, Remotive
├── ai_score.py        # Vacancy scoring (Haiku)
├── cover_letter.py    # Cover letter generation (Sonnet)
├── resume_feedback.py # Resume analysis (Sonnet)
├── resume_parser.py   # .txt/.pdf/.docx parsing
├── strings.py         # i18n: EN/RU/PL
├── open_jobs.py       # CLI: open vacancies in browser
├── Procfile           # Railway: web process
└── .claude/
    └── rules/         # Rules for AI assistant
```
