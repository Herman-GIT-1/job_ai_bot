import html
import json
import logging
import os
import re
import time
import requests
from dotenv import load_dotenv
from anthropic import Anthropic
from config import MODEL_QUERY_BUILDER
from resume_parser import load_resume

load_dotenv()

logger = logging.getLogger(__name__)

ADZUNA_APP_ID = os.environ.get("ADZUNA_APP_ID")
ADZUNA_APP_KEY = os.environ.get("ADZUNA_APP_KEY")
ADZUNA_BASE_URL = "https://api.adzuna.com/v1/api/jobs/pl/search/1"
JUSTJOIN_API = "https://justjoin.it/api/candidate-api/offers"
ROCKETJOBS_API = "https://rocketjobs.pl/api/candidate-api/offers"
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


def _strip_html(text: str, max_len: int = 1500) -> str:
    """Strip HTML tags, decode entities, collapse whitespace."""
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<li\s*/?>", "\n• ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()[:max_len]

TECH_KEYWORDS = [
    "Python", "SQL", "Java", "JavaScript", "TypeScript", "React", "Django",
    "Flask", "FastAPI", "PostgreSQL", "MongoDB", "Docker", "Git",
    "Power BI", "Excel", "R", "Machine Learning", "pandas", "scikit-learn",
    "Alteryx", "Tableau", "Spark", "C#", "C++", "Go", "Kotlin", "Swift",
]

JUNIOR_KEYWORDS = [
    "intern", "junior", "trainee", "stażyst", "praktyk", "staż",
    "absolwent", "młodszy", "entry-level", "entry level", "graduate",
    "associate", "bez doświadczenia", "apprentice",
]

# Remotive API categories — used for dynamic category selection
REMOTIVE_CATEGORIES = [
    "software-dev", "data", "marketing", "design", "devops",
    "finance", "product", "writing", "hr", "qa",
]

# Job titles to exclude — irrelevant for students regardless of "junior" label
_EXCLUDED_TITLE_KEYWORDS = [
    "driver", "kierowca", "cashier", "kasjer", "cleaner", "sprzątacz",
    "warehouse", "magazyn", "security", "ochroniar", "delivery", "kurier",
    "waiter", "kelner", "cook", "kucharz", "barista", "bartender",
]


def build_queries(resume_text: str, city: str) -> tuple[list[str], bool, list[str]]:
    """Use Claude to generate job search terms and Remotive categories from resume.
    Returns (queries, used_fallback, remotive_categories)."""
    prompt = f"""Analyze this resume and return a JSON object with two keys:
- "queries": array of 6 short job search strings for positions in {city}, Poland, based on the person's skills, split evenly:
    * 3 strings for JUNIOR roles  — start with "junior" or "młodszy"
    * 3 strings for INTERN roles  — start with "intern", "stażysta", or "praktykant"
  Each string is a "what" keyword for a job search API (2-4 words max).
  Base ALL 6 on the person's actual field of study and skills — do NOT restrict to IT.
  Examples for various profiles:
    IT student:         "junior python developer", "intern python developer", "junior data analyst",     "data analyst intern"
    Marketing student:  "junior marketing specialist", "junior copywriter",   "marketing intern"
    Finance student:    "junior financial analyst", "junior accountant",      "stażysta analityk"
    Design student:     "junior graphic designer", "junior ux designer",      "praktykant grafika"
  NEVER include jobs like driver, cashier, warehouse, security, delivery, cook, waiter.

- "remotive_categories": array of 1-3 Remotive API category slugs that best match this resume.
  Choose ONLY from: {REMOTIVE_CATEGORIES}

Resume:
{resume_text}

Return ONLY a valid JSON object. No explanation."""

    try:
        response = _claude.messages.create(
            model=MODEL_QUERY_BUILDER,
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = response.content[0].text.strip()
        # Strip markdown code fences if Claude wrapped the JSON
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        result = json.loads(raw)
        queries = result.get("queries", [])
        categories = result.get("remotive_categories", ["software-dev"])
        if isinstance(queries, list) and queries:
            # Validate categories against known list
            categories = [c for c in categories if c in REMOTIVE_CATEGORIES] or ["software-dev"]
            return queries, False, categories
    except Exception as e:
        logger.warning("Не удалось сгенерировать запросы через AI: %s", e)

    return ["junior developer", "intern IT", "junior python", "stażysta programista"], True, ["software-dev"]


def _is_junior(title: str) -> bool:
    t = title.lower()
    if any(w in t for w in _EXCLUDED_TITLE_KEYWORDS):
        return False
    return any(w in t for w in JUNIOR_KEYWORDS)


def _extract_tech(text: str) -> str:
    found = [t for t in TECH_KEYWORDS if t.lower() in text.lower()]
    return ", ".join(found[:6])


def _fetch_adzuna(queries: list[str], city: str) -> list[dict]:
    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        logger.info("Нет ADZUNA_APP_ID или ADZUNA_APP_KEY — источник пропущен.")
        return []

    jobs = []
    for query in queries:
        logger.info("[Adzuna] Ищу: %s", query)
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
                description = _strip_html(offer.get("description") or "")
                jobs.append({
                    "title": title,
                    "company": (offer.get("company") or {}).get("display_name", "Unknown"),
                    "link": link,
                    "tech_stack": _extract_tech(description),
                    "remote": "remote" in description.lower() or "zdaln" in description.lower(),
                    "city": (offer.get("location") or {}).get("display_name", city),
                    "description": description,
                    "source": "Adzuna",
                    "salary_min": offer.get("salary_min"),
                    "salary_max": offer.get("salary_max"),
                    "salary_currency": "GBP" if offer.get("salary_min") else None,
                })
        except Exception as e:
            logger.error("[Adzuna] Ошибка '%s': %s", query, e)
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
    logger.info("[NoFluffJobs] Ищу junior/intern в %s (slug: %s)...", city, city_slug)

    jobs = []
    page = 1
    total_pages = 1

    while page <= total_pages and page <= 5:  # cap at 250 jobs
        body = {
            "criteriaSearch": {"city": [city_slug], "requirement": ["junior", "intern", "trainee"]},
            "page": page,
            "pageSize": 50,
        }
        try:
            r = requests.post(NFJ_SEARCH_URL, headers=NFJ_HEADERS, json=body, timeout=15)
            r.raise_for_status()
            data = r.json()
            if page == 1:
                total_pages = data.get("totalPages", 1)
                logger.info("[NoFluffJobs] Всего: %d вакансий, %d стр.", data.get("totalCount", 0), total_pages)

            for p in data.get("postings", []):
                seniority = [s.lower() for s in (p.get("seniority") or [])]
                if not any(s in ("junior", "intern", "trainee") for s in seniority):
                    continue

                title = p.get("title", "")
                places = (p.get("location") or {}).get("places") or []
                url_slug = places[0].get("url", p.get("id", "")) if places else p.get("id", "")
                link = f"https://nofluffjobs.com/pl/job/{url_slug}"

                tiles = (p.get("tiles") or {}).get("values") or []
                tech = [t["value"] for t in tiles if t.get("type") == "requirement"]
                tech_stack = ", ".join(tech[:8])
                description = f"Required skills: {', '.join(tech)}." if tech else ""

                offer_city = places[0].get("city", city) if places else city
                remote = (p.get("location") or {}).get("fullyRemote", False)

                salary = p.get("salary") or {}
                jobs.append({
                    "title": title,
                    "company": p.get("name", "Unknown"),
                    "link": link,
                    "tech_stack": tech_stack,
                    "remote": remote,
                    "city": offer_city,
                    "description": description,
                    "source": "NoFluffJobs",
                    "salary_min": salary.get("from"),
                    "salary_max": salary.get("to"),
                    "salary_currency": salary.get("currency", "PLN") if salary.get("from") else None,
                })
        except Exception as e:
            logger.error("[NoFluffJobs] Ошибка стр. %d: %s", page, e)
            break
        page += 1

    logger.info("[NoFluffJobs] Найдено подходящих: %d", len(jobs))
    return jobs


def _fetch_remotive(categories: list[str]) -> list[dict]:
    """Remotive — remote jobs worldwide, no API key needed.
    Queries each category from the provided list."""
    jobs = []
    seen_links: set[str] = set()

    for category in categories:
        logger.info("[Remotive] Ищу категорию: %s...", category)
        try:
            r = requests.get(
                REMOTIVE_URL,
                params={"category": category, "limit": 100},
                timeout=15,
            )
            r.raise_for_status()
            offers = r.json().get("jobs", [])
        except Exception as e:
            logger.error("[Remotive] Ошибка категории '%s': %s", category, e)
            continue

        for offer in offers:
            title = offer.get("title", "")
            if not _is_junior(title):
                continue
            link = offer.get("url", "")
            if not link or link in seen_links:
                continue
            seen_links.add(link)
            description = _strip_html(offer.get("description") or "")
            jobs.append({
                "title": title,
                "company": offer.get("company_name", "Unknown"),
                "link": link,
                "tech_stack": _extract_tech(description),
                "remote": True,
                "city": "Remote",
                "description": description,
                "source": "Remotive",
                "salary_min": None,
                "salary_max": None,
                "salary_currency": None,
            })

    logger.info("[Remotive] Найдено подходящих: %d", len(jobs))
    return jobs


def _fetch_jjit_api(api_url: str, city_slug: str, source: str, base_url: str) -> list[dict]:
    """Общий fetcher для justjoin.it и rocketjobs.pl — внутренний Next.js API.
    Город не передаём в API (city-фильтр ненадёжен), фильтруем клиентски.
    """
    jobs = []
    seen_slugs: set[str] = set()

    for page in range(1, 11):  # максимум 500 вакансий
        try:
            r = requests.get(
                api_url,
                params={
                    "experienceLevel[]": ["junior", "intern"],
                    "limit": 50,
                    "page": page,
                },
                timeout=15,
            )
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            logger.error("[%s] Ошибка стр. %d: %s", source, page, e)
            break

        offers = data.get("data", [])
        if not offers:
            break

        for item in offers:
            slug = item.get("slug", "")
            if not slug or slug in seen_slugs:
                continue
            title = item.get("title", "")
            if any(w in title.lower() for w in _EXCLUDED_TITLE_KEYWORDS):
                continue

            # Принимаем вакансию если она remote ИЛИ в целевом городе
            is_remote = item.get("workplaceType") == "remote"
            offer_cities = [_city_to_nfj_slug(item.get("city") or "")]
            offer_cities += [_city_to_nfj_slug(loc.get("city", "")) for loc in (item.get("locations") or [])]
            if not is_remote and city_slug not in offer_cities:
                continue

            seen_slugs.add(slug)
            emp = (item.get("employmentTypes") or [{}])[0]
            skills = [s["name"] for s in (item.get("requiredSkills") or [])]
            description = f"Required skills: {', '.join(skills)}." if skills else ""

            jobs.append({
                "title": title,
                "company": item.get("companyName", "Unknown"),
                "link": f"{base_url}{slug}",
                "tech_stack": ", ".join(skills[:6]),
                "remote": is_remote,
                "city": item.get("city") or city_slug,
                "description": description,
                "source": source,
                "salary_min": emp.get("from"),
                "salary_max": emp.get("to"),
                "salary_currency": emp.get("currency") if emp.get("from") else None,
            })

        if not (data.get("meta") or {}).get("next"):
            break

    logger.info("[%s] Найдено подходящих: %d", source, len(jobs))
    return jobs


def _fetch_justjoin(city: str) -> list[dict]:
    """JustJoin.it — внутренний Next.js API, авторизация не нужна."""
    logger.info("[JustJoin] Ищу junior/intern в %s...", city)
    return _fetch_jjit_api(JUSTJOIN_API, _city_to_nfj_slug(city), "JustJoin", "https://justjoin.it/job-offer/")


def _fetch_rocketjobs(city: str) -> list[dict]:
    """RocketJobs — тот же API-бэкенд что и JustJoin (одна компания)."""
    logger.info("[RocketJobs] Ищу junior/intern в %s...", city)
    return _fetch_jjit_api(ROCKETJOBS_API, _city_to_nfj_slug(city), "RocketJobs", "https://rocketjobs.pl/job-offer/")


def search_jobs(city: str = "Warsaw", chat_id: int = 0) -> tuple[list[dict], bool]:
    try:
        resume_text = load_resume(chat_id)
    except FileNotFoundError:
        resume_text = ""
        logger.warning("resume.txt не найдено — используются базовые запросы.")

    queries, used_fallback, remotive_categories = build_queries(resume_text, city)
    logger.info("Запросов для Adzuna: %d%s", len(queries), " (fallback)" if used_fallback else "")
    logger.info("Категории Remotive: %s", remotive_categories)

    raw = []
    raw.extend(_fetch_adzuna(queries, city))
    raw.extend(_fetch_nofluffjobs(city))
    raw.extend(_fetch_justjoin(city))
    raw.extend(_fetch_rocketjobs(city))
    raw.extend(_fetch_remotive(remotive_categories))

    # Deduplicate by link
    seen = set()
    jobs = []
    for job in raw:
        link = job["link"]
        if link and link not in seen:
            seen.add(link)
            jobs.append(job)

    logger.info("Итого уникальных вакансий: %d", len(jobs))
    return jobs, used_fallback
