from dotenv import load_dotenv
load_dotenv()

import argparse
import logging
import os

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
from scraper import search_jobs
from database import save_job, get_jobs, update_job, count_jobs, CLI_CHAT_ID
from ai_score import evaluate
from cover_letter import generate_letter
from resume_parser import load_resume


def run_scrape(city: str = "Warsaw") -> None:
    print(f"=== Scraping jobs — {city} (Adzuna + NoFluffJobs + Remotive) ===")
    before = count_jobs(CLI_CHAT_ID)
    jobs, used_fallback = search_jobs(city)
    if used_fallback:
        print("[!] AI query builder failed — using generic fallback queries.")
    for job in jobs:
        save_job(job, CLI_CHAT_ID)
    saved = count_jobs(CLI_CHAT_ID) - before
    print(f"Done. Found: {len(jobs)}, new in DB: {saved}.")


def run_score(min_letter_score: int = 7) -> None:
    print("=== AI scoring + cover letter generation ===")
    pending = get_jobs(CLI_CHAT_ID)
    if not pending:
        print("No unscored jobs. Run --scrape first.")
        return

    resume = load_resume(CLI_CHAT_ID)
    total = len(pending)
    print(f"Scoring {total} jobs...\n")

    for i, (job_id, title, company, _, tech_stack, description) in enumerate(pending, 1):
        job_dict = {
            "title": title,
            "company": company,
            "tech_stack": tech_stack,
            "description": description,
        }
        score = evaluate(job_dict, resume=resume)
        letter = generate_letter(job_dict, resume=resume) if score >= min_letter_score else ""
        update_job(job_id, CLI_CHAT_ID, score, letter)
        print(f"[{i}/{total}] {title} @ {company} — {score}/10")

    print("\nDone.")


def run_bot() -> None:
    import threading
    import uvicorn
    from webapp import app as web_app

    port = int(os.environ.get("PORT", 8000))
    t = threading.Thread(
        target=lambda: uvicorn.run(web_app, host="0.0.0.0", port=port, log_level="warning"),
        daemon=True,
    )
    t.start()
    logging.getLogger(__name__).info("Mini App server started on port %d", port)

    import bot
    bot.main()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Job Search Bot — CLI",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--scrape", action="store_true", help="Fetch jobs and save to DB")
    parser.add_argument("--score",  action="store_true", help="AI-score jobs + generate cover letters")
    parser.add_argument("--bot",    action="store_true", help="Start Telegram bot")
    parser.add_argument("--all",    action="store_true", help="Run scrape → score")
    parser.add_argument(
        "--city",
        default="Warsaw",
        metavar="CITY",
        help="City to search in (default: Warsaw). Used with --scrape and --all.",
    )
    args = parser.parse_args()

    if not any([args.scrape, args.score, args.bot, args.all]):
        parser.print_help()
        return

    if args.bot:
        run_bot()
        return

    if args.all or args.scrape:
        run_scrape(args.city)
    if args.all or args.score:
        run_score()


if __name__ == "__main__":
    main()
