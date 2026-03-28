import webbrowser
from database import get_jobs_to_apply, mark_applied

def open_jobs():

    jobs = get_jobs_to_apply()

    for job in jobs:

        job_id, title, company, link, letter = job

        print("\nCompany:", company)
        print("Role:", title)
        print("\nCover letter:\n", letter)

        webbrowser.open(link)

        input("Press ENTER after applying")

        mark_applied(job_id)