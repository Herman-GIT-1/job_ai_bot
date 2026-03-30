import json
import os
import requests
from dotenv import load_dotenv
from groq import Groq
from resume_parser import load_resume

load_dotenv()

ADZUNA_APP_ID = os.environ.get("ADZUNA_APP_ID")
ADZUNA_APP_KEY = os.environ.get("ADZUNA_APP_KEY")
ADZUNA_BASE_URL = "https://api.adzuna.com/v1/api/jobs/pl/search/1"
JUSTJOIN_URL = "https://justjoin.it/api/offers"
REMOTIVE_URL = "https://remotive.com/api/remote-jobs"

_groq = Groq(api_key=os.environ.get("GROQ_API_KEY"))

TECH_KEYWORDS = [
    "Python", "SQL", "Java", "JavaScript", "TypeScript", "React", "Django",
    "Flask", "FastAPI", "PostgreSQL", "MongoDB", "Docker", "Git",
    "Power BI", "Excel", "R", "Machine Learning", "pandas", "scikit-learn",
    "Alteryx", "Tableau", "Spark", "C#", "C++", "Go", "Kotlin", "Swift",
]

JUNIOR_KEYWORDS = ["intern", "junior", "trainee", "stażyst", "praktyk", "staż"]


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


def _is_junior(title: str) -> bool:
    t = title.lower()
    return any(w in t for w in JUNIOR_KEYWORDS)


def _extract_tech(text: str) -> str:
    found = [t for t in TECH_KEYWORDS if t.lower() in text.lower()]
    return ", ".join(found[:6])


def _fetch_adzuna(queries: list[str], city: str) -> list[dict]:
    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        print("[Adzuna] Нет ADZUNA_APP_ID или ADZUNA_APP_KEY — источник пропущен.")
        return []

    jobs = []
    for query in queries:
        print(f"  [Adzuna] Ищу: {query}")
        params = {
            "app_id": ADZUNA_APP_ID,
            "app_key": ADZUNA_APP_KEY,
            "results_per_page": 50,
            "what": query,
            "where": city,
            "content-type": "application/json",
        }
        try:
            r = requests.get(ADZUNA_BASE_URL, params=params, timeout=15)
            r.raise_for_status()
            for offer in r.json().get("results", []):
                title = offer.get("title", "")
                if not _is_junior(title):
                    continue
                link = offer.get("redirect_url", "")
                if not link:
                    continue
                description = (offer.get("description") or "")[:1500]
                jobs.append({
                    "title": title,
                    "company": (offer.get("company") or {}).get("display_name", "Unknown"),
                    "link": link,
                    "tech_stack": _extract_tech(description),
                    "remote": "remote" in description.lower() or "zdaln" in description.lower(),
                    "city": (offer.get("location") or {}).get("display_name", city),
                    "description": description,
                    "_source": "Adzuna",
                })
        except Exception as e:
            print(f"  [Adzuna] Ошибка '{query}': {e}")

    return jobs


def _fetch_justjoin(city: str) -> list[dict]:
    print(f"  [JustJoin] Ищу вакансии в {city}...")
    try:
        r = requests.get(JUSTJOIN_URL, timeout=20)
        r.raise_for_status()
        all_offers = r.json()
    except Exception as e:
        print(f"  [JustJoin] Недоступен: {e}")
        return []

    city_lower = city.lower()
    jobs = []
    for offer in all_offers:
        title = offer.get("title", "")
        if not _is_junior(title):
            exp = (offer.get("experienceLevel") or "").lower()
            if exp not in ("junior", "intern"):
                continue

        offer_city = (offer.get("city") or "").lower()
        remote_ok = offer.get("remote", False)
        if not remote_ok and city_lower not in offer_city:
            continue

        link = f"https://justjoin.it/offers/{offer.get('id', '')}"
        skills = offer.get("skills") or []
        tech_stack = ", ".join(s.get("name", "") for s in skills[:6] if s.get("name"))
        description = (offer.get("body") or offer.get("description") or "")[:1500]

        jobs.append({
            "title": title,
            "company": offer.get("companyName", "Unknown"),
            "link": link,
            "tech_stack": tech_stack or _extract_tech(description),
            "remote": remote_ok,
            "city": offer.get("city", city),
            "description": description,
            "_source": "JustJoin",
        })

    print(f"  [JustJoin] Найдено подходящих: {len(jobs)}")
    return jobs


def _fetch_remotive(city: str) -> list[dict]:
    """Remotive — remote IT jobs worldwide, no API key needed."""
    print("  [Remotive] Ищу remote вакансии...")
    try:
        r = requests.get(
            REMOTIVE_URL,
            params={"category": "software-dev", "limit": 100},
            timeout=15,
        )
        r.raise_for_status()
        offers = r.json().get("jobs", [])
    except Exception as e:
        print(f"  [Remotive] Недоступен: {e}")
        return []

    jobs = []
    for offer in offers:
        title = offer.get("title", "")
        if not _is_junior(title):
            continue
        link = offer.get("url", "")
        if not link:
            continue
        description = (offer.get("description") or "")[:1500]
        jobs.append({
            "title": title,
            "company": offer.get("company_name", "Unknown"),
            "link": link,
            "tech_stack": _extract_tech(description),
            "remote": True,
            "city": "Remote",
            "description": description,
            "_source": "Remotive",
        })

    print(f"  [Remotive] Найдено подходящих: {len(jobs)}")
    return jobs


def search_jobs(city: str = "Warsaw") -> tuple[list[dict], bool]:
    try:
        resume_text = load_resume()
    except FileNotFoundError:
        resume_text = ""
        print("[Scraper] resume.txt не найдено — используются базовые запросы.")

    queries, used_fallback = build_queries(resume_text, city)
    print(f"[Scraper] Запросов для Adzuna: {len(queries)}{' (fallback)' if used_fallback else ''}")

    raw = []
    raw.extend(_fetch_adzuna(queries, city))
    raw.extend(_fetch_justjoin(city))
    raw.extend(_fetch_remotive(city))

    # Deduplicate by link
    seen = set()
    jobs = []
    for job in raw:
        link = job["link"]
        if link and link not in seen:
            seen.add(link)
            job.pop("_source", None)
            jobs.append(job)

    print(f"\n[Scraper] Итого уникальных вакансий: {len(jobs)}")
    return jobs, used_fallback
