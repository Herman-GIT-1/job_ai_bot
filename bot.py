import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

from database import get_jobs_to_apply, get_job_link, mark_applied, get_stats

load_dotenv()

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = int(os.environ["TELEGRAM_CHAT_ID"])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я бот для поиска работы.\n\n"
        "/jobs — показать вакансии с оценкой ≥ 7\n"
        "/stats — статистика по базе вакансий"
    )


async def jobs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    vacancies = get_jobs_to_apply()
    if not vacancies:
        await update.message.reply_text("Нет новых вакансий с оценкой ≥ 7.")
        return

    await update.message.reply_text(f"Найдено вакансий: {len(vacancies)}")

    for job_id, title, company, link, cover_letter in vacancies:
        preview = (cover_letter or "")[:300]
        text = (
            f"<b>{title}</b>\n"
            f"🏢 {company}\n\n"
            f"{preview}{'…' if len(cover_letter or '') > 300 else ''}"
        )
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Подать ✅", callback_data=f"apply:{job_id}"),
                InlineKeyboardButton("Пропустить ❌", callback_data=f"skip:{job_id}"),
            ]
        ])
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=keyboard)


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = get_stats()
    avg = f"{s['avg_score']:.1f}" if s["avg_score"] is not None else "—"
    await update.message.reply_text(
        f"📊 Статистика:\n"
        f"Всего вакансий: {s['total']}\n"
        f"Оценено: {s['scored']}\n"
        f"Средний score: {avg}\n"
        f"Подано заявок: {s['applied']}"
    )


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, job_id = query.data.split(":")
    job_id = int(job_id)

    if action == "apply":
        link = get_job_link(job_id)
        mark_applied(job_id)
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(f"Заявка отмечена ✅\n🔗 {link}")
    else:
        mark_applied(job_id)
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("Пропущено ❌")


def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("jobs", jobs))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CallbackQueryHandler(button))
    print("Бот запущен...")
    app.run_polling()


if __name__ == "__main__":
    main()
