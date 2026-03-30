import json
import os
import requests
from dotenv import load_dotenv
from groq import Groq
from resume_parser import load_resume

load_dotenv()

ADZUNA_APP_ID = os.environ.get("ADZUNA_APP_ID")
ADZUNA_APP_KEY = os.environ.get("ADZUNA_APP_KEY")
BASE_URL = "https://api.adzuna.com/v1/api/jobs/pl/search/1"

_groq = Groq(api_key=os.environ.get("GROQ_API_KEY"))


def build_queries(resume_text: str, city: str) -> tuple[list[str], bool]:
    """Use Groq to generate 5 job search terms from resume.
    Returns (queries, used_fallback)."""
    prompt = f"""Analyze this resume and return a JSON array of 5 short job search strings
for junior/intern IT positions in {city}, Poland.
Each string is a "what" keyword for a job search API (2-4 words max).
Examples: "junior python developer", "data analyst intern", "sql junior".
Always include at least one Polish term like "stażysta programista".

Resume:
{resume_text}

Return ONLY a valid JSON array of strings. No explanation."""

    try:
        response = _groq.chat.completions.create(
            model="llama-3.1-8b-instant",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}]
        )
        queries = json.loads(response.choices[0].message.content.strip())
        if isinstance(queries, list) and queries:
            return queries, False
    except Exception as e:
        print(f"[Scraper] Не удалось сгенерировать запросы через AI: {e}")

    return ["junior developer", "intern IT", "junior python", "stażysta programista"], True


def is_relevant(title: str) -> bool:
    title = title.lower()
    return any(word in title for word in [
        "intern", "junior", "trainee", "stażyst", "praktyk", "staż"
    ])


def search_jobs(city: str = "Warsaw") -> tuple[list[dict], bool]:
    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        print("[Scraper] Brak ADZUNA_APP_ID lub ADZUNA_APP_KEY w pliku .env")
        return [], False

    try:
        resume_text = load_resume()
    except FileNotFoundError:
        resume_text = ""
        print("[Scraper] resume.txt не найдено — используются базовые запросы.")

    queries, used_fallback = build_queries(resume_text, city)
    print(f"[Scraper] Запросов: {len(queries)}{' (fallback)' if used_fallback else ''}")

    jobs = []
    seen_links = set()
    tech_keywords = [
        "Python", "SQL", "Java", "JavaScript", "TypeScript", "React", "Django",
        "Flask", "FastAPI", "PostgreSQL", "MongoDB", "Docker", "Git",
        "Power BI", "Excel", "R", "Machine Learning", "pandas", "scikit-learn",
        "Alteryx", "Tableau", "Spark", "C#", "C++", "Go", "Kotlin", "Swift",
    ]

    for query in queries:
        print(f"  Ищу: {query}")
        params = {
            "app_id": ADZUNA_APP_ID,
            "app_key": ADZUNA_APP_KEY,
            "results_per_page": 50,
            "what": query,
            "where": city,
            "content-type": "application/json",
        }
        try:
            response = requests.get(BASE_URL, params=params, timeout=15)
            response.raise_for_status()
            results = response.json().get("results", [])

            for offer in results:
                title = offer.get("title", "")
                if not is_relevant(title):
                    continue

                link = offer.get("redirect_url", "")
                if not link or link in seen_links:
                    continue
                seen_links.add(link)

                description = (offer.get("description") or "")[:1500]
                found_tech = [t for t in tech_keywords if t.lower() in description.lower()]
                tech_stack = ", ".join(found_tech[:6])

                remote = "remote" in description.lower() or "zdaln" in description.lower()

                company = (offer.get("company") or {}).get("display_name", "Unknown")
                location = (offer.get("location") or {}).get("display_name", city)

                jobs.append({
                    "title": title,
                    "company": company,
                    "link": link,
                    "tech_stack": tech_stack,
                    "remote": remote,
                    "city": location,
                    "description": description,
                })

        except Exception as e:
            print(f"  [Ошибка] '{query}': {e}")

    print(f"\n[Scraper] Найдено уникальных вакансий: {len(jobs)}")
    return jobs, used_fallback
