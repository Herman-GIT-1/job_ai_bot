# Job Search Bot 🤖

Автоматизированный поиск стажировок: собирает вакансии с JustJoin.it, оценивает их через AI, генерирует cover letter и уведомляет через Telegram.

## Установка

```bash
pip install -r requirements.txt
```

## Настройка

Создай файл `.env` в корне проекта (`.env.example` есть в репозитории):

```env
GROQ_API_KEY=your_groq_api_key_here
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here
```

| Переменная | Где получить |
|---|---|
| `GROQ_API_KEY` | console.groq.com → API Keys |
| `TELEGRAM_BOT_TOKEN` | @BotFather в Telegram |
| `TELEGRAM_CHAT_ID` | @userinfobot в Telegram |

## Запуск

```bash
python main.py --scrape   # найти вакансии и сохранить в БД
python main.py --score    # AI-оценка + генерация cover letter
python main.py --apply    # открыть лучшие вакансии (score >= 7) в браузере
python main.py --bot      # запустить Telegram-бот
python main.py --all      # scrape + score + apply последовательно
```

## Команды Telegram-бота

| Команда | Действие |
|---|---|
| `/start` | Приветствие и список команд |
| `/resume` | Показать текущее резюме (первые 600 символов) |
| `/scrape` | Найти новые вакансии (спросит город) |
| `/score` | AI-оценка + cover letter для всех новых вакансий |
| `/jobs` | Вакансии с оценкой ≥ 7, кнопки: Подать / Пропустить / Письмо |
| `/stats` | Статистика: найдено, оценено, подано, пропущено |
| `/stop` | Остановить бота |
| `<файл>` | Загрузить резюме (.txt / .pdf / .docx) |

При нажатии **Письмо 📄** бот отправляет cover letter как `.txt` файл, не меняя статус вакансии.

## Как работает

```
JustJoin.it API → scraper.py → database.py (SQLite)
                                      ↓
                           ai_score.py + cover_letter.py (Groq)
                                      ↓
                           bot.py (Telegram) / open_jobs.py (браузер)
```

- `/scrape` делает один GET-запрос к JustJoin.it, фильтрует по городу и уровню (junior/intern), сохраняет в `jobs.db` — без ключей и квот
- `/score` оценивает каждую новую вакансию (0–10) и генерирует cover letter
- `/jobs` показывает вакансии с оценкой ≥ 7, не отмеченные как поданные или пропущенные
