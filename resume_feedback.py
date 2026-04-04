import os
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

_client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


def analyze_resume(resume_text: str) -> str:
    """Return AI critique of the resume (150-200 words).
    Uses Claude Sonnet with prompt caching on the resume block."""
    cached_prefix = f"""You are a career coach reviewing a student's resume.
Analyze the resume below and provide direct, actionable feedback.

Resume:
{resume_text}

Your feedback must cover exactly these three points:
1. Top 3 skills or keywords missing for junior/intern roles in this field
2. The weakest section of the resume and why (e.g. vague descriptions, no projects, missing metrics)
3. One concrete rewrite suggestion for the single most important bullet point — show before and after

Be direct and specific. No generic advice. Max 200 words total."""

    try:
        response = _client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=400,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": cached_prefix,
                     "cache_control": {"type": "ephemeral"}},
                    {"type": "text", "text": "Provide the feedback now."},
                ],
            }],
        )
        return response.content[0].text
    except Exception as e:
        print(f"[ResumeFeedback] Error: {e}")
        return "Resume feedback generation failed."
