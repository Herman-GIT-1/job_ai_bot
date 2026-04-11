# Job Search Bot 🤖

Automated internship and junior job search bot: scrapes vacancies from Adzuna, NoFluffJobs and Remotive, scores them with AI, generates cover letters, and delivers results via Telegram.

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Create a `.env` file in the project root (`.env.example` is included in the repository):

```env
ANTHROPIC_API_KEY=your_anthropic_api_key_here
DATABASE_URL=postgresql://user:password@localhost:5432/job_bot
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here   # admin chat_id — get it from @userinfobot
ADZUNA_APP_ID=your_adzuna_app_id_here
ADZUNA_APP_KEY=your_adzuna_app_key_here
```

| Variable | Where to get it |
|---|---|
| `ANTHROPIC_API_KEY` | console.anthropic.com → API Keys |
| `DATABASE_URL` | Railway injects automatically; locally use `postgresql://...` |
| `TELEGRAM_BOT_TOKEN` | @BotFather on Telegram |
| `TELEGRAM_CHAT_ID` | @userinfobot on Telegram |
| `ADZUNA_APP_ID` | developer.adzuna.com → My Apps |
| `ADZUNA_APP_KEY` | developer.adzuna.com → My Apps |

## Running

```bash
python main.py --scrape   # find vacancies and save to DB
python main.py --score    # AI scoring + cover letter generation
python main.py --apply    # open top vacancies (score >= 7) in browser
python main.py --bot      # start the Telegram bot
python main.py --all      # scrape + score + apply in sequence
```

## Telegram Bot Commands

| Command | Action |
|---|---|
| `/start` | Welcome message and command list |
| `/resume` | Show current resume (first 600 characters) |
| `/scrape` | Find new vacancies (will ask for city) |
| `/score` | AI scoring + cover letter for all new vacancies |
| `/rescore` | Reset scores and re-score all pending vacancies |
| `/jobs` | Vacancies with score ≥ 7, buttons: Apply / Skip / Letter |
| `/tracker` | Application tracker with statuses and follow-up alerts |
| `/feedback` | AI analysis of your resume (missing skills, weak sections) |
| `/stats` | Statistics: found, scored, applied, skipped |
| `/language` | Change interface language (EN / RU / PL) |
| `/stop` | Stop the bot (admin only) |
| `<file>` | Upload resume (.txt / .pdf / .docx) |

Pressing **Letter 📄** sends the cover letter as text directly in the chat without changing the vacancy status.

## How it works

```
Adzuna API  ─┐
NoFluffJobs ─┼─→ scraper.py → database.py (PostgreSQL)
Remotive    ─┘                      ↓
                       ai_score.py + cover_letter.py (Claude API)
                                    ↓
                       bot.py (Telegram) / open_jobs.py (browser)
```

- `/scrape` uses Claude to generate 5 personalised search queries from the resume, queries each job source, filters by seniority (junior/intern), and saves results to PostgreSQL
- `/score` evaluates each new vacancy (0–10) and generates a cover letter for jobs scoring ≥ 6
- `/jobs` displays vacancies with score ≥ 6 that have not yet been applied to or skipped, with pagination
- The bot supports **multiple users** — all data is scoped by `chat_id`
- Deployed on **Railway** with PostgreSQL; the Mini App (swipe UI) runs in the same process via FastAPI
