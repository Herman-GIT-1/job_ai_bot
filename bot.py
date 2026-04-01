import asyncio
import datetime
import functools
import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (Application, CommandHandler, CallbackQueryHandler,
                          MessageHandler, ConversationHandler, filters, ContextTypes)

from database import (get_jobs_to_apply, get_job_link, get_cover_letter, mark_applied,
                      get_stats, get_jobs, update_job, count_jobs, reset_scores,
                      save_job, get_user_lang, set_user_lang,
                      get_last_scrape, set_last_scrape)
from scraper import search_jobs
from resume_parser import parse_resume, save_resume, load_resume, validate
from ai_score import evaluate
from cover_letter import generate_letter
from strings import t

load_dotenv()

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ADMIN_CHAT_ID = int(os.environ["TELEGRAM_CHAT_ID"])

ASK_CITY = 0

CITIES = ["Warszawa", "Kraków", "Wrocław", "Gdańsk", "Poznań", "Remote"]


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
            score = await loop.run_in_executor(
                None, lambda j=job, r=resume: evaluate(j, resume=r)
            )
            letter = (
                await loop.run_in_executor(
                    None, lambda j=job, r=resume: generate_letter(j, resume=r)
                )
                if score >= 7 else ""
            )
            update_job(job_id, chat_id, score, letter)
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

    # Completion summary + high-score alert (NEXT_STEPS 4.1)
    high_count = len(get_jobs_to_apply(chat_id, min_score=8))
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(t(lang_code, "btn_view_jobs"), callback_data="action:jobs"),
    ]])
    summary = t(lang_code, "score_done", total=total)
    if high_count:
        summary += "\n\n" + t(lang_code, "score_high_alert", high=high_count)
    await status_msg.edit_text(summary, reply_markup=keyboard)


async def _send_jobs(msg, chat_id: int, min_score: int, lang_code: str) -> None:
    """Send job cards with Apply/Skip/Letter buttons."""
    vacancies = get_jobs_to_apply(chat_id, min_score)
    if not vacancies:
        await msg.reply_text(t(lang_code, "jobs_none", min_score=min_score))
        return

    await msg.reply_text(t(lang_code, "jobs_found", min_score=min_score, count=len(vacancies)))

    for job_id, title, company, _link, score, description, _cover_letter in vacancies:
        desc = (description or "").strip()
        preview = desc[:280] + "…" if len(desc) > 280 else desc
        text = (
            f"<b>{title}</b>\n"
            f"🏢 {company}  •  ⭐ {score}/10\n\n"
            f"{preview}"
        )
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(t(lang_code, "btn_apply"),  callback_data=f"apply:{job_id}"),
            InlineKeyboardButton(t(lang_code, "btn_skip"),   callback_data=f"skip:{job_id}"),
            InlineKeyboardButton(t(lang_code, "btn_letter"), callback_data=f"letter:{job_id}"),
        ]])
        await msg.reply_text(text, parse_mode="HTML", reply_markup=keyboard)


SCRAPE_COOLDOWN_MINUTES = 60


async def _run_scrape(city: str, msg, chat_id: int, lang_code: str) -> None:
    """Run scraping for city and send results. msg — telegram Message to reply to."""
    if chat_id != CHAT_ID:
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
    await msg.reply_text(t(lang_code, "scrape_searching", city=city))
    loop = asyncio.get_running_loop()
    jobs, used_fallback = await loop.run_in_executor(None, search_jobs, city)

    if used_fallback:
        await msg.reply_text(t(lang_code, "scrape_fallback_warning"))

    saved = 0
    for job in jobs:
        before = count_jobs(chat_id)
        save_job(job, chat_id)
        if count_jobs(chat_id) > before:
            saved += 1

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
    reset_scores(chat_id)
    await update.message.reply_text(t(lang_code, "rescore_start"))
    await _run_score(update.message, chat_id, lang_code)


async def cmd_scrape_ask_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang_code = _lang(update)
    await update.message.reply_text(
        t(lang_code, "scrape_ask_city"),
        reply_markup=_city_keyboard(),
    )
    return ASK_CITY


async def cmd_scrape_run(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User typed a custom city name."""
    city = update.message.text.strip()
    chat_id = update.effective_chat.id
    await _run_scrape(city, update.message, chat_id, _lang(update))
    return ConversationHandler.END


async def cmd_scrape_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang_code = _lang(update)
    await update.message.reply_text(t(lang_code, "scrape_cancelled"))
    return ConversationHandler.END


async def cmd_jobs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    lang_code = _lang(update)
    try:
        min_score = int(context.args[0]) if context.args else 7
        min_score = max(0, min(10, min_score))
    except (ValueError, IndexError):
        min_score = 7
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
        await update.message.reply_text(t(lang_code, "resume_saved", chars=len(text)))
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


@admin_only
async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(t(_lang(update), "stop_msg"))
    await context.application.stop()


# ---------------------------------------------------------------------------
# Inline button callback handler
# ---------------------------------------------------------------------------

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat.id
    data = query.data
    lang_code = get_user_lang(chat_id)

    # --- language selection ---
    if data.startswith("lang:"):
        new_lang = data.split(":", 1)[1]
        set_user_lang(chat_id, new_lang)
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(t(new_lang, "lang_set"))
        return

    # --- city selection (inside scrape conversation) ---
    if data.startswith("city:"):
        city = data.split(":", 1)[1]
        await query.edit_message_reply_markup(reply_markup=None)
        await _run_scrape(city, query.message, chat_id, lang_code)
        return

    # --- quick actions from stats / score done buttons ---
    if data.startswith("action:"):
        action = data.split(":", 1)[1]
        if action == "jobs":
            await _send_jobs(query.message, chat_id, 7, lang_code)
        elif action == "score":
            await _run_score(query.message, chat_id, lang_code)
        elif action == "rescore":
            reset_scores(chat_id)
            await query.message.reply_text(t(lang_code, "rescore_start"))
            await _run_score(query.message, chat_id, lang_code)
        return

    # --- job card actions: apply / skip / letter ---
    parts = data.split(":", 1)
    if len(parts) != 2:
        return
    action, job_id_str = parts
    job_id = int(job_id_str)

    if action == "letter":
        row = get_cover_letter(job_id, chat_id)
        if not row or not row[2]:
            await query.answer(t(lang_code, "letter_not_found"), show_alert=True)
            return
        title, company, letter = row
        filename = f"cover_letter_{company}_{title}.txt".replace(" ", "_").replace("/", "-")
        await query.message.reply_document(document=letter.encode("utf-8"), filename=filename)

    elif action == "apply":
        link = get_job_link(job_id, chat_id)
        mark_applied(job_id, chat_id, status=1)
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(t(lang_code, "applied_msg", link=link))

    elif action == "skip":
        mark_applied(job_id, chat_id, status=2)
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(t(lang_code, "skipped_msg"))


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
    await query.edit_message_reply_markup(reply_markup=None)
    await _run_scrape(city, query.message, chat_id, lang_code)
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# App entry point
# ---------------------------------------------------------------------------

def main():
    app = Application.builder().token(TOKEN).build()

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
    app.add_handler(CommandHandler("language", cmd_language))
    app.add_handler(CommandHandler("resume",   cmd_resume_show))
    app.add_handler(CommandHandler("score",    cmd_score))
    app.add_handler(CommandHandler("rescore",  cmd_rescore))
    app.add_handler(CommandHandler("jobs",     cmd_jobs))
    app.add_handler(CommandHandler("stats",    cmd_stats))
    app.add_handler(CommandHandler("stop",     cmd_stop))
    app.add_handler(scrape_conv)
    app.add_handler(MessageHandler(filters.Document.ALL, cmd_resume_upload))
    app.add_handler(CallbackQueryHandler(button))

    print("Bot started...")
    app.run_polling()


if __name__ == "__main__":
    main()
