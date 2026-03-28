import argparse
from scraper import search_jobs
from database import save_job, get_jobs, update_job
from ai_score import evaluate
from cover_letter import generate_letter as generate
from open_jobs import open_jobs

def run_scrape():
    print("=== Поиск вакансий через SerpAPI ===")
    jobs = search_jobs()
    print(f"Сохраняем в базу...")
    for job in jobs:
        save_job(job)
    print(f"Готово. {len(jobs)} вакансий добавлено.")

def run_score():
    print("=== AI оценка и генерация cover letter ===")
    pending = get_jobs()
    if not pending:
        print("Нет вакансий для оценки.")
        return
    print(f"Оцениваем {len(pending)} вакансий...\n")
    for job in pending:
        job_id, title, company, link, tech_stack = job
        print(f"Analyzing: {title} @ {company}")
        score = evaluate({"title": title, "company": company, "tech_stack": tech_stack})
        letter = generate({"title": title, "company": company, "tech_stack": tech_stack})
        update_job(job_id, score, letter)
        print(f"Score: {score}/10")

def run_apply():
    print("=== Открываем лучшие вакансии (score >= 7) ===")
    open_jobs()

def run_bot():
    import bot
    bot.main()

def main():
    parser = argparse.ArgumentParser(
        description="Job Search Automation",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--scrape", action="store_true", help="Найти вакансии и сохранить в БД")
    parser.add_argument("--score",  action="store_true", help="AI-оценка и генерация cover letter")
    parser.add_argument("--apply",  action="store_true", help="Открыть лучшие вакансии (score >= 7)")
    parser.add_argument("--all",    action="store_true", help="Запустить все этапы подряд")
    parser.add_argument("--bot",    action="store_true", help="Запустить Telegram-бот")
    args = parser.parse_args()

    if not any(vars(args).values()):
        parser.print_help()
        return

    if args.bot:
        run_bot()
        return

    if args.all or args.scrape:
        run_scrape()
    if args.all or args.score:
        run_score()
    if args.all or args.apply:
        run_apply()

if __name__ == "__main__":
    main()