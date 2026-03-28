import os
from groq import Groq
from dotenv import load_dotenv
from resume_parser import load_resume

load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def generate_letter(job):
    resume = load_resume()
    tech_stack = job.get("tech_stack", "")
    tech_info = f"Required tech stack: {tech_stack}" if tech_stack else ""

    prompt = f"""Write a short cover letter (100-120 words) for this candidate applying to this job.

Candidate Resume:
{resume}

Job: {job['title']} at {job['company']}
{tech_info}

Guidelines:
- Read the resume carefully and pick the 2-3 skills most relevant to THIS specific role
- Mention 1-2 specific projects from the resume briefly if they relate to the role
- Professional, concise, enthusiastic tone
- Focus on concrete value the candidate brings based on their actual background
- Do NOT list certificates explicitly — write as if skills are naturally demonstrated
- End with a clear call to action

Write only the cover letter text. No subject line, no placeholders."""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"[Cover letter error] {e}")
        return "Cover letter generation failed."