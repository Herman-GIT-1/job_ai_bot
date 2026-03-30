import json
import os
import requests
from dotenv import load_dotenv
from groq import Groq
from resume_parser import load_resume

load_dotenv()

SERPAPI_KEY = os.environ.get("SERPAPI_KEY")
_groq = Groq(api_key=os.environ.get("GROQ_API_KEY"))


def build_queries(resume_text: str, city: str) -> tuple[list[str], list[str], bool]:
    """Ask Groq to produce search queries and tech keywords from the resume.
    Returns (queries, tech_keywords, used_fallback)."""
    prompt = f"""You are a job search assistant. Analyze this resume and return a JSON object with two keys:
- "queries": list of 6-8 Google Jobs search strings for junior/intern positions in {city}.
  Each query should combine a role and a key skill (e.g. "junior python developer {city.lower()}").
  Always include at least one query with "stażysta" or "praktykant" for Polish-language results.
- "tech_keywords": list of 10-15 technology names mentioned or implied in the resume
  (e.g. "Python", "SQL", "Power BI"). Used to scan job descriptions.

Resume:
{resume_text}

Return ONLY valid JSON. No explanation."""

    try:
        response = _groq.chat.completions.create(
            model="llama-3.1-8b-instant",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}]
        )
        data = json.loads(response.choices[0].message.content.strip())
        queries = data.get("queries", [])
        tech_keywords = data.get("tech_keywords", [])
        if queries and tech_keywords:
            return queries, tech_keywords, False
    except Exception as e:
        print(f"[Scraper] Не удалось сгенерировать запросы через AI: {e}")

    # Fallback — generic queries so scraping still works without a resume
    return [
        f"junior developer {city.lower()}",
        f"intern IT {city.lower()}",
        f"stażysta programista {city.lower()}",
    ], ["Python", "SQL", "Java", "JavaScript"], True


def is_relevant(title: str) -> bool:
    title = title.lower()
    return any(word in title for word in [
        "intern", "junior", "trainee", "stażyst", "praktyk", "staż"
    ])


def search_jobs(city: str = "Warsaw, Poland") -> list[dict]:
    if not SERPAPI_KEY:
        print("[Scraper] Brak SERPAPI_KEY w pliku .env")
        return []

    try:
        resume_text = load_resume()
    except FileNotFoundError:
        resume_text = ""
        print("[Scraper] resume.txt не найдено — используются базовые запросы.")

    queries, tech_keywords, used_fallback = build_queries(resume_text, city)
    print(f"[Scraper] Запросов: {len(queries)}, технологий в фильтре: {len(tech_keywords)}")

    jobs = []
    seen_links = set()

    for query in queries:
        print(f"  Ищу: {query}")
        params = {
            "engine": "google_jobs",
            "q": query,
            "location": city,
            "hl": "en",
            "api_key": SERPAPI_KEY,
        }
        try:
            response = requests.get("https://serpapi.com/search", params=params, timeout=15)
            results = response.json().get("jobs_results", [])

            for job in results:
                title = job.get("title", "")
                company = job.get("company_name", "Unknown")

                apply_options = job.get("apply_options", [])
                link = apply_options[0].get("link", "") if apply_options else ""

                if not link:
                    continue
                if not is_relevant(title):
                    continue
                if link in seen_links:
                    continue
                seen_links.add(link)

                description = job.get("description", "")
                found_tech = [t for t in tech_keywords if t.lower() in description.lower()]
                tech_stack = ", ".join(found_tech[:6])

                remote = "remote" in str(job.get("detected_extensions", {})).lower()

                jobs.append({
                    "title": title,
                    "company": company,
                    "link": link,
                    "tech_stack": tech_stack,
                    "remote": remote,
                    "city": city,
                    "description": description[:1500],
                })

        except Exception as e:
            print(f"  [Ошибка] '{query}': {e}")

    print(f"\n[Scraper] Найдено уникальных вакансий: {len(jobs)}")
    return jobs, used_fallback
