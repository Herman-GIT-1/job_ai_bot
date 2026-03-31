# Next Steps

Current state: PostgreSQL-backed, multi-user schema, deployed locally. Ready for Railway.
Pipeline: Adzuna + NoFluffJobs + Remotive → scraper.py → database.py (PostgreSQL, ThreadedConnectionPool)
         → ai_score.py + cover_letter.py (Claude API, prompt caching) → bot.py (Telegram, EN/RU/PL).

---

## Priority 2 — Deploy to Railway.app

**Trigger:** do this now — the codebase is ready.

1. Push `main` to GitHub (if not already)
2. Create new project on Railway.app → "Deploy from GitHub repo"
3. Add PostgreSQL plugin — Railway auto-injects `DATABASE_URL`
4. Set env vars in Railway dashboard:
   - `ANTHROPIC_API_KEY`
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
   - `ADZUNA_APP_ID` + `ADZUNA_APP_KEY`
5. Add `Procfile` to repo root:
   ```
   worker: python main.py --bot
   ```
6. Deploy → bot runs 24/7, no local machine needed

**Cost:** Railway free tier covers this. PostgreSQL plugin is free up to 1 GB.

---

## Priority 3 — Open registration (first external users)

**Trigger:** after deploy is stable and you want to onboard friends / testers.

### 3.1 Remove hardcoded single-user guard

**File:** `bot.py`

Currently `owner_only` blocks everyone except `TELEGRAM_CHAT_ID`. For open registration,
remove this decorator and replace with a whitelist or open `/start` flow.

Staged approach:
```
Stage A — whitelist: ALLOWED_CHAT_IDS = {id1, id2, ...} in .env, comma-separated
Stage B — open: any user who sends /start gets onboarded
```

**Implementation for Stage A (10 min):**
```python
ALLOWED = set(int(x) for x in os.getenv("ALLOWED_CHAT_IDS", "").split(",") if x)

def allowed(func):
    @functools.wraps(func)
    async def wrapper(update, context):
        if update.effective_chat.id not in ALLOWED:
            await update.message.reply_text("Bot is in closed beta. Contact admin.")
            return
        return await func(update, context)
    return wrapper
```

### 3.2 Onboarding conversation for new users

**File:** `bot.py`

New user flow via `ConversationHandler`:
```
/start
  → "Choose language" [EN] [RU] [PL]
  → "Send your resume (.txt / .pdf / .docx)"
  → <file uploaded>
  → "Which city to search in?" [city buttons]
  → auto-runs /scrape + /score in background
  → sends first job cards
```

This replaces the current "send resume, then run /scrape manually" flow.
Use `context.user_data` to track onboarding state per user.

### 3.3 Per-user scrape settings in DB

**File:** `database.py`, `bot.py`

Add to `user_settings`:
```sql
ALTER TABLE user_settings ADD COLUMN city TEXT DEFAULT 'Warszawa';
ALTER TABLE user_settings ADD COLUMN min_score INTEGER DEFAULT 7;
```

User sets preferred city once via `/settings city Kraków` — no need to type it every `/scrape`.
`/settings score 6` — change default score threshold.

### 3.4 Rate limiting per user

**File:** `bot.py`

Prevent abuse: one `/scrape` per user per hour.
Store `last_scrape_at TIMESTAMP` in `user_settings`.
Check before running: if `now - last_scrape_at < 1h`, reply "Come back in X minutes."

---

## Priority 4 — UX & quality improvements

### 4.1 High-score alert after scoring ✳ already in strings.py

**File:** `bot.py:_run_score()`

After scoring completes, count jobs with score ≥ 8.
If any found, send an additional message:
```
⭐ 3 jobs scored ≥ 8 — these are your best matches. /jobs 8
```
Key `score_high_alert` already added to `strings.py` — just wire it in `_run_score()`.

**Implementation (5 lines):**
```python
high = len([j for j in get_jobs_to_apply(chat_id, min_score=8)])
if high:
    await msg.reply_text(t(lang_code, "score_high_alert", high=high))
```

### 4.2 Export to CSV

**File:** `bot.py` — new `/export` command

Send all jobs (or only applied) as a `.csv` file. Useful for tracking outside the bot.

```python
import csv, io

@owner_only
async def cmd_export(update, context):
    chat_id = update.effective_chat.id
    rows = get_all_jobs(chat_id)   # new DB function: SELECT * FROM jobs WHERE chat_id=?
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["title", "company", "link", "score", "applied", "city", "tech_stack"])
    writer.writerows(rows)
    await update.message.reply_document(
        document=buf.getvalue().encode("utf-8"),
        filename="jobs_export.csv"
    )
```

### 4.3 `/jobs` pagination

When there are 20+ jobs with score ≥ 7, Telegram floods the chat with cards.
Add pagination: show 5 at a time with a "Show more →" inline button.

```
/jobs → shows cards 1–5
        [Show more →]  ← callback: action:jobs_page:1
```

Store `offset` in callback data: `action:jobs_page:5`, `action:jobs_page:10`, etc.

### 4.4 Scheduled auto-scrape

**File:** new `scheduler.py` or APScheduler integration in `main.py`

Run scrape + score automatically once a day (e.g. at 09:00) for each user who has a resume.
Notify only if new jobs with score ≥ 7 are found.

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()
scheduler.add_job(daily_scrape_all_users, "cron", hour=9)
scheduler.start()
```

This turns the bot from a tool you have to remember to use into a proactive assistant.

### 4.5 Application tracking follow-up

After marking a job as "Applied ✅", bot sends a follow-up message 7 days later:
"Any news from Addepto? Mark as: [Got interview] [Rejected] [No reply]"

Adds `applied_at TIMESTAMP` and `outcome TEXT` columns to `jobs`.
Scheduler checks daily for applications older than 7 days without an outcome.

---

## Priority 5 — Web dashboard (Stage 3)

**Trigger:** after stable multi-user flow on Railway.

- **FastAPI backend** — expose `/api/jobs`, `/api/stats`, `/api/resume` endpoints
- **Simple HTML frontend** — job list with score bars, apply/skip buttons, resume upload form
- **Auth** — Telegram Login Widget (users log in with the same Telegram account as the bot)
- **Stripe integration** — free tier (20 scrapes/month) + paid tier (unlimited)

No need to build this now. The DB schema is already ready — every table has `chat_id`.

---

## Done ✓

- ~~Replace SerpAPI with JustJoin.it~~ — single GET, no key, no quota
- ~~Migrate scraper from JustJoin.it to Adzuna API~~ — JustJoin closed public API
- ~~Add multiple job sources~~ — Adzuna + NoFluffJobs + Remotive
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
- ~~Add multilingual support (EN/RU/PL) with inline language picker~~
- ~~Add inline city quick-pick buttons in `/scrape`~~
- ~~Show job description in cards instead of cover letter preview~~
- ~~Add `chat_id` to all DB functions and queries~~
- ~~Store resume in DB (`user_settings.resume_text`) — no file dependency~~
- ~~Replace singleton `conn`/`cursor` with connection pool~~
- ~~Replace Groq → Anthropic Claude API (Haiku for scoring, Sonnet for letters)~~
- ~~Migrate SQLite → PostgreSQL (psycopg2, ThreadedConnectionPool, %s placeholders)~~
