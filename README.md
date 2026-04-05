# Job AI Bot

AI-powered Telegram бот для поиска стажировок и junior IT-позиций в Польше.

Собирает вакансии из нескольких источников, оценивает их через Claude AI на соответствие резюме, генерирует cover letter и открывает swipe-интерфейс в виде Telegram Mini App.

---

## Возможности

- **Поиск вакансий** — Adzuna, NoFluffJobs, Remotive; Claude строит запросы под конкретное резюме
- **AI-оценка** — каждая вакансия получает оценку 0–10 (Haiku, быстро и дёшево)
- **Cover letter** — автоматическая генерация под вакансию + резюме (Sonnet)
- **Swipe Mini App** — карточки прямо в Telegram: влево = пропустить, вправо = сохранить, кнопка = откликнуться
- **Трекер заявок** — `/tracker` с группировкой по дате и статусами (interviewing / rejected / offer)
- **AI-фидбэк резюме** — `/feedback` анализирует слабые места
- **Мультиязычность** — EN / RU / PL, `/language` для переключения
- **Multi-user** — все данные изолированы по `chat_id`

---

## Стек

| Слой | Технология |
|---|---|
| Бот | python-telegram-bot 20+ |
| Web / Mini App | FastAPI + uvicorn (daemon thread) |
| База данных | PostgreSQL · psycopg2 · ThreadedConnectionPool |
| AI — scoring | `claude-haiku-4-5-20251001` |
| AI — letters, queries | `claude-sonnet-4-6` |
| Деплой | Railway (один процесс: бот + веб-сервер) |

---

## Архитектура

```
Telegram (пользователь)
    │
    ├── Команды (/scrape, /score, /jobs, ...)
    │       └── bot.py ──► scraper.py  ──► Adzuna / NoFluffJobs / Remotive
    │                  ──► ai_score.py ──► Claude Haiku
    │                  ──► cover_letter.py ──► Claude Sonnet
    │                  ──► database.py ──► PostgreSQL
    │
    └── /jobs → WebAppInfo кнопка
            └── Mini App (браузер Telegram)
                    ├── GET  /app          → static/index.html
                    ├── GET  /api/jobs     → JSON вакансий (HMAC auth)
                    ├── POST /api/skip     → applied=2
                    ├── POST /api/save     → applied=3 (сохранено)
                    └── POST /api/apply    → applied=1

main.py --bot
    ├── thread: uvicorn webapp.py (port $PORT)
    └── bot.main() — Telegram polling
```

---

## Установка и запуск локально

### 1. Клонировать и установить зависимости

```bash
git clone https://github.com/Herman-GIT-1/job_ai_bot
cd job_ai_bot
pip install -r requirements.txt
```

### 2. Создать `.env`

```env
ANTHROPIC_API_KEY=sk-ant-...
DATABASE_URL=postgresql://postgres:pass@localhost:5432/job_bot
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...

# Опционально
ADZUNA_APP_ID=...
ADZUNA_APP_KEY=...
WEBAPP_URL=https://your-service.railway.app
```

### 3. Запустить

```bash
# Только Telegram-бот (+ Mini App сервер на localhost:8000)
python main.py --bot

# CLI-режим (без Telegram)
python main.py --scrape --city Warsaw
python main.py --score
python main.py --all
```

---

## Переменные окружения

| Переменная | Обязательная | Описание |
|---|---|---|
| `ANTHROPIC_API_KEY` | Да | [console.anthropic.com](https://console.anthropic.com) → API Keys |
| `DATABASE_URL` | Да | Railway подставляет автоматически; локально — строка подключения psycopg2 |
| `TELEGRAM_BOT_TOKEN` | Бот-режим | @BotFather |
| `TELEGRAM_CHAT_ID` | Бот-режим | @userinfobot — числовой ID |
| `ADZUNA_APP_ID` | Нет | [developer.adzuna.com](https://developer.adzuna.com) — без него источник пропускается |
| `ADZUNA_APP_KEY` | Нет | То же |
| `WEBAPP_URL` | Нет | Полный URL сервиса (например `https://xyz.railway.app`). При заданном значении `/jobs` открывает Mini App вместо сообщений в чате |
| `PORT` | Нет | Порт uvicorn (Railway подставляет, иначе 8000) |

---

## Команды бота

| Команда | Действие |
|---|---|
| `/start` | Приветствие; предлагает загрузить резюме |
| `<файл>` | Загрузить резюме (.txt / .pdf / .docx) |
| `/resume` | Показать текущее резюме |
| `/feedback` | AI-анализ резюме: пропущенные навыки, слабые секции |
| `/scrape` | Найти вакансии (спросит город) |
| `/score` | AI-оценка + генерация cover letter |
| `/rescore` | Сбросить оценки и переоценить заново |
| `/jobs` | Открыть Mini App (если `WEBAPP_URL` задан) или показать карточки в чате |
| `/tracker` | Трекер заявок с группировкой: сегодня / неделя / 2+ недели |
| `/stats` | Статистика: найдено, оценено, подано, пропущено, сохранено |
| `/language` | Сменить язык (EN / RU / PL) |
| `/stop` | Остановить бота (только admin) |

---

## Telegram Mini App

`/jobs` → кнопка **🃏 Смотреть вакансии** открывает браузер Telegram с интерфейсом на картах.

**Жесты:**
- Свайп влево — пропустить вакансию
- Свайп вправо — сохранить в "Мой список"
- Кнопка **✅ Apply** — открывает ссылку на вакансию и отмечает как поданную

**Аутентификация:** Mini App передаёт `initData` в заголовке `Authorization: tma <initData>`. Сервер верифицирует подпись через `HMAC-SHA256(key="WebAppData", msg=BOT_TOKEN)`.

---

## Статусы вакансий

| `applied` | `job_status` | Значение |
|---|---|---|
| 0 | `pending` | Новая, ожидает оценки или просмотра |
| 1 | `applied` | Откликнулся |
| 2 | `skipped` | Пропущена |
| 3 | `interested` | Сохранена в "Мой список" (Mini App) |
| 1 | `interviewing` | Есть собеседование |
| 1 | `rejected` | Отказ |
| 1 | `offer` | Получен оффер |

---

## Деплой на Railway

1. Подключить репозиторий в Railway
2. Добавить сервис PostgreSQL (Railway Dashboard → Add Service)
3. Задать переменные окружения (см. таблицу выше)
4. Railway использует `Procfile`:
   ```
   worker: python main.py --bot
   ```
5. После деплоя скопировать публичный URL сервиса в `WEBAPP_URL`

---

## Структура проекта

```
job_ai_bot/
├── main.py            # CLI + запуск бота + uvicorn thread
├── bot.py             # Telegram handlers
├── webapp.py          # FastAPI Mini App сервер
├── static/
│   └── index.html     # Mini App фронтенд (swipe UI)
├── database.py        # PostgreSQL layer (все функции принимают chat_id)
├── scraper.py         # Парсеры: Adzuna, NoFluffJobs, Remotive
├── ai_score.py        # Оценка вакансий (Haiku)
├── cover_letter.py    # Генерация письма (Sonnet)
├── resume_feedback.py # Анализ резюме (Sonnet)
├── resume_parser.py   # Парсинг .txt/.pdf/.docx
├── config.py          # Централизованные константы + WEBAPP_URL
├── strings.py         # i18n: EN/RU/PL
├── open_jobs.py       # CLI: открыть вакансии в браузере
├── Procfile           # Railway: worker process
└── .claude/
    └── rules/         # Правила для AI-ассистента
```
