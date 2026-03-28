import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

with open(os.path.join(os.path.dirname(__file__), "resume.txt")) as f:
    resume = f.read()

def evaluate(job):
    tech_stack = job.get("tech_stack", "")
    tech_info = f"Tech stack: {tech_stack}" if tech_stack else ""

    prompt = f"""You are a senior recruiter evaluating how well a candidate fits a job opening.

## Candidate Resume:
{resume}

## Job Opening:
Title: {job["title"]}
Company: {job.get("company", "Unknown")}
{tech_info}

## Scoring Criteria (0–10):
1. Technical skills match — Python, SQL, Power BI, ML, data analysis, backend
2. Seniority fit — is intern/junior/trainee level appropriate?
3. Project relevance — do candidate's projects match this role?
4. Education alignment — is IT/data degree relevant?
5. Overall potential — self-learning, initiative, certifications

## Scoring Guide:
- 9–10: Excellent fit
- 7–8: Good fit
- 5–6: Partial fit
- 3–4: Weak fit
- 0–2: Poor fit

Return ONLY a single integer from 0 to 10. No explanation. No punctuation. Just the number."""

    try:
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            max_tokens=5,
            messages=[{"role": "user", "content": prompt}]
        )
        return int(response.choices[0].message.content.strip())
    except Exception as e:
        print(f"[Score error] {e}")
        return 5