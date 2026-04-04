# NEXT_STEPS.md

Current state (Apr 2026): PostgreSQL · multi-user · Claude API · Telegram EN/RU/PL · Railway · 3 job sources (Adzuna/NoFluffJobs/Remotive) · application tracker · resume feedback · salary data · pagination · cooldown.

---

## Wave 1 — Foundation (1–2 weeks)

### P1 · Открытая регистрация

Сейчас все команды ограничены одним владельцем (`admin_only` на `/stop`).

**bot.py** — добавить whitelist-декоратор:

```python
ALLOWED = set(int(x) for x in os.getenv("ALLOWED_CHAT_IDS", "").split(",") if x)

def allowed(func):
    @functools.wraps(func)
    async def wrapper(update, context):
        if update.effective_chat.id not in ALLOWED:
            await update.message.reply_text(t("en", "access_denied"))
            return
        return await func(update, context)
    return wrapper
```

Добавить `ALLOWED_CHAT_IDS=id1,id2,id3` в `.env` и Railway dashboard.
Когда готов к полному open — убрать декоратор совсем.

---

### P2 · Score explanation (объяснение скора)

Сейчас бот показывает `7/10` без объяснений — пользователь не понимает что улучшить.

- **`ai_score.py`**: `max_tokens=5 → 80`, промт возвращает JSON `{"score": 7, "reason": "strong Python match, missing Docker"}`
- **`database.py`**: `ALTER TABLE jobs ADD COLUMN IF NOT EXISTS score_reason TEXT`
- **`database.py`**: обновить `update_job(job_id, chat_id, score, letter, reason)` 
- **`bot.py`**: показывать reason курсивом под скором в карточке вакансии

Ограничение: пока отложено, чтобы не увеличивать расход Haiku-токенов.

---

### P3 · Database backup

Railway free PostgreSQL не делает автобэкапов.

- Новый файл **`backup.py`** (≤ 30 строк):
  ```python
  result = subprocess.run(["pg_dump", DATABASE_URL], capture_output=True)
  # gzip + send_document(ADMIN_CHAT_ID, filename="backup_YYYY-MM-DD.sql.gz")
  ```
- Запуск: Railway cron job в 3:00 UTC ежедневно (отдельно от bot worker)

---

### P4 · Error monitoring → Admin chat

- Добавить `error_handler` в **`bot.py`** (PTB `application.add_error_handler`)
- Все необработанные исключения слать в `ADMIN_CHAT_ID` с трейсбеком
- Без внешних сервисов (Sentry платный)

---

## Wave 2 — Growth (1 month)

### P5 · Daily auto-scrape digest

- **`bot.py`**: `application.job_queue.run_daily()` в 9:00 UTC
- Перебирать пользователей у кого есть резюме + `last_scrape_at > 24h` (запрос в `database.py`)
- Присылать дайджест: "Найдено X вакансий, Y подходят (score ≥ 7)"
- Inline-кнопка "Смотреть вакансии" → триггерит `/jobs`

Предупреждение: APScheduler нестабилен на Railway free. Только PTB JobQueue.

---

### P6 · Новые источники вакансий

**Pracuj.pl** — крупнейший польский job-портал, без API-ключа:
- `_fetch_pracujpl(city)` в **`scraper.py`**
- Фильтр: seniority "Junior / Praktykant / Stażysta" в параметрах запроса

**Just Join IT** (justjoin.it) — IT-нишевый портал Польши, open API:
- `_fetch_justjoinit(city)` в **`scraper.py`**
- Содержит salary по умолчанию → хорошие данные для `salary_min/max`

Оба источника: обернуть в `try/except`, `return []` при ошибке (правило `api.md`).
Вызвать внутри `search_jobs()` через `raw.extend(...)`.

---

### P7 · Blacklist компаний

- **`database.py`**: `ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS blacklisted_companies TEXT DEFAULT ''`
- **`bot.py`**: команда `/blacklist <company>` — добавить, `/blacklist list` — показать, `/blacklist clear` — очистить
- **`scraper.py`**: фильтр после дедупликации — убирать вакансии от компаний из blacklist пользователя

---

### P8 · Job expiry cleanup

- **`database.py`**: `ALTER TABLE jobs ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW()`
- Railway cron (или PTB JobQueue раз в сутки):
  ```sql
  DELETE FROM jobs WHERE applied = 0 AND score IS NULL
  AND created_at < NOW() - INTERVAL '30 days'
  ```
- Предотвращает бесконечный рост таблицы у активных пользователей

---

## Wave 3 — Product (2–3 months)

### P9 · Монетизация (Telegram Payments + Stripe)

- BotFather → Payments → Stripe → получить `STRIPE_PROVIDER_TOKEN`
- **`database.py`**: новые колонки в `user_settings`:
  `plan TEXT DEFAULT 'free'`, `scrapes_this_month INT DEFAULT 0`, `plan_expires_at TIMESTAMPTZ`
- Freemium: 5 скрейпов/месяц бесплатно → unlimited за **€4.99/мес**
- **`bot.py`**: `/upgrade` → `send_invoice()` → `PreCheckoutQueryHandler` → `successful_payment` → `set_user_plan()`
- Сброс `scrapes_this_month` в 1-е число месяца (Railway cron)

---

### P10 · Несколько резюме (профили)

- **`database.py`**: новая таблица:
  ```sql
  CREATE TABLE resumes (
      id        BIGSERIAL PRIMARY KEY,
      chat_id   BIGINT NOT NULL,
      name      TEXT NOT NULL,
      resume_text TEXT NOT NULL,
      created_at TIMESTAMPTZ DEFAULT NOW()
  )
  ```
- `user_settings.active_resume_id BIGINT REFERENCES resumes(id)`
- **`bot.py`**: `/resume add <name>` — загрузить, `/resume switch <name>` — активировать, `/resume list` — список профилей
- Позволяет иметь отдельные резюме для IT / Marketing / Finance направлений

---

### P11 · Расширение на новые страны

- `CITIES` в **`bot.py`**: добавить `London`, `Berlin`, `Amsterdam` (уже `Remote` есть)
- **`scraper.py`**: Adzuna поддерживает `gb`, `de`, `nl` — определять country по городу
- NoFluffJobs пропускать для не-польских городов (только PL)
- Remotive уже глобальный (remote-only) — работает везде

---

### P12 · Web dashboard (минимальный)

- **Новый файл `dashboard.py`**: FastAPI (≤ 200 строк) + Jinja2
- Авторизация через Telegram Login Widget (OAuth, без пароля)
- Страницы: My Jobs (таблица со скорами), Tracker (kanban: pending/applied/interviewing/offer), Stats
- Деплой: второй Railway сервис, тот же PostgreSQL

---

## Wave 4 — Scale (3+ months)

### P13 · Расширенная аналитика пользователя

- `/stats` — добавить: conversion rate (applied / total scored), avg score by source, best job source
- ASCII-график скоров по неделям (не требует внешних библиотек)

---

### P14 · Реферальная система

- `user_settings.referral_code TEXT UNIQUE` — генерировать при первом `/start`
- `/refer` — показать `t.me/<bot>?start=REF_<code>`
- При оплате Pro: проверить реферера → подарить 1 месяц Pro рефереру
- **`database.py`**: `referred_by BIGINT` в `user_settings`

---

### P15 · Кастомизация cover letter

- `user_settings.letter_tone TEXT DEFAULT 'formal'` (formal / casual / creative)
- **`bot.py`**: inline-кнопки выбора тона в `/help` или отдельная `/settings` команда
- **`cover_letter.py`**: `generate_letter(job, resume, tone="formal")` — тон в промт

---

## Done ✓

- Multi-user schema с `chat_id` везде
- PostgreSQL + ThreadedConnectionPool (с rollback на ошибку)
- Prompt caching на resume block (`ai_score` + `cover_letter`)
- Три источника вакансий: Adzuna + NoFluffJobs + Remotive
- Telegram bot EN/RU/PL (strings.py)
- Резюме хранится в БД (не файлом)
- Динамические AI-запросы из резюме (build_queries → Claude Sonnet)
- Расширенный JUNIOR_KEYWORDS + фильтр нерелевантных вакансий
- `/rescore` команда
- Настраиваемый порог `/jobs 6`
- Source вакансии в БД (Adzuna / NoFluffJobs / Remotive)
- Salary данные (salary_min / salary_max / salary_currency)
- Salary отображается в карточке вакансии
- Пагинация `/jobs` (5 вакансий + кнопка "Показать ещё")
- Сопроводительное письмо текстом (не файлом)
- Таймауты executor: 30s scoring, 60s cover letter, 60s feedback
- `/tracker` — трекер заявок с группировкой по дате и статусами (pending/applied/interviewing/rejected/offer)
- `/feedback` — AI-анализ резюме (Sonnet): пропущенные навыки, слабые секции
- После загрузки резюме автоматически предлагается выбор города
- `save_job()` возвращает bool
- Cooldown 60 мин между `/scrape` (кроме admin)
- Inline city quick-pick кнопки
- `admin_only` guard на `/stop`
- `load_dotenv()` первой строкой в `main.py` и `bot.py` (до всех импортов)
- `_get_conn()` с rollback при исключении
- `applied_at TIMESTAMPTZ`, `job_status`, `created_at` колонки в `jobs`
- `last_scrape_at` в `user_settings`
