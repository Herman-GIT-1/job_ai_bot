# NEXT_STEPS.md

Current state: PostgreSQL · multi-user schema · Claude API · Telegram EN/RU/PL · Railway deployed · any-student jobs · application tracker · resume feedback.

---

## Priority 1 — Открытая регистрация

Сейчас бот доступен только владельцу (`owner_only` на всех командах кроме `/stop`).

**Файл:** `bot.py`

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

Добавить `ALLOWED_CHAT_IDS=id1,id2,id3` в `.env` и Railway dashboard.
Когда готов к полному открытию — убрать декоратор совсем.

---

## Priority 2 — UX: score explanation (объяснение скора)

Сейчас бот показывает `⭐ 6/10` без объяснений — студент не понимает что улучшить.

**Ограничение:** пока отложено чтобы не увеличивать расход токенов Haiku.

Когда будет готов к production:

- `ai_score.py`: изменить `max_tokens=5` → `max_tokens=80`, промт возвращает JSON `{"score": 7, "reason": "..."}`
- `database.py`: `ALTER TABLE jobs ADD COLUMN IF NOT EXISTS score_reason TEXT`
- `database.py`: обновить `update_job()` для сохранения reason
- `bot.py`: показывать в карточке под скором

---

## Priority 3 — Scheduled auto-scrape

JobQueue внутри бота — запускать скрейп+скоринг раз в день и присылать дайджест.

**Предупреждение:** APScheduler не работает надёжно на Railway free tier.
Использовать `python-telegram-bot` `JobQueue`:

```python
application.job_queue.run_daily(
    daily_scrape,
    time=datetime.time(hour=9, tzinfo=datetime.timezone.utc)
)
```

Функция `daily_scrape` должна перебирать всех пользователей у которых есть резюме и `last_scrape_at` старше 24h.

---

## Priority 4 — Database backup

Railway free PostgreSQL не делает автоматических бэкапов.

```python
import subprocess
result = subprocess.run(["pg_dump", DATABASE_URL], capture_output=True)
await bot.send_document(chat_id=ADMIN_CHAT_ID, document=result.stdout, filename="backup.sql")
```

Добавить как Railway cron job (отдельно от bot worker).

---

## Priority 5 — Монетизация

Когда будет стабильная пользовательская база:

- **Telegram Payments + Stripe** — пользователь платит прямо в Telegram, без веб-сайта
- Настроить в BotFather → Payments → Stripe (занимает ~15 мин)
- Новая переменная: `STRIPE_PROVIDER_TOKEN`
- Новые колонки в `user_settings`: `plan TEXT DEFAULT 'free'`, `scrapes_this_month INT DEFAULT 0`, `plan_expires_at TIMESTAMPTZ`
- Freemium: 5 скрейпов/месяц бесплатно → unlimited за ~€4.99/мес
- `/upgrade` команда → `send_invoice()` → `successful_payment` handler → `set_user_plan()`

---

## Done ✓

- Multi-user schema с chat_id везде
- PostgreSQL + ThreadedConnectionPool (с rollback на ошибку)
- Prompt caching на resume block (ai_score + cover_letter)
- Три источника вакансий: Adzuna + NoFluffJobs + Remotive
- Telegram bot EN/RU/PL
- Резюме хранится в БД (не файлом)
- Поиск для любых студентов (не только IT) — динамические запросы и категории Remotive
- Расширенный JUNIOR_KEYWORDS + фильтр нерелевантных вакансий
- /rescore команда
- Настраиваемый порог /jobs 6
- Описание вакансии передаётся AI-промтам (полное, без [:1500] cap)
- Source вакансии сохраняется в БД (Adzuna / NoFluffJobs / Remotive)
- Salary данные из Adzuna и NoFluffJobs (salary_min / salary_max / salary_currency)
- Пагинация /jobs (5 вакансий + кнопка "Показать ещё")
- Зарплата отображается в карточке вакансии
- Сопроводительное письмо отправляется текстом (не файлом)
- Таймауты executor: 30s для скоринга, 60s для письма
- /tracker — трекер заявок с группировкой по дате и статусами
- /feedback — AI-анализ резюме (Sonnet): пропущенные навыки, слабые секции, rewrite suggestion
- После загрузки резюме автоматически предлагается выбор города
- save_job возвращает bool (без двойного count_jobs)
- Cooldown 60 мин между /scrape (кроме admin)
- Inline city quick-pick кнопки
- owner_only guard на /stop
