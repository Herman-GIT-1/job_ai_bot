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
        "scrape_fallback_warning": (
            "Resume not found or AI could not process it — "
            "search used generic queries.\n"
            "Upload a resume (.txt/.pdf/.docx) for more accurate results."
        ),
        "scrape_done": "Done. Found: {found}, new in DB: {saved}.",
        "scrape_cancelled": "Search cancelled.",
        # --- scoring ---
        "score_no_resume": "Resume not found. Send a file (.txt, .pdf, .docx) and try again.",
        "score_no_jobs": "No jobs to score. Run /scrape first.",
        "score_progress": "Scoring {done}/{total}…",
        "score_done": "Done. Scored: {total} jobs.",
        "score_high_alert": "⭐ {high} job(s) scored ≥ 8 — view them with /jobs 8",
        "rescore_start": "Scores reset. Re-scoring now…",
        # --- jobs ---
        "jobs_none": "No new jobs with score ≥ {min_score}.",
        "jobs_found": "Jobs found (score ≥ {min_score}): {count}",
        "btn_apply": "Apply ✅",
        "btn_skip": "Skip ❌",
        "btn_letter": "Letter 📄",
        "applied_msg": "Application noted ✅\n🔗 {link}",
        "skipped_msg": "Skipped ❌",
        "letter_not_found": "Letter not found.",
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
        # --- language ---
        "lang_choose": "Choose language:",
        "lang_set": "Language set to English 🇬🇧",
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
        "scrape_fallback_warning": (
            "Резюме не найдено или AI не смог его обработать — "
            "поиск выполнен по базовым запросам.\n"
            "Загрузи резюме (.txt/.pdf/.docx) для более точных результатов."
        ),
        "scrape_done": "Готово. Найдено: {found}, новых в базе: {saved}.",
        "scrape_cancelled": "Поиск отменён.",
        "score_no_resume": "Резюме не найдено. Отправь файл (.txt, .pdf, .docx) и повтори.",
        "score_no_jobs": "Нет вакансий для оценки. Сначала запусти /scrape.",
        "score_progress": "Оцениваю {done}/{total}…",
        "score_done": "Готово. Оценено вакансий: {total}.",
        "score_high_alert": "⭐ {high} вакансий с оценкой ≥ 8 — смотри /jobs 8",
        "rescore_start": "Оценки сброшены. Запускаю оценку заново…",
        "jobs_none": "Нет новых вакансий с оценкой ≥ {min_score}.",
        "jobs_found": "Найдено вакансий (score ≥ {min_score}): {count}",
        "btn_apply": "Подать ✅",
        "btn_skip": "Пропустить ❌",
        "btn_letter": "Письмо 📄",
        "applied_msg": "Заявка отмечена ✅\n🔗 {link}",
        "skipped_msg": "Пропущено ❌",
        "letter_not_found": "Письмо не найдено.",
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
        "lang_choose": "Выбери язык:",
        "lang_set": "Язык изменён на Русский 🇷🇺",
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
        "scrape_fallback_warning": (
            "CV nie znalezione lub AI nie mógł go przetworzyć — "
            "wyszukiwanie z podstawowymi zapytaniami.\n"
            "Wgraj CV (.txt/.pdf/.docx) dla dokładniejszych wyników."
        ),
        "scrape_done": "Gotowe. Znalezione: {found}, nowych w bazie: {saved}.",
        "scrape_cancelled": "Wyszukiwanie anulowane.",
        "score_no_resume": "CV nie znalezione. Wyślij plik (.txt, .pdf, .docx) i spróbuj ponownie.",
        "score_no_jobs": "Brak ofert do oceny. Najpierw uruchom /scrape.",
        "score_progress": "Oceniam {done}/{total}…",
        "score_done": "Gotowe. Oceniono ofert: {total}.",
        "score_high_alert": "⭐ {high} ofert z oceną ≥ 8 — sprawdź /jobs 8",
        "rescore_start": "Oceny zresetowane. Ponowna ocena…",
        "jobs_none": "Brak nowych ofert z oceną ≥ {min_score}.",
        "jobs_found": "Znalezione oferty (ocena ≥ {min_score}): {count}",
        "btn_apply": "Aplikuj ✅",
        "btn_skip": "Pomiń ❌",
        "btn_letter": "List 📄",
        "applied_msg": "Aplikacja zaznaczona ✅\n🔗 {link}",
        "skipped_msg": "Pominięto ❌",
        "letter_not_found": "List nie znaleziony.",
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
        "lang_choose": "Wybierz język:",
        "lang_set": "Język zmieniony na Polski 🇵🇱",
        "access_denied": "Brak dostępu.",
        "stop_msg": "Zatrzymuję bota…",
    },
}


def t(lang: str, key: str, **kw) -> str:
    """Return translated string for lang+key, falling back to English."""
    text = TEXTS.get(lang, {}).get(key) or TEXTS["en"].get(key, key)
    return text.format(**kw) if kw else text
