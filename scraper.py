import os
import requests
from resume_parser import load_resume

SENIORITY_LEVELS = {"junior", "intern"}


def is_relevant(title: str) -> bool:
    title = title.lower()
    return any(word in title for word in [
        "intern", "junior", "trainee", "stażyst", "praktyk", "staż"
    ])


def search_jobs(city: str = "Warsaw") -> tuple[list[dict], bool]:
    city_key = city.lower().split(",")[0].strip()

    try:
        response = requests.get("https://justjoin.it/api/offers", timeout=30)
        response.raise_for_status()
        offers = response.json()
    except Exception as e:
        print(f"[Scraper] Не удалось получить вакансии с JustJoin.it: {e}")
        return [], False

    jobs = []
    seen_links = set()

    for offer in offers:
        offer_city = (offer.get("city") or "").lower()
        if city_key not in offer_city:
            continue

        experience = (offer.get("experienceLevel") or "").lower()
        title = offer.get("title") or ""
        if experience not in SENIORITY_LEVELS and not is_relevant(title):
            continue

        offer_id = offer.get("id") or ""
        link = f"https://justjoin.it/offers/{offer_id}" if offer_id else ""
        if not link or link in seen_links:
            continue
        seen_links.add(link)

        skills = offer.get("skills") or []
        tech_stack = ", ".join(
            s.get("name", "") for s in skills[:6] if s.get("name")
        )

        remote = (offer.get("workplaceType") or "") == "remote"
        description = (offer.get("body") or "")[:1500]

        jobs.append({
            "title": title,
            "company": offer.get("companyName") or "Unknown",
            "link": link,
            "tech_stack": tech_stack,
            "remote": remote,
            "city": offer.get("city") or city,
            "description": description,
        })

    print(f"[Scraper] JustJoin.it: найдено {len(jobs)} junior/intern вакансий в '{city}'")
    return jobs, False
