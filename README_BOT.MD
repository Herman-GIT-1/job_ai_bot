# Job Search Bot 🤖

Автоматизированный поиск стажировок: собирает вакансии, оценивает их через AI и генерирует cover letter.

## Как запустить

### 1. Установить зависимости
```bash
pip install requests groq python-dotenv python-telegram-bot
```

### 2. Получить API ключи

**Groq** (бесплатно):
- Зайди на https://console.groq.com
- Sign up → API Keys → Create API Key

**SerpAPI** (100 запросов/месяц бесплатно):
- Зайди на https://serpapi.com
- Sign up → Dashboard → Your API Key

### 3. Создать .env файл

Создай файл `.env` в корне проекта:
```env
GROQ_API_KEY=your_groq_api_key_here
SERPAPI_KEY=your_serpapi_key_here
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here
```

## Переменные окружения

| Переменная | Где получить | Описание |
|---|---|---|
| `GROQ_API_KEY` | console.groq.com | LLM API для оценки вакансий и генерации cover letter |
| `SERPAPI_KEY` | serpapi.com | Поиск вакансий через Google Jobs (100 запросов/месяц бесплатно) |
| `TELEGRAM_BOT_TOKEN` | @BotFather в Telegram | Токен Telegram-бота |
| `TELEGRAM_CHAT_ID` | @userinfobot в Telegram | Твой личный chat ID |

### 4. Запуск

```bash
# Найти вакансии и сохранить в БД
python main.py --scrape

# AI-оценка + генерация cover letter
python main.py --score

# Открыть лучшие вакансии (score >= 7) в браузере
python main.py --apply

# Запустить Telegram-бот
python main.py --bot

# Всё сразу
python main.py --all
```

## Как работает

```
SerpAPI (Google Jobs) → scraper.py → database.py (SQLite)
                                           ↓
                                    ai_score.py (Groq)
                                    cover_letter.py (Groq)
                                           ↓
                                    open_jobs.py → браузер
```

## Источник вакансий

**SerpAPI / Google Jobs** — поиск вакансий через Google Jobs API. 6 поисковых запросов за один `--scrape` (junior developer, data analyst и др. в Варшаве), итого ~50+ уникальных вакансий.