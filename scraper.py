import json
import os
import time
import requests
from dotenv import load_dotenv
from anthropic import Anthropic
from resume_parser import load_resume

load_dotenv()

ADZUNA_APP_ID = os.environ.get("ADZUNA_APP_ID")
ADZUNA_APP_KEY = os.environ.get("ADZUNA_APP_KEY")
ADZUNA_BASE_URL = "https://api.adzuna.com/v1/api/jobs/pl/search/1"
JUSTJOIN_URL = "https://justjoin.it/api/offers"
REMOTIVE_URL = "https://remotive.com/api/remote-jobs"
NFJ_SEARCH_URL = "https://nofluffjobs.com/api/search/posting?salaryCurrency=PLN&salaryPeriod=month"
NFJ_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "Origin": "https://nofluffjobs.com",
    "Referer": "https://nofluffjobs.com/pl/praca",
}

_claude = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

TECH_KEYWORDS = [
    "Python", "SQL", "Java", "JavaScript", "TypeScript", "React", "Django",
    "Flask", "FastAPI", "PostgreSQL", "MongoDB", "Docker", "Git",
    "Power BI", "Excel", "R", "Machine Learning", "pandas", "scikit-learn",
    "Alteryx", "Tableau", "Spark", "C#", "C++", "Go", "Kotlin", "Swift",
]

JUNIOR_KEYWORDS = ["intern", "junior", "trainee", "stażyst", "praktyk", "staż"]


def build_queries(resume_text: str, city: str) -> tuple[list[str], bool]:
    """Use Claude to generate 5 job search terms from resume.
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
        response = _claude.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}]
        )
        queries = json.loads(response.content[0].text.strip())
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
        time.sleep(0.5)  # avoid hammering Adzuna between queries

    return jobs


def _city_to_nfj_slug(city: str) -> str:
    """Warsaw / Warszawa / Kraków → warszawa / krakow for NoFluffJobs criteria."""
    slug = city.lower().split(",")[0].strip()
    for pl, en in [("ą","a"),("ć","c"),("ę","e"),("ł","l"),("ń","n"),("ó","o"),("ś","s"),("ź","z"),("ż","z")]:
        slug = slug.replace(pl, en)
    return slug


def _fetch_nofluffjobs(city: str) -> list[dict]:
    """NoFluffJobs — Polish IT jobs, no API key needed."""
    city_slug = _city_to_nfj_slug(city)
    print(f"  [NoFluffJobs] Ищу junior/intern в {city} (slug: {city_slug})...")

    jobs = []
    page = 1
    total_pages = 1

    while page <= total_pages and page <= 5:  # cap at 250 jobs
        body = {
            "criteriaSearch": {"city": [city_slug], "requirement": ["junior"]},
            "page": page,
            "pageSize": 50,
        }
        try:
            r = requests.post(NFJ_SEARCH_URL, headers=NFJ_HEADERS, json=body, timeout=15)
            r.raise_for_status()
            data = r.json()
            if page == 1:
                total_pages = data.get("totalPages", 1)
                print(f"  [NoFluffJobs] Всего: {data.get('totalCount', 0)} вакансий, {total_pages} стр.")

            for p in data.get("postings", []):
                seniority = [s.lower() for s in (p.get("seniority") or [])]
                if not any(s in ("junior", "intern", "trainee") for s in seniority):
                    continue

                title = p.get("title", "")
                places = (p.get("location") or {}).get("places") or []
                url_slug = places[0].get("url", p.get("id", "")) if places else p.get("id", "")
                link = f"https://nofluffjobs.com/pl/oferta-pracy/{url_slug}"

                tiles = (p.get("tiles") or {}).get("values") or []
                tech = [t["value"] for t in tiles if t.get("type") == "requirement"]
                tech_stack = ", ".join(tech[:8])
                description = f"Required skills: {', '.join(tech)}." if tech else ""

                offer_city = places[0].get("city", city) if places else city
                remote = (p.get("location") or {}).get("fullyRemote", False)

                jobs.append({
                    "title": title,
                    "company": p.get("name", "Unknown"),
                    "link": link,
                    "tech_stack": tech_stack,
                    "remote": remote,
                    "city": offer_city,
                    "description": description,
                    "_source": "NoFluffJobs",
                })
        except Exception as e:
            print(f"  [NoFluffJobs] Ошибка стр. {page}: {e}")
            break
        page += 1

    print(f"  [NoFluffJobs] Найдено подходящих: {len(jobs)}")
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
    raw.extend(_fetch_nofluffjobs(city))
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
