# NEXT_STEPS.md

Current state: PostgreSQL · multi-user schema · Claude API · Telegram EN/RU/PL · ready for Railway.

---

## Priority 1 — Deploy to Railway ← user has to say when it's have to be done

1. Push `main` to GitHub
2. Railway.app → "Deploy from GitHub repo"
3. Add PostgreSQL plugin — Railway injects `DATABASE_URL` automatically
4. Set env vars in Railway dashboard: `ANTHROPIC_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `ADZUNA_APP_ID`, `ADZUNA_APP_KEY`
5. Add `Procfile` to repo root:
   ```
   worker: python main.py --bot
   ```
6. Deploy → bot runs 24/7

**Cost:** Railway free tier covers this. PostgreSQL plugin free up to 1 GB.

**After deploy — add monitoring (15 min):**
- Sign up at UptimeRobot (free)
- Add a "TCP port" monitor for your Railway app
- Set alert to your email — you'll know when the bot crashes at 3am

---

## Priority 2 — Open to first external users

**Trigger:** after deploy is stable.

### 2.1 Replace owner_only with whitelist

File: `bot.py`

```python
ALLOWED = set(int(x) for x in os.getenv("ALLOWED_CHAT_IDS", "").split(",") if x)

def allowed(func):
    @functools.wraps(func)
    async def wrapper(update, context):
        if update.effective_chat.id not in ALLOWED:
            await update.message.reply_text("Bot is in closed beta.")
            return
        return await func(update, context)
    return wrapper
```

Add `ALLOWED_CHAT_IDS=id1,id2,id3` to `.env` and Railway dashboard.

### 2.2 Guided onboarding for new users

File: `bot.py` — `ConversationHandler`

```
/start
  → "Choose language" [EN] [RU] [PL]
  → "Send your resume (.txt / .pdf / .docx)"
  → <file uploaded>
  → "Which city?" [city buttons]
  → auto-runs /scrape + /score in background
  → sends first job cards
```

### 2.3 Rate limiting per user

Add `last_scrape_at TIMESTAMP` to `user_settings`.
Before running scrape: if `now - last_scrape_at < 1h`, reply "Come back in X minutes."

---

## Priority 3 — UX improvements

### 3.1 High-score alert after scoring

File: `bot.py` — `_run_score()`

String `score_high_alert` already in `strings.py`. Wire it in:

```python
high = len(get_jobs_to_apply(chat_id, min_score=8))
if high:
    await msg.reply_text(t(lang, "score_high_alert", high=high))
```

### 3.2 Export to CSV

New `/export` command — sends all jobs as `.csv` file.

```python
import csv, io

async def cmd_export(update, context):
    chat_id = update.effective_chat.id
    rows = get_all_jobs(chat_id)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["title", "company", "link", "score", "applied", "city", "tech_stack"])
    writer.writerows(rows)
    await update.message.reply_document(
        document=buf.getvalue().encode("utf-8"),
        filename="jobs_export.csv"
    )
```

### 3.3 Scheduled auto-scrape

**Warning:** APScheduler won't work reliably on Railway free tier (worker sleeps).
Use Railway Cron Jobs instead — create a separate cron job that hits an endpoint.

Alternative: `python-telegram-bot` `JobQueue` — runs inside the bot process, survives as long as the worker is alive.

```python
application.job_queue.run_daily(
    daily_scrape,
    time=datetime.time(hour=9, tzinfo=datetime.timezone.utc)
)
```

### 3.4 /jobs pagination

When >10 jobs with score ≥ 7 exist, Telegram floods the chat.
Add "Show more →" inline button with offset in callback data: `jobs_page:5`.

---

## Priority 4 — Database backup

Railway free PostgreSQL has no automatic backups.

Quick solution: daily `pg_dump` via Railway cron → upload to Telegram (send to yourself as a file).

```python
import subprocess
result = subprocess.run(["pg_dump", DATABASE_URL], capture_output=True)
await bot.send_document(chat_id=OWNER_ID, document=result.stdout, filename="backup.sql")
```

Add this as a daily cron job on Railway (separate from the bot worker).

---

## Priority 5 — Web dashboard (Stage 3)

**Trigger:** after stable multi-user flow on Railway.

- FastAPI backend — `/api/jobs`, `/api/stats`, `/api/resume`
- Simple HTML frontend — job list with score bars, apply/skip, resume upload
- Auth — Telegram Login Widget
- Stripe — free tier (20 scrapes/month) + paid (unlimited)

DB schema already ready — every table has `chat_id`.

---

## Done ✓

- Multi-user schema with chat_id everywhere
- PostgreSQL + ThreadedConnectionPool
- Prompt caching on resume block (ai_score + cover_letter)
- Three job sources: Adzuna + NoFluffJobs + Remotive
- Telegram bot with EN/RU/PL
- Resume stored in DB (not as file)
- /rescore command
- Configurable score threshold /jobs 6
- Job description passed to AI prompts
- Inline city quick-pick buttons
- owner_only guard
- Guided onboarding in /start