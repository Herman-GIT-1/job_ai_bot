import logging
import os
import time

from anthropic import Anthropic
from dotenv import load_dotenv

from config import MODEL_LETTER
from resume_parser import load_resume

load_dotenv()

logger = logging.getLogger(__name__)
client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


def generate_letter(job, resume=None):
    if resume is None:
        resume = load_resume()

    tech_stack = job.get("tech_stack", "")
    tech_info = f"Required tech stack: {tech_stack}" if tech_stack else ""
    description = job.get("description", "")
    desc_info = f"Job description:\n{description[:600]}" if description else ""

    # Cached block: static instructions + resume.
    cached_prefix = f"""Write a short cover letter (100-120 words) for this candidate.

Candidate Resume:
{resume}

Guidelines:
- Pick 2-3 skills most relevant to the specific role
- Mention 1-2 projects from the resume briefly if they relate
- Professional, concise, enthusiastic tone
- Do NOT list certificates explicitly
- End with a clear call to action
- Write only the cover letter text. No subject line, no placeholders."""

    job_block = (
        f"Job: {job['title']} at {job['company']}"
        + (f"\n{tech_info}" if tech_info else "")
        + (f"\n{desc_info}" if desc_info else "")
    )

    last_err = None
    for attempt in range(3):
        try:
            response = client.messages.create(
                model=MODEL_LETTER,
                max_tokens=300,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": cached_prefix,
                         "cache_control": {"type": "ephemeral"}},
                        {"type": "text", "text": job_block},
                    ],
                }],
            )
            return response.content[0].text
        except Exception as e:
            last_err = e
            if attempt < 2:
                logger.warning("Letter attempt %d failed: %s — retrying in 2s", attempt + 1, e)
                time.sleep(2)

    logger.error("Cover letter error after 3 attempts: %s", last_err)
    return "Cover letter generation failed."
