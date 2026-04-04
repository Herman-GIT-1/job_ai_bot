import webbrowser
from database import get_jobs_to_apply, mark_applied, CLI_CHAT_ID

def open_jobs(min_score: int = 7):

    jobs = get_jobs_to_apply(CLI_CHAT_ID, min_score)

    for job in jobs:

        job_id, title, company, link, score, _, letter = job

        print("\nCompany:", company)
        print("Role:", title)
        print("Score:", score)
        print("\nCover letter:\n", letter)

        webbrowser.open(link)

        input("Press ENTER after applying")

        mark_applied(job_id, CLI_CHAT_ID)
