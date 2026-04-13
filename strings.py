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
            "/jobs — browse jobs in Mini App\n"
            "/tracker — track your applications\n"
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
        "scrape_cooldown": "Please wait {minutes} min before searching again.",
        # --- scoring ---
        "score_no_resume": "Resume not found. Send a file (.txt, .pdf, .docx) and try again.",
        "score_no_jobs": "No jobs to score. Run /scrape first.",
        "score_progress": "Scoring {done}/{total}…",
        "score_done": "Done. Scored: {total} jobs.",
        "score_high_alert": "⭐ {high} job(s) scored ≥ 8 — tap the button to browse!",
        "score_no_good_jobs": "No jobs met the minimum score threshold. Try /scrape to fetch more.",
        "rescore_start": "Re-scoring {count} job(s) with score ≤ 5 (older than 7 days)…",
        "rescore_nothing": "Nothing to re-score. No jobs with score ≤ 5 older than 7 days.",
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
        "interested_msg": "Saved to your list ✅",
        # --- pagination ---
        "jobs_show_more": "Show {remaining} more →",
        "jobs_page_info": "Showing {shown} of {total}",
        # --- onboarding city ---
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
        "status_offer": "Offer received! 🎉",
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
            "/jobs — browse jobs in Mini App\n\n"
            "📋 Tracking\n"
            "/tracker — view and manage your applications\n\n"
            "📊 Info\n"
            "/stats — show statistics\n"
            "/start — welcome message\n\n"
            "⚙️ Settings\n"
            "/language — change language\n"
            "/stop — stop the bot (admin only)"
        ),
        # --- filters ---
        "filters_current_none": "🔍 Skills filter: not set.\n\nAll jobs will be shown regardless of tech stack.",
        "filters_current": "🔍 Skills filter: {skills}\n\nOnly jobs mentioning these skills will be shown.",
        "filters_ask_skills": "Type skills separated by commas (e.g. Python, SQL, React):\n\n/cancel — keep current settings.",
        "filters_saved": "✅ Skills filter saved: {skills}\n\nNext /scrape will search for jobs requiring these skills.",
        "filters_cleared": "🗑️ Filters cleared. Next /scrape will show all jobs.",
        "filters_invalid": "Please enter at least one skill name.",
        "btn_set_skills": "🔧 Set skills",
        "btn_clear_filters": "🗑️ Clear filters",
        "scrape_skills_active": "Active skills filter: {skills}",
        # --- mini app ---
        "webapp_btn": "🃏 Browse Jobs",
        "webapp_open": "Tap the button below to browse jobs with swipe cards:",
        # --- backup ---
        "backup_running": "Creating backup…",
        "backup_done": "Backup sent ✅",
        # --- misc ---
        "error_generic": "Something went wrong: {error}",
        "access_denied": "Access denied.",
        "stop_msg": "Stopping bot…",
    },

    "ru": {
        # --- onboarding ---
        "start_no_resume": (
            "Привет! Я нахожу стажировки и junior IT-вакансии в Польше.\n\n"
            "Отправь резюме, чтобы начать (.txt, .pdf, .docx)."
        ),
        "start_with_resume": (
            "Привет! Резюме уже загружено.\n\n"
            "/scrape — найти вакансии (спросит город)\n"
            "/score — оценить вакансии через AI\n"
            "/jobs — просмотр вакансий в Mini App\n"
            "/tracker — отслеживать заявки\n"
            "/resume — показать резюме\n"
            "/stats — статистика\n"
            "/language — сменить язык\n"
            "/stop — остановить бота"
        ),
        # --- resume ---
        "resume_not_found": "Резюме не найдено. Отправь файл (.txt, .pdf, .docx).",
        "resume_show_header": "Текущее резюме ({chars} символов):",
        "resume_unsupported": "Поддерживаются только .txt, .pdf, .docx.",
        "resume_processing": "Обрабатываю файл…",
        "resume_saved": "Резюме сохранено ✅ ({chars} символов).\nБудет использоваться при следующем /scrape.",
        "resume_error": "Ошибка: {error}",
        "resume_upload_failed": "Не удалось обработать файл: {error}",
        # --- scrape ---
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
        "scrape_cooldown": "Подожди ещё {minutes} мин. перед следующим поиском.",
        # --- scoring ---
        "score_no_resume": "Резюме не найдено. Отправь файл (.txt, .pdf, .docx) и повтори.",
        "score_no_jobs": "Нет вакансий для оценки. Сначала запусти /scrape.",
        "score_progress": "Оцениваю {done}/{total}…",
        "score_done": "Готово. Оценено вакансий: {total}.",
        "score_high_alert": "⭐ {high} вакансий с оценкой ≥ 8 — нажми кнопку, чтобы открыть!",
        "score_no_good_jobs": "Ни одна вакансия не прошла минимальный порог оценки. Попробуй /scrape.",
        "rescore_start": "Переоцениваю {count} вакансий с оценкой ≤ 5 (старше 7 дней)…",
        "rescore_nothing": "Нечего переоценивать. Нет вакансий с оценкой ≤ 5 старше 7 дней.",
        # --- jobs ---
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
        "interested_msg": "Сохранено в список ✅",
        # --- pagination ---
        "jobs_show_more": "Показать ещё {remaining} →",
        "jobs_page_info": "Показано {shown} из {total}",
        # --- onboarding city ---
        "onboard_ask_city": "Отлично! Теперь выбери город для первого поиска:",
        # --- tracker ---
        "tracker_empty": "Заявок пока нет. Используй /jobs чтобы найти вакансии.",
        "tracker_header": "📋 Твои заявки ({count} всего):\n",
        "tracker_today": "Сегодня",
        "tracker_week": "На этой неделе",
        "tracker_older": "2+ недели назад",
        "tracker_followup": "написать follow-up?",
        "status_interviewing": "Отмечено: собеседование",
        "status_rejected": "Отмечено: отказ",
        "status_offer": "Оффер получен! 🎉",
        # --- feedback ---
        "feedback_generating": "Анализирую резюме…",
        "feedback_header": "📋 Анализ резюме",
        # --- stats ---
        "stats": (
            "📊 Статистика:\n"
            "Всего вакансий: {total}\n"
            "Оценено: {scored}\n"
            "Средний score: {avg}\n"
            "Подано заявок: {applied}\n"
            "Пропущено: {skipped}"
        ),
        # --- quick-action buttons ---
        "btn_view_jobs": "📋 Смотреть вакансии",
        "btn_rescore": "🔄 Переоценить",
        "btn_score_now": "🤖 Оценить сейчас",
        "btn_help": "❓ Помощь",
        # --- language ---
        "lang_choose": "Выбери язык:",
        "lang_set": "Язык изменён на Русский 🇷🇺",
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
            "/jobs — просмотр вакансий в Mini App\n\n"
            "📋 Отслеживание\n"
            "/tracker — просмотр и управление заявками\n\n"
            "📊 Информация\n"
            "/stats — статистика\n"
            "/start — приветственное сообщение\n\n"
            "⚙️ Настройки\n"
            "/language — сменить язык\n"
            "/stop — остановить бота (только admin)"
        ),
        # --- filters ---
        "filters_current_none": "🔍 Фильтр навыков: не задан.\n\nБудут показаны все вакансии.",
        "filters_current": "🔍 Фильтр навыков: {skills}\n\nБудут показаны только вакансии с этими навыками.",
        "filters_ask_skills": "Введи навыки через запятую (например: Python, SQL, React):\n\n/cancel — оставить текущие настройки.",
        "filters_saved": "✅ Фильтр навыков сохранён: {skills}\n\nСледующий /scrape будет искать вакансии с этими навыками.",
        "filters_cleared": "🗑️ Фильтры сброшены. Следующий /scrape покажет все вакансии.",
        "filters_invalid": "Введи хотя бы один навык.",
        "btn_set_skills": "🔧 Задать навыки",
        "btn_clear_filters": "🗑️ Сбросить фильтры",
        "scrape_skills_active": "Активный фильтр навыков: {skills}",
        # --- mini app ---
        "webapp_btn": "🃏 Смотреть вакансии",
        "webapp_open": "Нажми кнопку ниже, чтобы листать вакансии карточками:",
        # --- backup ---
        "backup_running": "Создаю резервную копию…",
        "backup_done": "Резервная копия отправлена ✅",
        # --- misc ---
        "error_generic": "Что-то пошло не так: {error}",
        "access_denied": "Доступ запрещён.",
        "stop_msg": "Останавливаю бота…",
    },

    "pl": {
        # --- onboarding ---
        "start_no_resume": (
            "Cześć! Szukam staży i ofert junior IT w Polsce.\n\n"
            "Wyślij swoje CV, żeby zacząć (.txt, .pdf, .docx)."
        ),
        "start_with_resume": (
            "Cześć! CV już wgrane.\n\n"
            "/scrape — znajdź oferty (zapyta o miasto)\n"
            "/score — ocen oferty przez AI\n"
            "/jobs — przeglądaj oferty w Mini App\n"
            "/tracker — śledź swoje aplikacje\n"
            "/resume — pokaż aktualne CV\n"
            "/stats — statystyki\n"
            "/language — zmień język\n"
            "/stop — zatrzymaj bota"
        ),
        # --- resume ---
        "resume_not_found": "CV nie znalezione. Wyślij plik (.txt, .pdf, .docx).",
        "resume_show_header": "Aktualne CV ({chars} znaków):",
        "resume_unsupported": "Obsługiwane tylko .txt, .pdf, .docx.",
        "resume_processing": "Przetwarzam plik…",
        "resume_saved": "CV zapisane ✅ ({chars} znaków).\nBędzie używane przy następnym /scrape.",
        "resume_error": "Błąd: {error}",
        "resume_upload_failed": "Nie udało się przetworzyć pliku: {error}",
        # --- scrape ---
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
        "scrape_cooldown": "Poczekaj jeszcze {minutes} min. przed następnym wyszukiwaniem.",
        # --- scoring ---
        "score_no_resume": "CV nie znalezione. Wyślij plik (.txt, .pdf, .docx) i spróbuj ponownie.",
        "score_no_jobs": "Brak ofert do oceny. Najpierw uruchom /scrape.",
        "score_progress": "Oceniam {done}/{total}…",
        "score_done": "Gotowe. Oceniono ofert: {total}.",
        "score_high_alert": "⭐ {high} ofert z oceną ≥ 8 — naciśnij przycisk, aby przeglądać!",
        "score_no_good_jobs": "Żadna oferta nie spełniła minimalnego progu. Spróbuj /scrape.",
        "rescore_start": "Ponowna ocena {count} ofert z wynikiem ≤ 5 (starszych niż 7 dni)…",
        "rescore_nothing": "Brak ofert do ponownej oceny. Brak ofert z wynikiem ≤ 5 starszych niż 7 dni.",
        # --- jobs ---
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
        "interested_msg": "Zapisano do listy ✅",
        # --- pagination ---
        "jobs_show_more": "Pokaż {remaining} więcej →",
        "jobs_page_info": "Pokazano {shown} z {total}",
        # --- onboarding city ---
        "onboard_ask_city": "Świetnie! Wybierz miasto do pierwszego wyszukiwania:",
        # --- tracker ---
        "tracker_empty": "Brak aplikacji. Użyj /jobs żeby znaleźć oferty.",
        "tracker_header": "📋 Twoje aplikacje ({count} łącznie):\n",
        "tracker_today": "Dzisiaj",
        "tracker_week": "W tym tygodniu",
        "tracker_older": "2+ tygodnie temu",
        "tracker_followup": "napisać follow-up?",
        "status_interviewing": "Zaznaczono: rozmowa rekrutacyjna",
        "status_rejected": "Zaznaczono: odmowa",
        "status_offer": "Oferta otrzymana! 🎉",
        # --- feedback ---
        "feedback_generating": "Analizuję CV…",
        "feedback_header": "📋 Analiza CV",
        # --- stats ---
        "stats": (
            "📊 Statystyki:\n"
            "Wszystkich ofert: {total}\n"
            "Ocenionych: {scored}\n"
            "Średnia ocena: {avg}\n"
            "Złożono aplikacji: {applied}\n"
            "Pominiętych: {skipped}"
        ),
        # --- quick-action buttons ---
        "btn_view_jobs": "📋 Pokaż oferty",
        "btn_rescore": "🔄 Oceń ponownie",
        "btn_score_now": "🤖 Oceń teraz",
        "btn_help": "❓ Pomoc",
        # --- language ---
        "lang_choose": "Wybierz język:",
        "lang_set": "Język zmieniony na Polski 🇵🇱",
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
            "/jobs — przeglądaj oferty w Mini App\n\n"
            "📋 Śledzenie\n"
            "/tracker — zarządzaj swoimi aplikacjami\n\n"
            "📊 Informacje\n"
            "/stats — statystyki\n"
            "/start — wiadomość powitalna\n\n"
            "⚙️ Ustawienia\n"
            "/language — zmień język\n"
            "/stop — zatrzymaj bota (tylko admin)"
        ),
        # --- filters ---
        "filters_current_none": "🔍 Filtr umiejętności: nie ustawiony.\n\nWszystkie oferty będą wyświetlane.",
        "filters_current": "🔍 Filtr umiejętności: {skills}\n\nPokazywane będą tylko oferty wymagające tych umiejętności.",
        "filters_ask_skills": "Wpisz umiejętności oddzielone przecinkami (np. Python, SQL, React):\n\n/cancel — zachowaj obecne ustawienia.",
        "filters_saved": "✅ Filtr umiejętności zapisany: {skills}\n\nNastępne /scrape będzie szukać ofert z tymi umiejętnościami.",
        "filters_cleared": "🗑️ Filtry wyczyszczone. Następne /scrape pokaże wszystkie oferty.",
        "filters_invalid": "Wpisz co najmniej jedną umiejętność.",
        "btn_set_skills": "🔧 Ustaw umiejętności",
        "btn_clear_filters": "🗑️ Wyczyść filtry",
        "scrape_skills_active": "Aktywny filtr umiejętności: {skills}",
        # --- mini app ---
        "webapp_btn": "🃏 Przeglądaj oferty",
        "webapp_open": "Kliknij przycisk poniżej, aby przeglądać oferty kartami:",
        # --- backup ---
        "backup_running": "Tworzę kopię zapasową…",
        "backup_done": "Kopia zapasowa wysłana ✅",
        # --- misc ---
        "error_generic": "Coś poszło nie tak: {error}",
        "access_denied": "Brak dostępu.",
        "stop_msg": "Zatrzymuję bota…",
    },
}


def t(lang: str, key: str, **kw) -> str:
    """Return translated string for lang+key, falling back to English."""
    text = TEXTS.get(lang, {}).get(key) or TEXTS["en"].get(key, key)
    return text.format(**kw) if kw else text
