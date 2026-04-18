import hashlib
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


def _normalize_title(title: str) -> str:
    """Strip trailing location/remote annotations from job title for dedup."""
    t = title.lower().strip()
    t = re.sub(
        r'\s*[-|(/]\s*'
        r'(warsaw|warszawa|krak[oó]w|wroclaw|wrocław|gdańsk|gdansk'
        r'|poznań|poznan|łódź|lodz|katowice|remote|zdalnie|hybrid).*$',
        '', t, flags=re.IGNORECASE,
    )
    return re.sub(r'\s+', ' ', t).strip()


def _dedup_hash(company: str, title: str, city: str) -> str:
    """MD5 hash of normalized (company|title|city) for cross-source dedup."""
    key = f"{company.lower().strip()}|{_normalize_title(title)}|{city.lower().strip()}"
    return hashlib.md5(key.encode()).hexdigest()


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

# Seniority keywords a user can add as custom filters to switch from junior to senior mode.
_SENIOR_SENIORITY = {"senior", "mid", "regular", "lead", "principal", "staff", "expert"}

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


def build_queries(resume_text: str, city: str, skills: list[str] = None) -> tuple[list[str], bool, list[str]]:
    """Use Claude to generate job search terms and Remotive categories from resume + user filters.
    Returns (queries, used_fallback, remotive_categories)."""
    seniority  = _detect_seniority(skills)
    is_senior  = seniority == "senior"
    specialties = _specialty_list(skills)

    specialty_line = (
        f"User's selected specialties/keywords (prioritise these over resume): {', '.join(specialties)}"
        if specialties
        else "Base ALL queries on the person's ACTUAL field, skills, and experience — do NOT default to IT."
    )

    if is_senior:
        seniority_rules = (
            '- Generate queries for EXPERIENCED professionals — no junior/intern words\n'
            '- 4 queries must use "senior" prefix: "senior python developer", "senior financial analyst"\n'
            '- 2 queries without seniority prefix (role only, implying experienced level)\n'
            '- NEVER use: junior, intern, stażysta, praktykant, trainee, associate, entry'
        )
        examples = (
            '  Python dev:      ["senior python developer", "senior backend engineer", "senior data engineer", "python developer", "backend engineer", "software engineer"]\n'
            '  Finance/Banking: ["senior financial analyst", "senior risk analyst", "senior compliance officer", "financial analyst", "risk manager", "treasury manager"]\n'
            '  Marketing:       ["senior marketing specialist", "senior SEO specialist", "senior content strategist", "marketing manager", "brand manager", "digital marketing"]\n'
            '  Data/BI:         ["senior data analyst", "senior BI analyst", "senior data engineer", "data engineer", "BI developer", "analytics engineer"]'
        )
        fallback = ["senior developer", "senior python developer", "senior data analyst",
                    "senior financial analyst", "python developer", "data analyst"]
    else:
        seniority_rules = (
            '- 3 queries must contain a junior-level word: "junior", "młodszy", "trainee", or "associate"\n'
            '- 3 queries must contain an intern-level word: "intern", "stażysta", or "praktykant"'
        )
        examples = (
            '  Python dev:      ["junior python developer", "junior data engineer", "intern python", "data analyst intern", "stażysta python", "praktykant programista"]\n'
            '  Finance/Banking: ["junior financial analyst", "junior operations analyst", "junior risk analyst", "intern finance", "stażysta analityk", "praktykant finansowy"]\n'
            '  Marketing:       ["junior marketing specialist", "junior social media", "junior copywriter", "marketing intern", "stażysta marketing", "praktykant content"]\n'
            '  Data/BI:         ["junior data analyst", "junior bi analyst", "junior sql analyst", "data analyst intern", "stażysta analityk danych", "intern business intelligence"]'
        )
        fallback = ["junior developer", "intern IT", "junior python", "stażysta programista",
                    "junior analyst", "intern finance"]

    prompt = f"""Analyze this resume and user preferences, then return a JSON object with two keys:

"queries": array of 6 short job search strings (2-5 words each) for a job search API.
  Rules:
  - {specialty_line}
  - {seniority_rules}
  - Match the person's real domain: finance → analyst/specialist/operations/risk/compliance/treasury/AML/KYC; IT → developer/engineer/analyst
  - NEVER output: driver, cashier, warehouse, security, delivery, cook, waiter, bartender

"remotive_categories": array of 1-3 Remotive API category slugs that best match this profile.
  Choose ONLY from: {REMOTIVE_CATEGORIES}
  Finance/banking → "finance". IT → "software-dev" or "data". Marketing → "marketing".

Examples:
{examples}

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
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        result = json.loads(raw)
        queries = result.get("queries", [])
        categories = result.get("remotive_categories", ["software-dev"])
        if isinstance(queries, list) and queries:
            categories = [c for c in categories if c in REMOTIVE_CATEGORIES] or ["software-dev"]
            return queries, False, categories
    except Exception as e:
        logger.warning("Failed to generate queries via AI: %s", e)

    return fallback, True, ["software-dev"]


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


def _matches_skills(job: dict, skills: list[str]) -> bool:
    """Return True if job mentions at least one of the required skills."""
    text = (job.get("tech_stack", "") + " " + job.get("description", "")).lower()
    return any(s.lower() in text for s in skills)


def _detect_seniority(skills: list[str]) -> str:
    """Return 'senior' if user's skills list contains a seniority indicator, else 'junior'."""
    lower = {s.lower() for s in (skills or [])}
    if lower & _SENIOR_SENIORITY:
        return "senior"
    return "junior"


def _specialty_list(skills: list[str]) -> list[str]:
    """Return skills stripped of seniority markers (pure domain/tech keywords)."""
    all_seniority = _SENIOR_SENIORITY | _JUNIOR_QUERY_WORDS | {"entry-level", "stażysta", "praktykant"}
    return [s for s in (skills or []) if s.lower() not in all_seniority]


def _fetch_adzuna(queries: list[str], city: str, skills: list[str] = None, seniority: str = "junior") -> list[dict]:
    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        logger.info("No ADZUNA_APP_ID or ADZUNA_APP_KEY — source skipped.")
        return []

    jobs = []
    for query in queries:
        logger.info("[Adzuna] Searching: %s", query)
        params = {
            "app_id": ADZUNA_APP_ID,
            "app_key": ADZUNA_APP_KEY,
            "results_per_page": 50,
            "what": query,
            "where": city,
            "content-type": "application/json",
        }
        # Append first specialty skill so Adzuna ranks relevant results higher
        specialties = _specialty_list(skills)
        if specialties:
            params["what"] = query + " " + specialties[0]
        try:
            r = requests.get(ADZUNA_BASE_URL, params=params, timeout=15)
            r.raise_for_status()
            for offer in r.json().get("results", []):
                title = offer.get("title", "")
                link = offer.get("redirect_url", "")
                if not link:
                    continue
                description = _strip_html(offer.get("description") or "")
                # Always exclude blacklisted job categories
                if any(w in title.lower() for w in _EXCLUDED_TITLE_KEYWORDS):
                    continue
                # In junior mode: filter to entry-level jobs only
                # In senior mode: queries already target senior roles — trust the API
                if seniority == "junior":
                    query_targets_junior = any(w in query.lower() for w in _JUNIOR_QUERY_WORDS)
                    if not query_targets_junior and not _is_junior(title, description):
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
            logger.error("[Adzuna] Error on query '%s': %s", query, e)
        time.sleep(0.5)  # avoid hammering Adzuna between queries

    return jobs



def _city_to_nfj_slug(city: str) -> str:
    """Warsaw / Warszawa / Kraków → warszawa / krakow for NoFluffJobs criteria."""
    slug = city.lower().split(",")[0].strip()
    for pl, en in [("ą","a"),("ć","c"),("ę","e"),("ł","l"),("ń","n"),("ó","o"),("ś","s"),("ź","z"),("ż","z")]:
        slug = slug.replace(pl, en)
    return slug


def _fetch_nofluffjobs(city: str, skills: list[str] = None, seniority: str = "junior") -> list[dict]:
    """NoFluffJobs — Polish IT jobs, no API key needed."""
    city_slug = _city_to_nfj_slug(city)
    logger.info("[NoFluffJobs] Searching %s in %s (slug: %s)...", seniority, city, city_slug)

    if seniority == "senior":
        nfj_levels     = ["senior", "mid", "regular", "expert"]
        nfj_level_set  = {"senior", "mid", "regular", "expert"}
    else:
        nfj_levels     = ["junior", "intern", "trainee"]
        nfj_level_set  = {"junior", "intern", "trainee"}

    specialties = _specialty_list(skills)

    jobs = []
    page = 1
    total_pages = 1

    while page <= total_pages and page <= 5:  # cap at 250 jobs
        criteria: dict = {"city": [city_slug], "requirement": nfj_levels}
        if specialties:
            criteria["skill"] = [s.lower() for s in specialties]
        body = {"criteriaSearch": criteria, "page": page, "pageSize": 50}
        try:
            r = requests.post(NFJ_SEARCH_URL, headers=NFJ_HEADERS, json=body, timeout=15)
            r.raise_for_status()
            data = r.json()
            if page == 1:
                total_pages = data.get("totalPages", 1)
                logger.info("[NoFluffJobs] Total: %d jobs, %d pages.", data.get("totalCount", 0), total_pages)

            for p in data.get("postings", []):
                job_seniority = [s.lower() for s in (p.get("seniority") or [])]
                if not any(s in nfj_level_set for s in job_seniority):
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
            logger.error("[NoFluffJobs] Error on page %d: %s", page, e)
            break
        page += 1

    logger.info("[NoFluffJobs] Found %d matching jobs.", len(jobs))
    return jobs


def _fetch_remotive(categories: list[str], seniority: str = "junior") -> list[dict]:
    """Remotive — remote jobs worldwide, no API key needed.
    Queries each category from the provided list."""
    jobs = []
    seen_links: set[str] = set()

    for category in categories:
        logger.info("[Remotive] Searching category: %s...", category)
        try:
            r = requests.get(
                REMOTIVE_URL,
                params={"category": category, "limit": 100},
                timeout=15,
            )
            r.raise_for_status()
            offers = r.json().get("jobs", [])
        except Exception as e:
            logger.error("[Remotive] Error on category '%s': %s", category, e)
            continue

        for offer in offers:
            title = offer.get("title", "")
            link = offer.get("url", "")
            if not link or link in seen_links:
                continue
            description = _strip_html(offer.get("description") or "")
            # In junior mode filter to entry-level only; senior mode trusts query results
            if seniority == "junior" and not _is_junior(title, description):
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

    logger.info("[Remotive] Found %d matching jobs.", len(jobs))
    return jobs


def _fetch_jjit_api(api_url: str, city_slug: str, source: str, base_url: str,
                    skills: list[str] = None, seniority: str = "junior") -> list[dict]:
    """Shared fetcher for justjoin.it and rocketjobs.pl (internal Next.js API).
    City is not passed to the API (unreliable) — filtered client-side instead.
    """
    exp_levels = ["senior", "mid"] if seniority == "senior" else ["junior", "intern"]
    specialties = _specialty_list(skills)

    jobs = []
    seen_slugs: set[str] = set()

    for page in range(1, 11):  # cap at 500 jobs
        try:
            params = {
                "experienceLevel[]": exp_levels,
                "limit": 50,
                "page": page,
            }
            if specialties:
                params["skill[]"] = [s.lower() for s in specialties]
            r = requests.get(api_url, params=params, timeout=15)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            logger.error("[%s] Error on page %d: %s", source, page, e)
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

            # Accept job if it is remote OR located in the target city
            is_remote = item.get("workplaceType") == "remote"
            offer_cities = [_city_to_nfj_slug(item.get("city") or "")]
            offer_cities += [_city_to_nfj_slug(loc.get("city", "")) for loc in (item.get("locations") or [])]
            if not is_remote and city_slug not in offer_cities:
                continue

            seen_slugs.add(slug)
            emp = (item.get("employmentTypes") or [{}])[0]
            req_skills = [s["name"] for s in (item.get("requiredSkills") or [])]
            description = f"Required skills: {', '.join(req_skills)}." if req_skills else ""

            jobs.append({
                "title": title,
                "company": item.get("companyName", "Unknown"),
                "link": f"{base_url}{slug}",
                "tech_stack": ", ".join(req_skills[:6]),
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

    logger.info("[%s] Found %d matching jobs.", source, len(jobs))
    return jobs


def _fetch_justjoin(city: str, skills: list[str] = None, seniority: str = "junior") -> list[dict]:
    """JustJoin.it — internal Next.js API, no auth required."""
    logger.info("[JustJoin] Searching %s in %s...", seniority, city)
    return _fetch_jjit_api(JUSTJOIN_API, _city_to_nfj_slug(city), "JustJoin",
                           "https://justjoin.it/job-offer/", skills, seniority)


def _fetch_rocketjobs(city: str, skills: list[str] = None, seniority: str = "junior") -> list[dict]:
    """RocketJobs — same backend as JustJoin (same company)."""
    logger.info("[RocketJobs] Searching %s in %s...", seniority, city)
    return _fetch_jjit_api(ROCKETJOBS_API, _city_to_nfj_slug(city), "RocketJobs",
                           "https://rocketjobs.pl/job-offer/", skills, seniority)


# ── ATS platform fetchers ─────────────────────────────────────────────────────

def _fetch_greenhouse(city: str, skills: list[str] = None, seniority: str = "junior") -> list[dict]:
    """Greenhouse ATS — iterate over curated company boards."""
    from ats_companies import GREENHOUSE_BOARDS
    if not GREENHOUSE_BOARDS:
        return []
    logger.info("[Greenhouse] Searching %d boards (%s)...", len(GREENHOUSE_BOARDS), seniority)
    jobs: list[dict] = []
    city_lower = city.lower()
    for board_id, company_name in GREENHOUSE_BOARDS.items():
        try:
            url = f"https://boards-api.greenhouse.io/v1/boards/{board_id}/jobs"
            r = requests.get(url, params={"content": "true"}, timeout=15)
            r.raise_for_status()
            for posting in r.json().get("jobs", []):
                title = posting.get("title", "")
                if any(w in title.lower() for w in _EXCLUDED_TITLE_KEYWORDS):
                    continue
                if seniority == "junior" and not _is_junior(title, ""):
                    continue
                location = (posting.get("location") or {}).get("name", "")
                loc_lower = location.lower()
                if city_lower not in loc_lower and "remote" not in loc_lower:
                    continue
                description = _strip_html(posting.get("content", ""))
                jobs.append({
                    "title": title,
                    "company": company_name,
                    "link": posting.get("absolute_url", ""),
                    "tech_stack": _extract_tech(description),
                    "remote": "remote" in loc_lower,
                    "city": location or city,
                    "description": description,
                    "source": "Greenhouse",
                    "salary_min": None,
                    "salary_max": None,
                    "salary_currency": None,
                })
        except Exception as e:
            logger.error("[Greenhouse] Error for board '%s': %s", board_id, e)
        time.sleep(0.3)
    logger.info("[Greenhouse] Found %d matching jobs.", len(jobs))
    return jobs


def _fetch_lever(city: str, skills: list[str] = None, seniority: str = "junior") -> list[dict]:
    """Lever ATS — iterate over curated company boards."""
    from ats_companies import LEVER_COMPANIES
    if not LEVER_COMPANIES:
        return []
    logger.info("[Lever] Searching %d companies (%s)...", len(LEVER_COMPANIES), seniority)
    jobs: list[dict] = []
    city_lower = city.lower()
    for company_slug, company_name in LEVER_COMPANIES.items():
        try:
            url = f"https://api.lever.co/v0/postings/{company_slug}"
            r = requests.get(url, params={"mode": "json"}, timeout=15)
            r.raise_for_status()
            data = r.json()
            if not isinstance(data, list):
                continue
            for posting in data:
                title = posting.get("text", "")
                if any(w in title.lower() for w in _EXCLUDED_TITLE_KEYWORDS):
                    continue
                if seniority == "junior" and not _is_junior(title, ""):
                    continue
                location = (posting.get("categories") or {}).get("location", "")
                loc_lower = (location or "").lower()
                if city_lower not in loc_lower and "remote" not in loc_lower:
                    continue
                description = _strip_html(posting.get("descriptionPlain", "") or "")
                jobs.append({
                    "title": title,
                    "company": company_name,
                    "link": posting.get("hostedUrl", ""),
                    "tech_stack": _extract_tech(description),
                    "remote": "remote" in loc_lower,
                    "city": location or city,
                    "description": description,
                    "source": "Lever",
                    "salary_min": None,
                    "salary_max": None,
                    "salary_currency": None,
                })
        except Exception as e:
            logger.error("[Lever] Error for company '%s': %s", company_slug, e)
        time.sleep(0.3)
    logger.info("[Lever] Found %d matching jobs.", len(jobs))
    return jobs


def _fetch_workable(city: str, skills: list[str] = None, seniority: str = "junior") -> list[dict]:
    """Workable ATS — iterate over curated company subdomains."""
    from ats_companies import WORKABLE_COMPANIES
    if not WORKABLE_COMPANIES:
        return []
    logger.info("[Workable] Searching %d companies (%s)...", len(WORKABLE_COMPANIES), seniority)
    jobs: list[dict] = []
    city_lower = city.lower()
    for subdomain, company_name in WORKABLE_COMPANIES.items():
        try:
            url = f"https://apply.workable.com/api/v3/accounts/{subdomain}/jobs"
            r = requests.post(url, json={
                "query": "", "location": [], "department": [],
                "worktype": [], "remote": [],
            }, timeout=15)
            r.raise_for_status()
            for posting in r.json().get("results", []):
                title = posting.get("title", "")
                if any(w in title.lower() for w in _EXCLUDED_TITLE_KEYWORDS):
                    continue
                if seniority == "junior" and not _is_junior(title, ""):
                    continue
                location = posting.get("location", "")
                loc_lower = (location or "").lower()
                if city_lower not in loc_lower and "remote" not in loc_lower:
                    continue
                shortcode = posting.get("shortcode", "")
                link = f"https://apply.workable.com/{subdomain}/j/{shortcode}/"
                description = _strip_html(posting.get("description", "") or "")
                jobs.append({
                    "title": title,
                    "company": company_name,
                    "link": link,
                    "tech_stack": _extract_tech(description),
                    "remote": "remote" in loc_lower,
                    "city": location or city,
                    "description": description,
                    "source": "Workable",
                    "salary_min": None,
                    "salary_max": None,
                    "salary_currency": None,
                })
        except Exception as e:
            logger.error("[Workable] Error for company '%s': %s", subdomain, e)
        time.sleep(0.3)
    logger.info("[Workable] Found %d matching jobs.", len(jobs))
    return jobs


# ── Corporate career page fetchers ────────────────────────────────────────────

def _fetch_workday_company(cfg: dict, city: str, seniority: str) -> list[dict]:
    """Fetch jobs from a single Workday-powered career site."""
    tenant = cfg["tenant"]
    instance = cfg["instance"]
    site = cfg["site"]
    company_name = cfg["company"]
    base = f"https://{tenant}.{instance}.myworkdayjobs.com"
    api = f"{base}/wday/cxs/{tenant}/{site}/jobs"

    jobs: list[dict] = []
    city_lower = city.lower()
    offset = 0
    limit = 20

    while True:
        r = requests.post(api, json={
            "appliedFacets": {},
            "limit": limit,
            "offset": offset,
            "searchText": "",
        }, timeout=15)
        r.raise_for_status()
        data = r.json()
        postings = data.get("jobPostings", [])
        if not postings:
            break

        for p in postings:
            title = p.get("title", "")
            if any(w in title.lower() for w in _EXCLUDED_TITLE_KEYWORDS):
                continue
            if seniority == "junior" and not _is_junior(title, ""):
                continue
            loc = p.get("locationsText", "")
            loc_lower = loc.lower()
            if city_lower not in loc_lower and "remote" not in loc_lower:
                continue
            path = p.get("externalPath", "")
            link = f"{base}/en-US/{site}/job{path}" if path else ""
            jobs.append({
                "title": title,
                "company": company_name,
                "link": link,
                "tech_stack": "",
                "remote": "remote" in loc_lower,
                "city": loc or city,
                "description": "",
                "source": f"{company_name} Careers",
                "salary_min": None,
                "salary_max": None,
                "salary_currency": None,
            })

        total = data.get("total", 0)
        offset += limit
        if offset >= total:
            break
        time.sleep(0.3)

    return jobs


def _fetch_corporate_careers(city: str, skills: list[str] = None, seniority: str = "junior") -> list[dict]:
    """Scrape career pages of top employers via Workday / custom APIs."""
    from careers_config import WORKDAY_COMPANIES

    jobs: list[dict] = []
    if WORKDAY_COMPANIES:
        logger.info("[CorporateCareers] Searching %d Workday sites (%s)...",
                     len(WORKDAY_COMPANIES), seniority)
    for cfg in WORKDAY_COMPANIES:
        try:
            jobs.extend(_fetch_workday_company(cfg, city, seniority))
        except Exception as e:
            logger.error("[CorporateCareers] Error for %s: %s", cfg["company"], e)
        time.sleep(0.5)

    if jobs:
        logger.info("[CorporateCareers] Found %d matching jobs.", len(jobs))
    return jobs


def search_jobs(city: str = "Warsaw", chat_id: int = 0) -> tuple[list[dict], bool]:
    from database import get_user_skills
    try:
        resume_text = load_resume(chat_id)
    except FileNotFoundError:
        resume_text = ""
        logger.warning("Resume not found — using fallback queries.")

    skills   = get_user_skills(chat_id)
    seniority = _detect_seniority(skills)
    if skills:
        logger.info("Skills filter active (%s mode): %s", seniority, skills)

    queries, used_fallback, remotive_categories = build_queries(resume_text, city, skills)
    logger.info("Adzuna queries: %d%s", len(queries), " (fallback)" if used_fallback else "")
    logger.info("Remotive categories: %s | seniority: %s", remotive_categories, seniority)

    raw = []
    raw.extend(_fetch_adzuna(queries, city, skills, seniority))
    raw.extend(_fetch_nofluffjobs(city, skills, seniority))
    # raw.extend(_fetch_justjoin(city, skills, seniority))
    # raw.extend(_fetch_rocketjobs(city, skills, seniority))
    raw.extend(_fetch_remotive(remotive_categories, seniority))
    # ATS platforms — direct company board APIs
    raw.extend(_fetch_greenhouse(city, skills, seniority))
    raw.extend(_fetch_lever(city, skills, seniority))
    raw.extend(_fetch_workable(city, skills, seniority))
    # Corporate career pages (Workday, etc.)
    raw.extend(_fetch_corporate_careers(city, skills, seniority))

    # Deduplicate: 3 layers
    # 1) link — exact URL match
    # 2) (title, company) — same job from different aggregators with different URLs
    # 3) content hash MD5(company|normalized_title|city) — catches cross-source
    #    duplicates where title has minor differences (e.g. "- Warsaw" suffix)
    seen_links: set[str] = set()
    seen_pairs: set[tuple] = set()
    seen_hashes: set[str] = set()
    jobs = []
    for job in raw:
        link = job["link"]
        pair = (job["title"].lower().strip(), job["company"].lower().strip())
        h = _dedup_hash(job["company"], job["title"], job.get("city", ""))
        if not link:
            continue
        if link in seen_links or pair in seen_pairs or h in seen_hashes:
            continue
        seen_links.add(link)
        seen_pairs.add(pair)
        seen_hashes.add(h)
        job["content_hash"] = h
        jobs.append(job)

    # Post-filter by specialty keywords (catches Remotive and sources without native skill filter)
    specialties = _specialty_list(skills)
    if specialties:
        before = len(jobs)
        jobs = [j for j in jobs if _matches_skills(j, specialties)]
        logger.info("Specialty filter: kept %d of %d jobs (required: %s)", len(jobs), before, specialties)

    logger.info("Total unique jobs: %d (from %d raw)", len(jobs), len(raw))
    return jobs, used_fallback
