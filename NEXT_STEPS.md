# NEXT_STEPS.md

Current state (Apr 2026): PostgreSQL · multi-user · Claude API · Telegram EN/RU/PL · Railway · 3 job sources (Adzuna/NoFluffJobs/Remotive) · application tracker · resume feedback · salary data · pagination · cooldown · Telegram Mini App swipe UI.

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

### P2 · Score explanation (объяснение скора) ✓ Done

- **`ai_score.py`**: `max_tokens=5 → 80`; промт возвращает JSON `{"score": 7, "reason": "..."}`;
  `evaluate()` теперь возвращает `tuple[int, str]`
- **`database.py`**: `score_reason TEXT` колонка; `update_job()` принимает `reason` param
- **`bot.py`**: распаковка `(score, reason)`; reason отображается курсивом под score в карточке

---

### P3 · Database backup ✓ Done

- **`backup.py`**: `pg_dump` → gzip → `send_document(ADMIN_CHAT_ID)`; запускается как скрипт
- **`bot.py`**: команда `/backup` (admin_only) — ручной запуск резервной копии
- Для автоматического запуска: Railway cron job → `python backup.py` в 3:00 UTC

---

### P4 · Error monitoring → Admin chat ✓ Done

- `_error_handler` в **`bot.py`** пересылает трейсбек в `ADMIN_CHAT_ID` (truncated 3000 chars)
- Benign ошибки (Conflict, NetworkError) только логируются, не пересылаются

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

### P12 · Расширить Mini App — страница "Мой список"

Mini App уже есть (swipe-карточки, `applied=3`). Следующий шаг — показывать сохранённые вакансии прямо в webapp.

- **`webapp.py`**: новый роут `GET /api/saved` → `get_interested_jobs(chat_id)`
- **`static/index.html`**: вкладки "Карточки" / "Мой список" в хедере
- Вкладка "Мой список": скролл-список карточек с кнопками "Откликнуться 🔗" и "Убрать ❌"
- Убрать = `POST /api/skip` (перевод обратно в `applied=2`)

Зависимость: нужен `WEBAPP_URL` на Railway (уже поддерживается).

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
- Job expiry cleanup: `delete_expired_jobs()` + PTB daily job queue (P8)
- Score explanation: `evaluate()` → `(score, reason)`, reason в карточке курсивом (P2)
- `/backup` admin-команда: pg_dump → gzip → Telegram document (P3)
- Error monitoring: unhandled exceptions → ADMIN_CHAT_ID с трейсбеком (P4)
- **Telegram Mini App** (`webapp.py` + `static/index.html`):
  - FastAPI сервер запускается в daemon-треде внутри одного Railway-процесса
  - HMAC-SHA256 аутентификация через Telegram initData
  - Swipe-карточки: влево = skip, вправо = save (📋), кнопка = apply
  - `applied = 3` (interested/saved) — новый статус в БД
  - `mark_interested()` + `get_interested_jobs()` в `database.py`
  - `/jobs` открывает Mini App кнопкой если `WEBAPP_URL` задан, иначе старый режим
  - Strings в EN/RU/PL: `webapp_btn`, `webapp_open`, `webapp_not_configured`, `interested_msg`
