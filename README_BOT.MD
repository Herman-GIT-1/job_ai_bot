# Job Search Bot 🤖

Автоматизированный поиск стажировок: собирает вакансии через SerpAPI, оценивает их через AI, генерирует cover letter и уведомляет через Telegram.

## Установка

```bash
pip install requests groq python-dotenv python-telegram-bot pypdf python-docx
```

## Настройка

Создай файл `.env` в корне проекта (`.env.example` есть в репозитории):

```env
GROQ_API_KEY=your_groq_api_key_here
SERPAPI_KEY=your_serpapi_key_here
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here
```

| Переменная | Где получить |
|---|---|
| `GROQ_API_KEY` | console.groq.com → API Keys |
| `SERPAPI_KEY` | serpapi.com → Dashboard (100 запросов/месяц бесплатно) |
| `TELEGRAM_BOT_TOKEN` | @BotFather в Telegram |
| `TELEGRAM_CHAT_ID` | @userinfobot в Telegram |

## Запуск

```bash
python main.py --scrape   # найти вакансии и сохранить в БД
python main.py --score    # AI-оценка + генерация cover letter
python main.py --apply    # открыть лучшие вакансии (score >= 7) в браузере
python main.py --bot      # запустить Telegram-бот
python main.py --all      # scrape + score + apply последовательно

# Команды Telegram-бота:
# /resume        — показать текущее резюме
# /scrape        — запустить поиск вакансий прямо из бота
# /jobs          — вакансии с оценкой ≥ 7 с кнопками Подать / Пропустить
# /stats         — статистика базы
# <файл>         — отправь .txt / .pdf / .docx чтобы обновить резюме
```

## Как работает

```
SerpAPI (Google Jobs) → scraper.py → database.py (SQLite)
                                           ↓
                                    ai_score.py (Groq)
                                    cover_letter.py (Groq)
                                           ↓
                              bot.py (Telegram) / open_jobs.py (браузер)
```

`--scrape` выполняет 8 поисковых запросов (junior developer, data analyst и др. по Варшаве) и сохраняет ~50+ уникальных вакансий. Каждый запрос расходует 1 из 100 бесплатных запросов SerpAPI в месяц.
