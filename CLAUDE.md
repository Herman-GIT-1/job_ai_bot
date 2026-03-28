# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python-based job search automation bot for finding IT internships/junior positions, scoring them via AI, and generating personalized cover letters.

## Setup

```bash
pip install requests groq python-dotenv
```

Create `.env` in project root:
```
GROQ_API_KEY=<key from console.groq.com>
SERPAPI_KEY=<key from serpapi.com>
```

## Commands

```bash
python main.py --scrape   # Search jobs via SerpAPI → save to jobs.db
python main.py --score    # Score jobs with Groq AI + generate cover letters
python main.py --apply    # Open top-scored jobs (score >= 7) in browser
python main.py --all      # Run all three stages sequentially
```

## Architecture

Pipeline: **SerpAPI → scraper.py → database.py (SQLite) → ai_score.py + cover_letter.py → open_jobs.py → browser**

| Module | Role |
|---|---|
| `main.py` | CLI entry point (`argparse`), orchestrates pipeline stages |
| `scraper.py` | Fetches jobs from SerpAPI (Google Jobs engine), deduplicates, extracts tech stack keywords |
| `database.py` | SQLite wrapper (`jobs.db`): schema with score, cover_letter, applied columns |
| `ai_score.py` | Groq LLM (`llama3-8b-8192`) scores each job 0–10 based on `resume.txt` |
| `cover_letter.py` | Groq LLM generates 100–120 word tailored cover letters per job |
| `open_jobs.py` | Opens jobs with score ≥ 7 in browser, marks applied after manual confirmation |

## Key Details

- **Resume context** — `resume.txt` is read by both `ai_score.py` and `cover_letter.py` and injected into prompts. Updating this file changes how all future scoring/letters behave.
- **Database schema** — `jobs` table columns: `id, title, company, link, tech_stack, remote, city, score, cover_letter, applied`. No migrations system — schema changes require manual `ALTER TABLE` or deleting `jobs.db`.
- **SerpAPI quota** — 100 free requests/month. `scraper.py` runs 6 keyword searches per invocation, consuming 6 requests.
- **No test suite** — manual testing only; run commands directly to verify behavior.
