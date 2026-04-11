import html
import json
import logging
import os
import re
import time
import requests
from dotenv import load_dotenv
from anthropic import Anthropic
from config import MODEL_QUERY_BUILDER, TECH_KEYWORDS
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

# TECH_KEYWORDS is imported from config.py — edit the domain registry there.

JUNIOR_KEYWORDS = [
    "intern", "junior", "trainee", "stażyst", "praktyk", "staż",
    "absolwent", "młodszy", "entry-level", "entry level", "graduate",
    "associate", "bez doświadczenia", "apprentice",
    # entry-level signals common in finance/non-IT job descriptions
    "recent graduate", "fresh graduate", "dla absolwent", "dla studenta",
    "0-2 lat", "do 2 lat", "0-1 rok", "no experience required",
]

# Query-level keywords that signal the search is already targeting juniors.
# When present in the query, we trust the search engine and skip title-level filtering.
_JUNIOR_QUERY_WORDS = {
    "junior", "intern", "stażysta", "praktyk", "trainee",
    "młodszy", "absolwent", "entry",
}

# Remotive API categories — used for dynamic category selection
REMOTIVE_CATEGORIES = [
    "software-dev", "data", "marketing", "design", "devops",
    "finance", "product", "writing", "hr", "qa", "all-others",
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

"queries": array of 6 short job search strings (2-5 words each) for a job search API.
  Rules:
  - Base ALL queries on the person's ACTUAL field, skills, and experience — do NOT default to IT.
  - 3 queries must contain a junior-level word: "junior", "młodszy", "trainee", or "associate"
  - 3 queries must contain an intern-level word: "intern", "stażysta", or "praktykant"
  - Match the person's real domain: finance → "junior financial analyst"; banking → "junior operations analyst"; marketing → "junior marketing specialist"; IT → "junior python developer"
  - For finance/banking profiles use real industry titles: analyst, specialist, operations, risk, compliance, settlements, reconciliation, treasury, AML, KYC
  - For experienced candidates apply junior prefix to their specialisation, not generic roles
  - NEVER output: driver, cashier, warehouse, security, delivery, cook, waiter, bartender

"remotive_categories": array of 1-3 Remotive API category slugs that best match this resume.
  Choose ONLY from: {REMOTIVE_CATEGORIES}
  For finance/banking profiles prefer: "finance". For IT: "software-dev" or "data".

Examples by profile:
  Python dev:     ["junior python developer", "junior data engineer", "intern python", "data analyst intern", "stażysta python", "praktykant programista"]
  Finance/Banking:["junior financial analyst", "junior operations analyst", "junior risk analyst", "intern finance", "stażysta analityk", "praktykant finansowy"]
  Marketing:      ["junior marketing specialist", "junior social media", "junior copywriter", "marketing intern", "stażysta marketing", "praktykant content"]
  Data/BI:        ["junior data analyst", "junior bi analyst", "junior sql analyst", "data analyst intern", "stażysta analityk danych", "intern business intelligence"]

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


def _is_junior(title: str, description: str = "") -> bool:
    """True if the job seems entry-level and not in an excluded category.
    Checks title first; falls back to description for non-IT fields where
    job titles rarely contain 'junior' (e.g. finance, marketing).
    """
    title_lower = title.lower()
    if any(w in title_lower for w in _EXCLUDED_TITLE_KEYWORDS):
        return False
    combined = title_lower + " " + description[:400].lower()
    return any(w in combined for w in JUNIOR_KEYWORDS)


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
        # If the query already targets juniors (e.g. "junior financial analyst"),
        # the search engine already filtered by seniority — don't double-filter by title.
        # Only exclude irrelevant job categories. Otherwise apply the full _is_junior check.
        query_targets_junior = any(w in query.lower() for w in _JUNIOR_QUERY_WORDS)
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
                link = offer.get("redirect_url", "")
                if not link:
                    continue
                description = _strip_html(offer.get("description") or "")
                if query_targets_junior:
                    # Trust the query; only exclude blacklisted categories
                    if any(w in title.lower() for w in _EXCLUDED_TITLE_KEYWORDS):
                        continue
                else:
                    if not _is_junior(title, description):
                        continue
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
            link = offer.get("url", "")
            if not link or link in seen_links:
                continue
            description = _strip_html(offer.get("description") or "")
            if not _is_junior(title, description):
                continue
            seen_links.add(link)
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

    # Deduplicate by link first, then by (title, company) to catch
    # same job appearing on JustJoin + RocketJobs (same backend, different domains)
    # or Adzuna returning the same job across multiple queries with different redirect URLs.
    seen_links: set[str] = set()
    seen_pairs: set[tuple] = set()
    jobs = []
    for job in raw:
        link = job["link"]
        pair = (job["title"].lower().strip(), job["company"].lower().strip())
        if not link:
            continue
        if link in seen_links or pair in seen_pairs:
            continue
        seen_links.add(link)
        seen_pairs.add(pair)
        jobs.append(job)

    logger.info("Итого уникальных вакансий: %d (из %d сырых)", len(jobs), len(raw))
    return jobs, used_fallback
