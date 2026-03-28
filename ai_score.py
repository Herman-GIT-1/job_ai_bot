import os
from groq import Groq
from dotenv import load_dotenv
from resume_parser import load_resume

load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def evaluate(job):
    resume = load_resume()
    tech_stack = job.get("tech_stack", "")
    tech_info = f"Tech stack: {tech_stack}" if tech_stack else ""

    prompt = f"""You are a senior recruiter. Score how well this candidate fits the job opening.

## Candidate Resume:
{resume}

## Job Opening:
Title: {job["title"]}
Company: {job.get("company", "Unknown")}
{tech_info}

## Instructions:
Analyze the resume and the job, then score the match from 0 to 10 based on:
1. Technical skills overlap — compare the candidate's actual skills with what the job requires
2. Seniority fit — does the role level (intern/junior/mid) match the candidate's experience?
3. Domain relevance — do the candidate's projects and background relate to this role?
4. Education fit — is the candidate's field of study relevant?
5. Growth potential — certifications, side projects, self-learning

## Scoring Guide:
- 9–10: Excellent fit
- 7–8: Good fit
- 5–6: Partial fit
- 3–4: Weak fit
- 0–2: Poor fit

Return ONLY a single integer from 0 to 10. No explanation. No punctuation. Just the number."""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            max_tokens=5,
            messages=[{"role": "user", "content": prompt}]
        )
        return int(response.choices[0].message.content.strip())
    except Exception as e:
        print(f"[Score error] {e}")
        return 5