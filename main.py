from dotenv import load_dotenv
load_dotenv()

import argparse
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
from scraper import search_jobs
from database import save_job, get_jobs, update_job, count_jobs, CLI_CHAT_ID
from ai_score import evaluate
from cover_letter import generate_letter
from open_jobs import open_jobs
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


def run_apply(min_score: int = 7) -> None:
    print(f"=== Opening top jobs in browser (score >= {min_score}) ===")
    open_jobs(min_score)


def run_bot() -> None:
    import bot
    bot.main()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Job Search Bot — CLI",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--scrape", action="store_true", help="Fetch jobs and save to DB")
    parser.add_argument("--score",  action="store_true", help="AI-score jobs + generate cover letters")
    parser.add_argument("--apply",  action="store_true", help="Open top jobs in browser")
    parser.add_argument("--bot",    action="store_true", help="Start Telegram bot")
    parser.add_argument("--all",    action="store_true", help="Run scrape → score → apply")
    parser.add_argument(
        "--city",
        default="Warsaw",
        metavar="CITY",
        help="City to search in (default: Warsaw). Used with --scrape and --all.",
    )
    parser.add_argument(
        "--min-score",
        type=int,
        default=7,
        metavar="N",
        dest="min_score",
        help="Minimum score threshold for --apply (default: 7).",
    )
    args = parser.parse_args()

    if not any([args.scrape, args.score, args.apply, args.bot, args.all]):
        parser.print_help()
        return

    if args.bot:
        run_bot()
        return

    if args.all or args.scrape:
        run_scrape(args.city)
    if args.all or args.score:
        run_score()
    if args.all or args.apply:
        run_apply(args.min_score)


if __name__ == "__main__":
    main()
