"""
UI strings for all supported languages.
Usage: t(lang, "key")  or  t(lang, "key", var=value)
"""

TEXTS: dict[str, dict[str, str]] = {
    "en": {
        # --- onboarding ---
        "start_no_resume": (
            "Hi! I find internships and junior IT positions in Poland.\n\n"
            "Send your resume to get started (.txt, .pdf, .docx)."
        ),
        "start_with_resume": (
            "Hi! Resume already loaded.\n\n"
            "/scrape — find jobs (will ask for a city)\n"
            "/score — score found jobs with AI\n"
            "/jobs — show jobs with score ≥ 7\n"
            "/resume — view current resume\n"
            "/stats — statistics\n"
            "/language — change language\n"
            "/stop — stop the bot"
        ),
        # --- resume ---
        "resume_not_found": "Resume not found. Send a file (.txt, .pdf, .docx).",
        "resume_show_header": "Current resume ({chars} chars):",
        "resume_unsupported": "Only .txt, .pdf, .docx are supported.",
        "resume_processing": "Processing file…",
        "resume_saved": "Resume saved ✅ ({chars} chars).\nIt will be used on the next /scrape and scoring.",
        "resume_error": "Error: {error}",
        "resume_upload_failed": "Could not process file: {error}",
        # --- scrape ---
        "scrape_ask_city": "Which city to search in?\nOr type a custom city name below.\n\n/cancel to abort.",
        "scrape_searching": "Searching for jobs in {city}… ~30 seconds.",
        "scrape_no_resume_hint": (
            "No resume uploaded yet — search will use generic queries.\n"
            "Send a .txt/.pdf/.docx file to get personalised results."
        ),
        "scrape_fallback_warning": (
            "AI query generation failed — search used generic queries.\n"
            "This is temporary; your resume is saved."
        ),
        "scrape_done": "Done. Found: {found}, new in DB: {saved}.",
        "scrape_cancelled": "Search cancelled.",
        # --- scoring ---
        "score_no_resume": "Resume not found. Send a file (.txt, .pdf, .docx) and try again.",
        "score_no_jobs": "No jobs to score. Run /scrape first.",
        "score_progress": "Scoring {done}/{total}…",
        "score_done": "Done. Scored: {total} jobs.",
        "score_high_alert": "⭐ {high} job(s) scored ≥ 8 — tap the button to browse!",
        "score_no_good_jobs": "No jobs met the minimum score threshold. Try /scrape to fetch more.",
        "scrape_cooldown": "Please wait {minutes} min before searching again.",
        "rescore_start": "Scores reset. Re-scoring now…",
        # --- jobs ---
        "jobs_none": "No new jobs with score ≥ {min_score}.",
        "jobs_found": "Jobs found (score ≥ {min_score}): {count}",
        "btn_apply": "Apply ✅",
        "btn_skip": "Skip ❌",
        "btn_letter": "Letter 📄",
        "applied_msg": "Application noted ✅ Open the link below and apply:",
        "btn_open_job": "Open job page 🔗",
        "btn_interviewing": "Got interview! 🤝",
        "btn_rejected": "Rejected ❌",
        "skipped_msg": "Skipped ❌",
        "letter_not_found": "Letter not found.",
        # --- pagination ---
        "jobs_show_more": "Show {remaining} more →",
        "jobs_page_info": "Showing {shown} of {total}",
        # --- onboarding ---
        "onboard_ask_city": "Great! Now choose a city for your first job search:",
        # --- tracker ---
        "tracker_empty": "No applications yet. Use /jobs to find jobs and apply.",
        "tracker_header": "📋 Your applications ({count} total):\n",
        "tracker_today": "Today",
        "tracker_week": "This week",
        "tracker_older": "2+ weeks ago",
        "tracker_followup": "follow up?",
        "status_interviewing": "Marked as interviewing",
        "status_rejected": "Marked as rejected",
        "status_offer": "Offer received!",
        # --- feedback ---
        "feedback_generating": "Analyzing your resume…",
        "feedback_header": "📋 Resume Feedback",
        # --- stats ---
        "stats": (
            "📊 Stats:\n"
            "Total jobs: {total}\n"
            "Scored: {scored}\n"
            "Avg score: {avg}\n"
            "Applied: {applied}\n"
            "Skipped: {skipped}"
        ),
        # --- quick-action buttons ---
        "btn_view_jobs": "📋 View jobs",
        "btn_rescore": "🔄 Re-score",
        "btn_score_now": "🤖 Score now",
        "btn_help": "❓ Help",
        # --- language ---
        "lang_choose": "Choose language:",
        "lang_set": "Language set to English 🇬🇧",
        # --- after language set ---
        "lang_set_next_no_resume": (
            "To get started, send your resume file (.txt, .pdf, .docx).\n"
            "I'll use it to search for relevant jobs and score them."
        ),
        "lang_set_next_has_resume": "Resume already loaded. What would you like to do?",
        # --- help ---
        "help_text": (
            "🤖 Job Bot — Command Reference\n\n"
            "📄 Resume\n"
            "/resume — view current resume\n"
            "/feedback — get AI feedback on your resume\n"
            "Send file — upload (.txt, .pdf, .docx)\n\n"
            "🔍 Search\n"
            "/scrape — search for jobs (asks for city)\n"
            "/cancel — cancel city selection\n\n"
            "⭐ Scoring\n"
            "/score — score all found jobs with AI\n"
            "/rescore — reset scores and re-score\n"
            "/jobs [N] — show jobs with score ≥ N (default 7)\n\n"
            "📊 Info\n"
            "/stats — show statistics\n"
            "/start — welcome message\n\n"
            "⚙️ Settings\n"
            "/language — change language\n"
            "/stop — stop the bot (admin only)"
        ),
        # --- mini app ---
        "webapp_btn": "🃏 Browse Jobs",
        "webapp_open": "Tap the button below to browse jobs with swipe cards:",
        "webapp_not_configured": "Mini App is not configured yet. Use /jobs to see jobs in chat.",
        "interested_msg": "Saved to your list ✅",
        # --- backup ---
        "backup_running": "Creating backup…",
        "backup_done": "Backup sent ✅",
        # --- misc ---
        "access_denied": "Access denied.",
        "stop_msg": "Stopping bot…",
    },

    "ru": {
        "start_no_resume": (
            "Привет! Я нахожу стажировки и junior IT-вакансии в Польше.\n\n"
            "Отправь резюме, чтобы начать (.txt, .pdf, .docx)."
        ),
        "start_with_resume": (
            "Привет! Резюме уже загружено.\n\n"
            "/scrape — найти вакансии (спросит город)\n"
            "/score — оценить вакансии через AI\n"
            "/jobs — показать вакансии с оценкой ≥ 7\n"
            "/resume — показать резюме\n"
            "/stats — статистика\n"
            "/language — сменить язык\n"
            "/stop — остановить бота"
        ),
        "resume_not_found": "Резюме не найдено. Отправь файл (.txt, .pdf, .docx).",
        "resume_show_header": "Текущее резюме ({chars} символов):",
        "resume_unsupported": "Поддерживаются только .txt, .pdf, .docx.",
        "resume_processing": "Обрабатываю файл…",
        "resume_saved": "Резюме сохранено ✅ ({chars} символов).\nБудет использоваться при следующем /scrape.",
        "resume_error": "Ошибка: {error}",
        "resume_upload_failed": "Не удалось обработать файл: {error}",
        "scrape_ask_city": "В каком городе искать?\nИли введи название города вручную.\n\n/cancel — отменить.",
        "scrape_searching": "Ищу вакансии в {city}… ~30 секунд.",
        "scrape_no_resume_hint": (
            "Резюме ещё не загружено — поиск будет выполнен по базовым запросам.\n"
            "Отправь файл .txt/.pdf/.docx чтобы получить персональные результаты."
        ),
        "scrape_fallback_warning": (
            "AI не смог сформировать запросы — поиск выполнен по базовым запросам.\n"
            "Это временная ошибка, твоё резюме сохранено."
        ),
        "scrape_done": "Готово. Найдено: {found}, новых в базе: {saved}.",
        "scrape_cancelled": "Поиск отменён.",
        "score_no_resume": "Резюме не найдено. Отправь файл (.txt, .pdf, .docx) и повтори.",
        "score_no_jobs": "Нет вакансий для оценки. Сначала запусти /scrape.",
        "score_progress": "Оцениваю {done}/{total}…",
        "score_done": "Готово. Оценено вакансий: {total}.",
        "score_high_alert": "⭐ {high} вакансий с оценкой ≥ 8 — нажми кнопку, чтобы открыть!",
        "score_no_good_jobs": "Ни одна вакансия не прошла минимальный порог оценки. Попробуй /scrape.",
        "scrape_cooldown": "Подожди ещё {minutes} мин. перед следующим поиском.",
        "rescore_start": "Оценки сброшены. Запускаю оценку заново…",
        "jobs_none": "Нет новых вакансий с оценкой ≥ {min_score}.",
        "jobs_found": "Найдено вакансий (score ≥ {min_score}): {count}",
        "btn_apply": "Подать ✅",
        "btn_skip": "Пропустить ❌",
        "btn_letter": "Письмо 📄",
        "applied_msg": "Заявка отмечена ✅ Открой ссылку и подай заявку:",
        "btn_open_job": "Открыть вакансию 🔗",
        "btn_interviewing": "Собеседование! 🤝",
        "btn_rejected": "Отказ ❌",
        "skipped_msg": "Пропущено ❌",
        "letter_not_found": "Письмо не найдено.",
        "jobs_show_more": "Показать ещё {remaining} →",
        "jobs_page_info": "Показано {shown} из {total}",
        "onboard_ask_city": "Отлично! Теперь выбери город для первого поиска:",
        "tracker_empty": "Заявок пока нет. Используй /jobs чтобы найти вакансии.",
        "tracker_header": "📋 Твои заявки ({count} всего):\n",
        "tracker_today": "Сегодня",
        "tracker_week": "На этой неделе",
        "tracker_older": "2+ недели назад",
        "tracker_followup": "написать follow-up?",
        "status_interviewing": "Отмечено: собеседование",
        "status_rejected": "Отмечено: отказ",
        "status_offer": "Оффер получен!",
        "feedback_generating": "Анализирую резюме…",
        "feedback_header": "📋 Анализ резюме",
        "stats": (
            "📊 Статистика:\n"
            "Всего вакансий: {total}\n"
            "Оценено: {scored}\n"
            "Средний score: {avg}\n"
            "Подано заявок: {applied}\n"
            "Пропущено: {skipped}"
        ),
        "btn_view_jobs": "📋 Смотреть вакансии",
        "btn_rescore": "🔄 Переоценить",
        "btn_score_now": "🤖 Оценить сейчас",
        "btn_help": "❓ Помощь",
        "lang_choose": "Выбери язык:",
        "lang_set": "Язык изменён на Русский 🇷🇺",
        # --- after language set ---
        "lang_set_next_no_resume": (
            "Для начала отправь файл с резюме (.txt, .pdf, .docx).\n"
            "Я использую его для поиска подходящих вакансий и их оценки."
        ),
        "lang_set_next_has_resume": "Резюме уже загружено. Что делать дальше?",
        # --- help ---
        "help_text": (
            "🤖 Job Bot — Список команд\n\n"
            "📄 Резюме\n"
            "/resume — посмотреть текущее резюме\n"
            "/feedback — получить AI-анализ резюме\n"
            "Отправить файл — загрузить (.txt, .pdf, .docx)\n\n"
            "🔍 Поиск\n"
            "/scrape — искать вакансии (спросит город)\n"
            "/cancel — отменить выбор города\n\n"
            "⭐ Оценка\n"
            "/score — оценить все найденные вакансии через AI\n"
            "/rescore — сбросить оценки и переоценить\n"
            "/jobs [N] — показать вакансии с оценкой ≥ N (по умолчанию 7)\n\n"
            "📊 Информация\n"
            "/stats — статистика\n"
            "/start — приветственное сообщение\n\n"
            "⚙️ Настройки\n"
            "/language — сменить язык\n"
            "/stop — остановить бота (только admin)"
        ),
        # --- mini app ---
        "webapp_btn": "🃏 Смотреть вакансии",
        "webapp_open": "Нажми кнопку ниже, чтобы листать вакансии карточками:",
        "webapp_not_configured": "Mini App ещё не настроен. Используй /jobs для просмотра в чате.",
        "interested_msg": "Сохранено в список ✅",
        # --- backup ---
        "backup_running": "Создаю резервную копию…",
        "backup_done": "Резервная копия отправлена ✅",
        "access_denied": "Доступ запрещён.",
        "stop_msg": "Останавливаю бота…",
    },

    "pl": {
        "start_no_resume": (
            "Cześć! Szukam staży i ofert junior IT w Polsce.\n\n"
            "Wyślij swoje CV, żeby zacząć (.txt, .pdf, .docx)."
        ),
        "start_with_resume": (
            "Cześć! CV już wgrane.\n\n"
            "/scrape — znajdź oferty (zapyta o miasto)\n"
            "/score — ocen oferty przez AI\n"
            "/jobs — pokaż oferty z oceną ≥ 7\n"
            "/resume — pokaż aktualne CV\n"
            "/stats — statystyki\n"
            "/language — zmień język\n"
            "/stop — zatrzymaj bota"
        ),
        "resume_not_found": "CV nie znalezione. Wyślij plik (.txt, .pdf, .docx).",
        "resume_show_header": "Aktualne CV ({chars} znaków):",
        "resume_unsupported": "Obsługiwane tylko .txt, .pdf, .docx.",
        "resume_processing": "Przetwarzam plik…",
        "resume_saved": "CV zapisane ✅ ({chars} znaków).\nBędzie używane przy następnym /scrape.",
        "resume_error": "Błąd: {error}",
        "resume_upload_failed": "Nie udało się przetworzyć pliku: {error}",
        "scrape_ask_city": "W jakim mieście szukać?\nMożesz też wpisać nazwę miasta ręcznie.\n\n/cancel — anuluj.",
        "scrape_searching": "Szukam ofert w {city}… ~30 sekund.",
        "scrape_no_resume_hint": (
            "Brak CV — wyszukiwanie z podstawowymi zapytaniami.\n"
            "Wyślij plik .txt/.pdf/.docx aby uzyskać spersonalizowane wyniki."
        ),
        "scrape_fallback_warning": (
            "AI nie mógł wygenerować zapytań — użyto podstawowych.\n"
            "To tymczasowy błąd, Twoje CV jest zapisane."
        ),
        "scrape_done": "Gotowe. Znalezione: {found}, nowych w bazie: {saved}.",
        "scrape_cancelled": "Wyszukiwanie anulowane.",
        "score_no_resume": "CV nie znalezione. Wyślij plik (.txt, .pdf, .docx) i spróbuj ponownie.",
        "score_no_jobs": "Brak ofert do oceny. Najpierw uruchom /scrape.",
        "score_progress": "Oceniam {done}/{total}…",
        "score_done": "Gotowe. Oceniono ofert: {total}.",
        "score_high_alert": "⭐ {high} ofert z oceną ≥ 8 — naciśnij przycisk, aby przeglądać!",
        "score_no_good_jobs": "Żadna oferta nie spełniła minimalnego progu. Spróbuj /scrape.",
        "scrape_cooldown": "Poczekaj jeszcze {minutes} min. przed następnym wyszukiwaniem.",
        "rescore_start": "Oceny zresetowane. Ponowna ocena…",
        "jobs_none": "Brak nowych ofert z oceną ≥ {min_score}.",
        "jobs_found": "Znalezione oferty (ocena ≥ {min_score}): {count}",
        "btn_apply": "Aplikuj ✅",
        "btn_skip": "Pomiń ❌",
        "btn_letter": "List 📄",
        "applied_msg": "Aplikacja zaznaczona ✅ Otwórz link i złóż aplikację:",
        "btn_open_job": "Otwórz ofertę 🔗",
        "btn_interviewing": "Rozmowa rekrutacyjna! 🤝",
        "btn_rejected": "Odmowa ❌",
        "skipped_msg": "Pominięto ❌",
        "letter_not_found": "List nie znaleziony.",
        "jobs_show_more": "Pokaż {remaining} więcej →",
        "jobs_page_info": "Pokazano {shown} z {total}",
        "onboard_ask_city": "Świetnie! Wybierz miasto do pierwszego wyszukiwania:",
        "tracker_empty": "Brak aplikacji. Użyj /jobs żeby znaleźć oferty.",
        "tracker_header": "📋 Twoje aplikacje ({count} łącznie):\n",
        "tracker_today": "Dzisiaj",
        "tracker_week": "W tym tygodniu",
        "tracker_older": "2+ tygodnie temu",
        "tracker_followup": "napisać follow-up?",
        "status_interviewing": "Zaznaczono: rozmowa rekrutacyjna",
        "status_rejected": "Zaznaczono: odmowa",
        "status_offer": "Oferta otrzymana!",
        "feedback_generating": "Analizuję CV…",
        "feedback_header": "📋 Analiza CV",
        "stats": (
            "📊 Statystyki:\n"
            "Wszystkich ofert: {total}\n"
            "Ocenionych: {scored}\n"
            "Średnia ocena: {avg}\n"
            "Złożono aplikacji: {applied}\n"
            "Pominiętych: {skipped}"
        ),
        "btn_view_jobs": "📋 Pokaż oferty",
        "btn_rescore": "🔄 Oceń ponownie",
        "btn_score_now": "🤖 Oceń teraz",
        "btn_help": "❓ Pomoc",
        "lang_choose": "Wybierz język:",
        "lang_set": "Język zmieniony na Polski 🇵🇱",
        # --- after language set ---
        "lang_set_next_no_resume": (
            "Na start wyślij plik CV (.txt, .pdf, .docx).\n"
            "Użyję go do wyszukiwania i oceny ofert pracy."
        ),
        "lang_set_next_has_resume": "CV już wgrane. Co chcesz zrobić?",
        # --- help ---
        "help_text": (
            "🤖 Job Bot — Lista komend\n\n"
            "📄 CV\n"
            "/resume — sprawdź aktualne CV\n"
            "/feedback — analiza CV przez AI\n"
            "Wyślij plik — wgraj (.txt, .pdf, .docx)\n\n"
            "🔍 Wyszukiwanie\n"
            "/scrape — szukaj ofert (zapyta o miasto)\n"
            "/cancel — anuluj wybór miasta\n\n"
            "⭐ Ocenianie\n"
            "/score — oceń oferty przez AI\n"
            "/rescore — zresetuj oceny i oceń ponownie\n"
            "/jobs [N] — pokaż oferty z oceną ≥ N (domyślnie 7)\n\n"
            "📊 Informacje\n"
            "/stats — statystyki\n"
            "/start — wiadomość powitalna\n\n"
            "⚙️ Ustawienia\n"
            "/language — zmień język\n"
            "/stop — zatrzymaj bota (tylko admin)"
        ),
        # --- mini app ---
        "webapp_btn": "🃏 Przeglądaj oferty",
        "webapp_open": "Kliknij przycisk poniżej, aby przeglądać oferty kartami:",
        "webapp_not_configured": "Mini App nie jest jeszcze skonfigurowany. Użyj /jobs aby zobaczyć oferty w czacie.",
        "interested_msg": "Zapisano do listy ✅",
        # --- backup ---
        "backup_running": "Tworzę kopię zapasową…",
        "backup_done": "Kopia zapasowa wysłana ✅",
        "access_denied": "Brak dostępu.",
        "stop_msg": "Zatrzymuję bota…",
    },
}


def t(lang: str, key: str, **kw) -> str:
    """Return translated string for lang+key, falling back to English."""
    text = TEXTS.get(lang, {}).get(key) or TEXTS["en"].get(key, key)
    return text.format(**kw) if kw else text
