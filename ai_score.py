import json
import logging
import os
import time

from anthropic import Anthropic
from dotenv import load_dotenv

from config import MODEL_SCORING
from resume_parser import load_resume

load_dotenv()

logger = logging.getLogger(__name__)
client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


def evaluate(job, resume=None) -> tuple[int, str]:
    """Return (score 0–10, reason str). On error returns (5, "")."""
    if resume is None:
        resume = load_resume()

    tech_stack = job.get("tech_stack", "")
    tech_info = f"Tech stack: {tech_stack}" if tech_stack else ""
    description = job.get("description", "")
    desc_info = f"Description:\n{description[:600]}" if description else ""

    # Cached block: static instructions + resume (same across all jobs in a run).
    # Anthropic caches this after the first call; subsequent reads cost 10% of normal.
    # Minimum cacheable size: 1024 tokens (Sonnet/Opus), 2048 tokens (Haiku).
    cached_prefix = f"""You are a recruiter scoring candidate fit for a job opening.

## Candidate Resume:
{resume}

Score 0–10 how well this candidate fits the job, based ONLY on the resume above.

Criteria (in order of importance):
1. Domain match — does the candidate's field/industry background align with the job? (highest weight)
2. Can they perform the core duties? (skills, tools, domain knowledge they already have)
3. Technical skills overlap with job requirements
4. Education relevance

Rules:
- A candidate with strong domain experience applying to a junior role in THEIR OWN field should score 7-9. Do NOT penalise for being "overqualified" — the bot helps people find roles in their area.
- Score low (1-4) ONLY when the domain is completely wrong (e.g. banker applying for a cooking job) or critical required skills are clearly absent.
- Do not assume skills not mentioned. Do not apply generic industry standards.

Return ONLY valid JSON on one line, no other text:
{{"score": N, "reason": "up to 12 words explaining the main match or gap"}}"""

    job_block = (
        f"## Job:\nTitle: {job['title']}\nCompany: {job.get('company', '')}"
        + (f"\n{tech_info}" if tech_info else "")
        + (f"\n{desc_info}" if desc_info else "")
    )

    last_err = None
    for attempt in range(3):
        try:
            response = client.messages.create(
                model=MODEL_SCORING,
                max_tokens=80,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": cached_prefix,
                         "cache_control": {"type": "ephemeral"}},
                        {"type": "text", "text": job_block},
                    ],
                }],
            )
            raw = response.content[0].text.strip()
            data = json.loads(raw)
            return int(data["score"]), str(data.get("reason", ""))
        except Exception as e:
            last_err = e
            if attempt < 2:
                logger.warning("Score attempt %d failed: %s — retrying in 2s", attempt + 1, e)
                time.sleep(2)

    logger.error("Score error after 3 attempts: %s", last_err)
    return 5, ""   # neutral default — never crash the pipeline
