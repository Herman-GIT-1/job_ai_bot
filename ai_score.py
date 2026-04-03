import os
from anthropic import Anthropic
from dotenv import load_dotenv
from resume_parser import load_resume

load_dotenv()

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


def evaluate(job, resume=None):
    if resume is None:
        resume = load_resume()

    tech_stack = job.get("tech_stack", "")
    tech_info = f"Tech stack: {tech_stack}" if tech_stack else ""
    description = job.get("description", "")
    desc_info = f"Description:\n{description[:600]}" if description else ""

    # Cached block: static instructions + resume (same across all jobs in a run).
    # Anthropic caches this after the first call; subsequent reads cost 10% of normal.
    # Minimum cacheable size: 1024 tokens (Sonnet/Opus), 2048 tokens (Haiku).
    cached_prefix = f"""You are a senior recruiter. Score how well this candidate fits a job opening.

## Candidate Resume:
{resume}

Score the match 0–10 based ONLY on what is written in this resume above.
Do not assume skills not mentioned. Do not apply generic industry standards.
Evaluate this specific candidate against this specific job:
1. Technical skills overlap
2. Seniority fit (intern/junior/mid)
3. Domain relevance to candidate's background
4. Education fit
5. Growth potential given candidate's actual trajectory

Return ONLY a single integer 0–10. No explanation."""

    job_block = (
        f"## Job:\nTitle: {job['title']}\nCompany: {job.get('company', '')}"
        + (f"\n{tech_info}" if tech_info else "")
        + (f"\n{desc_info}" if desc_info else "")
    )

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=5,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": cached_prefix,
                     "cache_control": {"type": "ephemeral"}},
                    {"type": "text", "text": job_block},
                ],
            }],
        )
        return int(response.content[0].text.strip())
    except Exception as e:
        print(f"[Score error] {e}")
        return 5
