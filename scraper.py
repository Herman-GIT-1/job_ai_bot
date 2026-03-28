import requests
import os
from dotenv import load_dotenv

load_dotenv()

# SerpApi — бесплатно 100 запросов/месяц
# Регистрация: https://serpapi.com/ → API Key
SERPAPI_KEY = os.environ.get("SERPAPI_KEY")

SEARCHES = [
    "junior python developer warszawa",
    "data analyst intern warszawa",
    "junior data analyst warszawa",
    "machine learning intern warszawa",
    "junior sql developer warszawa",
    "python intern warszawa",
    "data science intern warsaw poland",
    "IT stażysta warszawa",
]

def is_relevant(title):
    title = title.lower()
    return any(word in title for word in [
        "intern", "junior", "trainee", "stażyst", "praktyk", "staż"
    ])

def search_jobs():
    if not SERPAPI_KEY:
        print("BŁĄD: Brak SERPAPI_KEY w pliku .env")
        print("Zarejestruj się na https://serpapi.com/ (100 zapytań/miesiąc za darmo)")
        return []

    jobs = []
    seen_links = set()

    for query in SEARCHES:
        print(f"Szukam: {query}")

        params = {
            "engine": "google_jobs",
            "q": query,
            "location": "Warsaw, Poland",
            "hl": "en",
            "api_key": SERPAPI_KEY,
        }

        try:
            response = requests.get(
                "https://serpapi.com/search",
                params=params,
                timeout=15
            )
            data = response.json()

            results = data.get("jobs_results", [])

            for job in results:
                title = job.get("title", "")
                company = job.get("company_name", "Unknown")
                link = ""

                # Берём первую ссылку для подачи заявки
                apply_options = job.get("apply_options", [])
                if apply_options:
                    link = apply_options[0].get("link", "")

                # Фильтр по junior/intern
                if not is_relevant(title):
                    continue

                # Дедупликация
                key = f"{title}_{company}"
                if key in seen_links:
                    continue
                seen_links.add(key)

                # Собираем стек если есть в описании
                description = job.get("description", "")
                tech_keywords = ["Python", "SQL", "Power BI", "Excel", "R", "Tableau",
                                 "Machine Learning", "pandas", "scikit-learn", "Flask",
                                 "JavaScript", "Java", "Alteryx", "Spark"]
                found_tech = [t for t in tech_keywords if t.lower() in description.lower()]
                tech_stack = ", ".join(found_tech[:6])

                # Проверяем remote
                detected_extensions = job.get("detected_extensions", {})
                remote = "remote" in str(detected_extensions).lower()

                jobs.append({
                    "title": title,
                    "company": company,
                    "link": link,
                    "tech_stack": tech_stack,
                    "remote": remote,
                    "city": "Warsaw"
                })

        except Exception as e:
            print(f"Błąd dla '{query}': {e}")

    print(f"\nZnaleziono {len(jobs)} unikalnych ofert.")
    return jobs