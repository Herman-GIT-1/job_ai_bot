from dotenv import load_dotenv
load_dotenv()

import asyncio
import datetime
import functools
import logging
import os
from telegram import (Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo,
                       MenuButtonWebApp, MenuButtonDefault)
from telegram.ext import (Application, CommandHandler, CallbackQueryHandler,
                          MessageHandler, ConversationHandler, filters, ContextTypes)

from config import (CITIES, SCRAPE_COOLDOWN_MINUTES, JOBS_PAGE_SIZE,
                    DEFAULT_MIN_SCORE, HIGH_SCORE_ALERT, LETTER_MIN_SCORE,
                    JOB_EXPIRY_DAYS, WEBAPP_URL)
from database import (get_jobs_to_apply, count_jobs_to_apply, get_job_link,
                      get_cover_letter, mark_applied, update_job_status,
                      get_stats, get_jobs, update_job, reset_scores,
                      reset_scores_selective,
                      save_job, get_user_lang, set_user_lang,
                      get_last_scrape, set_last_scrape, get_applied_jobs,
                      delete_expired_jobs, get_resume,
                      get_user_skills, set_user_skills,
                      set_resume_file,
                      get_user_city, set_user_city)
from scraper import search_jobs
from resume_parser import parse_resume, save_resume, load_resume, validate
from ai_score import evaluate
from cover_letter import generate_letter
from resume_feedback import analyze_resume
from backup import send_backup
from strings import t

logger = logging.getLogger(__name__)

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ADMIN_CHAT_ID = int(os.environ["TELEGRAM_CHAT_ID"])

ASK_CITY = 0   # scrape_conv: waiting for city pick/type


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _lang(update: Update) -> str:
    return get_user_lang(update.effective_chat.id)


def admin_only(func):
    """Restrict handler to the bot admin. Used only for /stop."""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_chat.id != ADMIN_CHAT_ID:
            if update.message:
                await update.message.reply_text(t("en", "access_denied"))
            return
        return await func(update, context)
    return wrapper


def _city_keyboard() -> InlineKeyboardMarkup:
    buttons = [InlineKeyboardButton(c, callback_data=f"city:{c}") for c in CITIES]
    rows = [buttons[i:i + 3] for i in range(0, len(buttons), 3)]
    return InlineKeyboardMarkup(rows)


def _lang_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🇬🇧 English", callback_data="lang:en"),
        InlineKeyboardButton("🇷🇺 Русский", callback_data="lang:ru"),
        InlineKeyboardButton("🇵🇱 Polski",  callback_data="lang:pl"),
    ]])


# ---------------------------------------------------------------------------
# Core logic helpers (shared between commands and button callbacks)
# ---------------------------------------------------------------------------

async def _run_score(msg, chat_id: int, lang_code: str) -> None:
    """Score all unscored jobs for this user. msg — telegram Message to reply to."""
    try:
        resume = load_resume(chat_id)
    except FileNotFoundError:
        await msg.reply_text(t(lang_code, "score_no_resume"))
        return

    pending = get_jobs(chat_id)
    if not pending:
        await msg.reply_text(t(lang_code, "score_no_jobs"))
        return

    total = len(pending)
    status_msg = await msg.reply_text(t(lang_code, "score_progress", done=0, total=total))

    loop = asyncio.get_running_loop()
    sem = asyncio.Semaphore(5)
    done = 0

    async def score_one(job_id, job):
        nonlocal done
        async with sem:
            try:
                score, reason = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda j=job, r=resume: evaluate(j, resume=r)),
                    timeout=30.0,
                )
            except asyncio.TimeoutError:
                score, reason = 5, ""
            letter = ""
            if score >= LETTER_MIN_SCORE:
                try:
                    letter = await asyncio.wait_for(
                        loop.run_in_executor(
                            None, lambda j=job, r=resume: generate_letter(j, resume=r)
                        ),
                        timeout=60.0,
                    )
                except asyncio.TimeoutError:
                    letter = "Cover letter generation timed out."
            update_job(job_id, chat_id, score, letter, reason)
        done += 1
        if done % 5 == 0 or done == total:
            await status_msg.edit_text(t(lang_code, "score_progress", done=done, total=total))

    await asyncio.gather(*[
        score_one(
            job_id,
            {"title": title, "company": company,
             "tech_stack": tech_stack, "description": description},
        )
        for job_id, title, company, _link, tech_stack, description in pending
    ])

    good_count = count_jobs_to_apply(chat_id, min_score=DEFAULT_MIN_SCORE)
    high_count = count_jobs_to_apply(chat_id, min_score=HIGH_SCORE_ALERT)

    summary = t(lang_code, "score_done", total=total)
    if good_count == 0:
        summary += "\n\n" + t(lang_code, "score_no_good_jobs")
    elif high_count:
        summary += "\n\n" + t(lang_code, "score_high_alert", high=high_count)

    if WEBAPP_URL and good_count > 0:
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(t(lang_code, "webapp_btn"), web_app=WebAppInfo(url=WEBAPP_URL))
        ]])
    else:
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(t(lang_code, "btn_view_jobs"), callback_data="action:jobs"),
        ]]) if good_count > 0 else None

    await status_msg.edit_text(summary, reply_markup=keyboard)


async def _send_jobs(msg, chat_id: int, min_score: int, lang_code: str,
                     offset: int = 0) -> None:
    """Send paginated job cards with Apply/Skip/Letter buttons."""
    vacancies = get_jobs_to_apply(chat_id, min_score, limit=JOBS_PAGE_SIZE, offset=offset)
    if not vacancies:
        if offset == 0:
            await msg.reply_text(t(lang_code, "jobs_none", min_score=min_score))
        return

    total = count_jobs_to_apply(chat_id, min_score)
    if offset == 0:
        await msg.reply_text(t(lang_code, "jobs_found", min_score=min_score, count=total))

    for row in vacancies:
        job_id, title, company, _link, score, description, _cover_letter = row[:7]
        salary_min, salary_max, salary_currency = row[7], row[8], row[9]
        score_reason = row[10] if len(row) > 10 else None
        desc = (description or "").strip()
        preview = desc[:280] + "…" if len(desc) > 280 else desc

        salary_line = ""
        if salary_min:
            cur = salary_currency or "PLN"
            salary_line = f"\n💰 {salary_min:,}–{salary_max:,} {cur}" if salary_max else f"\n💰 from {salary_min:,} {cur}"

        safe_reason = score_reason.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") if score_reason else ""
        reason_line = f"\n<i>{safe_reason}</i>" if safe_reason else ""

        text = (
            f"<b>{title}</b>\n"
            f"🏢 {company}  •  ⭐ {score}/10{salary_line}{reason_line}\n\n"
            f"{preview}"
        )
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(t(lang_code, "btn_apply"),  callback_data=f"apply:{job_id}"),
            InlineKeyboardButton(t(lang_code, "btn_skip"),   callback_data=f"skip:{job_id}"),
            InlineKeyboardButton(t(lang_code, "btn_letter"), callback_data=f"letter:{job_id}"),
        ]])
        await msg.reply_text(text, parse_mode="HTML", reply_markup=keyboard)

    shown = offset + len(vacancies)
    if shown < total:
        more_keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(
                t(lang_code, "jobs_show_more", remaining=total - shown),
                callback_data=f"jobs_page:{shown}:{min_score}",
            )
        ]])
        await msg.reply_text(
            t(lang_code, "jobs_page_info", shown=shown, total=total),
            reply_markup=more_keyboard,
        )


async def _run_scrape(city: str, msg, chat_id: int, lang_code: str) -> None:
    """Run scraping for city and send results. msg — telegram Message to reply to."""
    if chat_id != ADMIN_CHAT_ID:
        last = get_last_scrape(chat_id)
        if last is not None:
            elapsed = datetime.datetime.now(datetime.timezone.utc) - last
            remaining = SCRAPE_COOLDOWN_MINUTES * 60 - int(elapsed.total_seconds())
            if remaining > 0:
                await msg.reply_text(
                    t(lang_code, "scrape_cooldown", minutes=remaining // 60 + 1)
                )
                return

    set_last_scrape(chat_id)

    has_resume = get_resume(chat_id) is not None
    if not has_resume:
        await msg.reply_text(t(lang_code, "scrape_no_resume_hint"))

    skills = get_user_skills(chat_id)
    search_msg = t(lang_code, "scrape_searching", city=city)
    if skills:
        search_msg += "\n" + t(lang_code, "scrape_skills_active", skills=", ".join(skills))
    await msg.reply_text(search_msg)
    loop = asyncio.get_running_loop()
    jobs, used_fallback = await loop.run_in_executor(None, lambda: search_jobs(city, chat_id))

    if used_fallback and has_resume:
        await msg.reply_text(t(lang_code, "scrape_fallback_warning"))

    saved = sum(1 for job in jobs if save_job(job, chat_id))

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(t(lang_code, "btn_score_now"), callback_data="action:score"),
    ]])
    await msg.reply_text(
        t(lang_code, "scrape_done", found=len(jobs), saved=saved),
        reply_markup=keyboard,
    )


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang_code = _lang(update)
    try:
        load_resume(update.effective_chat.id)
        await update.message.reply_text(t(lang_code, "start_with_resume"))
    except FileNotFoundError:
        await update.message.reply_text(
            t(lang_code, "start_no_resume"),
            reply_markup=_lang_keyboard(),
        )


async def cmd_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang_code = _lang(update)
    await update.message.reply_text(t(lang_code, "lang_choose"), reply_markup=_lang_keyboard())


async def cmd_score(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await _run_score(update.message, chat_id, _lang(update))


async def cmd_rescore(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    lang_code = _lang(update)
    count = reset_scores_selective(chat_id)
    if count == 0:
        await update.message.reply_text(t(lang_code, "rescore_nothing"))
        return
    await update.message.reply_text(t(lang_code, "rescore_start", count=count))
    await _run_score(update.message, chat_id, lang_code)


async def cmd_scrape_ask_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    lang_code = _lang(update)
    saved_city = get_user_city(chat_id)
    if saved_city:
        await _run_scrape(saved_city, update.message, chat_id, lang_code)
        return ConversationHandler.END
    await update.message.reply_text(
        t(lang_code, "scrape_ask_city"),
        reply_markup=_city_keyboard(),
    )
    return ASK_CITY


async def cmd_scrape_run(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User typed a custom city name."""
    city = update.message.text.strip()
    chat_id = update.effective_chat.id
    set_user_city(chat_id, city)
    await _run_scrape(city, update.message, chat_id, _lang(update))
    return ConversationHandler.END


async def cmd_scrape_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang_code = _lang(update)
    await update.message.reply_text(t(lang_code, "scrape_cancelled"))
    return ConversationHandler.END


async def cmd_jobs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    lang_code = _lang(update)
    if WEBAPP_URL:
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(t(lang_code, "webapp_btn"), web_app=WebAppInfo(url=WEBAPP_URL))
        ]])
        await update.message.reply_text(t(lang_code, "webapp_open"), reply_markup=keyboard)
    else:
        try:
            min_score = int(context.args[0]) if context.args else DEFAULT_MIN_SCORE
            min_score = max(0, min(10, min_score))
        except (ValueError, IndexError):
            min_score = DEFAULT_MIN_SCORE
        await _send_jobs(update.message, chat_id, min_score, lang_code)


async def cmd_resume_show(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang_code = _lang(update)
    try:
        chat_id = update.effective_chat.id
        text = load_resume(chat_id)
        preview = text[:600].strip()
        header = t(lang_code, "resume_show_header", chars=len(text))
        await update.message.reply_text(
            f"{header}\n\n{preview}" + ("…" if len(text) > 600 else "")
        )
    except FileNotFoundError:
        await update.message.reply_text(t(lang_code, "resume_not_found"))


async def cmd_resume_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang_code = _lang(update)
    doc = update.message.document
    filename = doc.file_name or ""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext not in ("txt", "pdf", "docx"):
        await update.message.reply_text(t(lang_code, "resume_unsupported"))
        return

    await update.message.reply_text(t(lang_code, "resume_processing"))
    try:
        tg_file = await doc.get_file()
        file_bytes = await tg_file.download_as_bytearray()
        chat_id = update.effective_chat.id
        text = parse_resume(bytes(file_bytes), filename)
        validate(text)
        save_resume(text, chat_id)
        set_resume_file(chat_id, doc.file_id, filename)
        await update.message.reply_text(t(lang_code, "resume_saved", chars=len(text)))
        await update.message.reply_text(
            t(lang_code, "onboard_ask_city"), reply_markup=_city_keyboard()
        )
    except (ValueError, ImportError) as e:
        await update.message.reply_text(t(lang_code, "resume_error", error=e))
    except Exception as e:
        await update.message.reply_text(t(lang_code, "resume_upload_failed", error=e))


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    lang_code = _lang(update)
    s = get_stats(chat_id)
    avg = f"{s['avg_score']:.1f}" if s["avg_score"] is not None else "—"
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(t(lang_code, "btn_view_jobs"), callback_data="action:jobs"),
        InlineKeyboardButton(t(lang_code, "btn_rescore"),   callback_data="action:rescore"),
    ]])
    await update.message.reply_text(
        t(lang_code, "stats",
          total=s["total"], scored=s["scored"], avg=avg,
          applied=s["applied"], skipped=s["skipped"]),
        reply_markup=keyboard,
    )


async def cmd_help(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    lang_code = _lang(update)
    await update.message.reply_text(t(lang_code, "help_text"))


async def cmd_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    lang_code = _lang(update)
    try:
        resume = load_resume(chat_id)
    except FileNotFoundError:
        await update.message.reply_text(t(lang_code, "resume_not_found"))
        return
    msg = await update.message.reply_text(t(lang_code, "feedback_generating"))
    loop = asyncio.get_running_loop()
    try:
        feedback = await asyncio.wait_for(
            loop.run_in_executor(None, lambda: analyze_resume(resume)),
            timeout=60.0,
        )
    except asyncio.TimeoutError:
        feedback = "Feedback generation timed out."
    await msg.edit_text(t(lang_code, "feedback_header") + "\n\n" + feedback)


async def cmd_tracker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    lang_code = _lang(update)
    rows = get_applied_jobs(chat_id)
    if not rows:
        await update.message.reply_text(t(lang_code, "tracker_empty"))
        return

    now = datetime.datetime.now(datetime.timezone.utc)
    groups = {"today": [], "week": [], "older": []}
    for row in rows:
        job_id, title, company, link, score, job_status, applied_at = row
        age_days = (now - applied_at).days if applied_at is not None else 0
        entry = (job_id, title, company, link, score, job_status or "applied", age_days)
        if age_days == 0:
            groups["today"].append(entry)
        elif age_days <= 7:
            groups["week"].append(entry)
        else:
            groups["older"].append(entry)

    lines = []
    for group_key, label_key in (("today", "tracker_today"), ("week", "tracker_week"), ("older", "tracker_older")):
        items = groups[group_key]
        if not items:
            continue
        lines.append(f"\n<b>{t(lang_code, label_key)}</b>")
        for job_id, title, company, link, score, job_status, age_days in items:
            status_emoji = {"applied": "📤", "interviewing": "🤝", "rejected": "❌", "offer": "🎉"}.get(job_status, "📤")
            follow_up = f" ⚠️ {t(lang_code, 'tracker_followup')}" if age_days >= 14 and job_status == "applied" else ""
            lines.append(f'{status_emoji} <a href="{link}">{title}</a> @ {company}{follow_up}')

    await update.message.reply_text(
        t(lang_code, "tracker_header", count=len(rows)) + "\n".join(lines),
        parse_mode="HTML", disable_web_page_preview=True,
    )


@admin_only
async def cmd_backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang_code = _lang(update)
    msg = await update.message.reply_text(t(lang_code, "backup_running"))
    await send_backup(context.bot, ADMIN_CHAT_ID)
    await msg.edit_text(t(lang_code, "backup_done"))




@admin_only
async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(t(_lang(update), "stop_msg"))
    await context.application.stop()


# ---------------------------------------------------------------------------
# Inline button callback handlers (one function per callback type)
# ---------------------------------------------------------------------------

async def on_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    new_lang = query.data.split(":", 1)[1]
    set_user_lang(chat_id, new_lang)
    await query.edit_message_reply_markup(reply_markup=None)
    await query.message.reply_text(t(new_lang, "lang_set"))
    try:
        load_resume(chat_id)
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(t(new_lang, "btn_score_now"),  callback_data="action:score"),
            InlineKeyboardButton(t(new_lang, "btn_view_jobs"),  callback_data="action:jobs"),
        ], [
            InlineKeyboardButton(t(new_lang, "btn_help"),       callback_data="action:help"),
        ]])
        await query.message.reply_text(
            t(new_lang, "lang_set_next_has_resume"), reply_markup=keyboard
        )
    except FileNotFoundError:
        await query.message.reply_text(t(new_lang, "lang_set_next_no_resume"))


async def on_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """City button pressed outside the /scrape conversation (e.g. after resume upload)."""
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    city = query.data.split(":", 1)[1]
    lang_code = get_user_lang(chat_id)
    set_user_city(chat_id, city)
    await query.edit_message_reply_markup(reply_markup=None)
    await _run_scrape(city, query.message, chat_id, lang_code)


async def on_jobs_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    lang_code = get_user_lang(chat_id)
    parts = query.data.split(":")
    offset, min_score = int(parts[1]), int(parts[2])
    await query.edit_message_reply_markup(reply_markup=None)
    await _send_jobs(query.message, chat_id, min_score, lang_code, offset=offset)


async def on_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    lang_code = get_user_lang(chat_id)
    action = query.data.split(":", 1)[1]
    if action == "jobs":
        if WEBAPP_URL:
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton(t(lang_code, "webapp_btn"), web_app=WebAppInfo(url=WEBAPP_URL))
            ]])
            await query.message.reply_text(t(lang_code, "webapp_open"), reply_markup=keyboard)
        else:
            await _send_jobs(query.message, chat_id, DEFAULT_MIN_SCORE, lang_code)
    elif action == "score":
        await _run_score(query.message, chat_id, lang_code)
    elif action == "rescore":
        count = reset_scores_selective(chat_id)
        if count == 0:
            await query.message.reply_text(t(lang_code, "rescore_nothing"))
            return
        await query.message.reply_text(t(lang_code, "rescore_start", count=count))
        await _run_score(query.message, chat_id, lang_code)
    elif action == "help":
        await query.message.reply_text(t(lang_code, "help_text"))


async def on_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    lang_code = get_user_lang(chat_id)
    parts = query.data.split(":")
    job_status, job_id = parts[1], int(parts[2])
    update_job_status(job_id, chat_id, job_status)
    await query.edit_message_reply_markup(reply_markup=None)
    await query.answer(t(lang_code, f"status_{job_status}"), show_alert=False)


async def on_apply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    lang_code = get_user_lang(chat_id)
    job_id = int(query.data.split(":", 1)[1])
    link = get_job_link(job_id, chat_id)
    row = get_cover_letter(job_id, chat_id)
    mark_applied(job_id, chat_id, status=1)
    await query.edit_message_reply_markup(reply_markup=None)
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(t(lang_code, "btn_open_job"), url=link),
    ], [
        InlineKeyboardButton(t(lang_code, "btn_interviewing"), callback_data=f"status:interviewing:{job_id}"),
        InlineKeyboardButton(t(lang_code, "btn_rejected"),     callback_data=f"status:rejected:{job_id}"),
    ]])
    if row:
        safe_title   = row[0].replace("<", "&lt;").replace(">", "&gt;")
        safe_company = row[1].replace("<", "&lt;").replace(">", "&gt;")
        header = f"<b>{safe_title}</b> — {safe_company}\n\n"
    else:
        header = ""
    await query.message.reply_text(
        header + t(lang_code, "applied_msg"),
        reply_markup=keyboard,
        parse_mode="HTML",
    )


async def on_skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    lang_code = get_user_lang(chat_id)
    job_id = int(query.data.split(":", 1)[1])
    mark_applied(job_id, chat_id, status=2)
    await query.edit_message_reply_markup(reply_markup=None)
    await query.message.reply_text(t(lang_code, "skipped_msg"))


async def on_letter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    lang_code = get_user_lang(chat_id)
    job_id = int(query.data.split(":", 1)[1])
    row = get_cover_letter(job_id, chat_id)
    if not row or not row[2]:
        await query.answer(t(lang_code, "letter_not_found"), show_alert=True)
        return
    title, company, letter = row
    safe_title = title.replace("<", "&lt;").replace(">", "&gt;")
    safe_company = company.replace("<", "&lt;").replace(">", "&gt;")
    await query.message.reply_text(
        f"<b>{safe_company} — {safe_title}</b>\n\n<pre>{letter}</pre>",
        parse_mode="HTML",
    )


# ---------------------------------------------------------------------------
# City button inside ConversationHandler
# ---------------------------------------------------------------------------

async def conv_city_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles city quick-pick button while inside the scrape conversation."""
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    city = query.data.split(":", 1)[1]
    lang_code = get_user_lang(chat_id)
    set_user_city(chat_id, city)
    await query.edit_message_reply_markup(reply_markup=None)
    await _run_scrape(city, query.message, chat_id, lang_code)
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# App entry point
# ---------------------------------------------------------------------------

async def _set_commands(app: Application) -> None:
    await app.bot.set_my_commands([
        ("start",    "Welcome message"),
        ("scrape",   "Search for jobs"),
        ("score",    "Score jobs with AI"),
        ("rescore",  "Reset scores and re-score"),
        ("jobs",     "Show top jobs (optional min score)"),
        ("tracker",  "Track your applications"),
        ("feedback", "Get AI feedback on your resume"),
        ("resume",   "View current resume"),
        ("stats",    "Statistics"),
        ("help",     "Command reference"),
        ("language", "Change language"),
    ])
    if WEBAPP_URL:
        await app.bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(text="My Jobs", web_app=WebAppInfo(url=WEBAPP_URL))
        )
    else:
        await app.bot.set_chat_menu_button(menu_button=MenuButtonDefault())


async def _daily_cleanup(context) -> None:
    deleted = delete_expired_jobs(days=JOB_EXPIRY_DAYS)
    if deleted:
        logger.info("Deleted %d expired jobs (>%d days old, unscored)", deleted, JOB_EXPIRY_DAYS)


async def _daily_backup(context) -> None:
    await send_backup(context.bot, ADMIN_CHAT_ID)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)

    app = Application.builder().token(TOKEN).post_init(_set_commands).build()
    app.job_queue.run_daily(
        _daily_cleanup,
        time=datetime.time(hour=4, tzinfo=datetime.timezone.utc),
    )
    app.job_queue.run_daily(
        _daily_backup,
        time=datetime.time(hour=3, tzinfo=datetime.timezone.utc),
    )

    scrape_conv = ConversationHandler(
        entry_points=[CommandHandler("scrape", cmd_scrape_ask_city)],
        states={
            ASK_CITY: [
                CallbackQueryHandler(conv_city_button, pattern="^city:"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, cmd_scrape_run),
            ],
        },
        fallbacks=[CommandHandler("cancel", cmd_scrape_cancel)],
    )

    app.add_handler(CommandHandler("start",    cmd_start))
    app.add_handler(CommandHandler("help",     cmd_help))
    app.add_handler(CommandHandler("language", cmd_language))
    app.add_handler(CommandHandler("resume",   cmd_resume_show))
    app.add_handler(CommandHandler("score",    cmd_score))
    app.add_handler(CommandHandler("rescore",  cmd_rescore))
    app.add_handler(CommandHandler("jobs",     cmd_jobs))
    app.add_handler(CommandHandler("tracker",  cmd_tracker))
    app.add_handler(CommandHandler("feedback", cmd_feedback))
    app.add_handler(CommandHandler("stats",    cmd_stats))
    app.add_handler(CommandHandler("backup",   cmd_backup))
    app.add_handler(CommandHandler("stop",     cmd_stop))
    app.add_handler(scrape_conv)

    app.add_handler(MessageHandler(filters.Document.ALL, cmd_resume_upload))

    # Inline button handlers — one per callback type for clarity
    app.add_handler(CallbackQueryHandler(on_lang,      pattern=r"^lang:"))
    app.add_handler(CallbackQueryHandler(on_city,      pattern=r"^city:"))
    app.add_handler(CallbackQueryHandler(on_jobs_page, pattern=r"^jobs_page:"))
    app.add_handler(CallbackQueryHandler(on_action,    pattern=r"^action:"))
    app.add_handler(CallbackQueryHandler(on_status,    pattern=r"^status:"))
    app.add_handler(CallbackQueryHandler(on_apply,     pattern=r"^apply:"))
    app.add_handler(CallbackQueryHandler(on_skip,      pattern=r"^skip:"))
    app.add_handler(CallbackQueryHandler(on_letter,    pattern=r"^letter:"))

    async def _error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        import traceback
        from telegram.error import Conflict, NetworkError
        if isinstance(context.error, Conflict):
            logger.warning("Conflict: another bot instance is running. Retrying…")
            return
        if isinstance(context.error, NetworkError):
            logger.warning("NetworkError: %s", context.error)
            return
        logger.error("Unhandled error", exc_info=context.error)
        try:
            tb = "".join(traceback.format_exception(
                type(context.error), context.error, context.error.__traceback__
            ))
            user_info = ""
            if isinstance(update, Update) and update.effective_chat:
                user_info = f"chat_id={update.effective_chat.id} "
            text = f"⚠️ Bot error {user_info}\n<pre>{tb[-3000:]}</pre>"
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID, text=text, parse_mode="HTML"
            )
        except Exception:
            pass  # never let the error handler itself crash the bot

    app.add_error_handler(_error_handler)
    logger.info("Bot started.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
