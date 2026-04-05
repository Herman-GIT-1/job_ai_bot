"""Centralised configuration constants.

All hard-coded values that were previously scattered across modules live here.
Import with:  from config import CITIES, JOBS_PAGE_SIZE, ...
"""

# ── Telegram bot behaviour ─────────────────────────────────────────────────────

CITIES = ["Warszawa", "Kraków", "Wrocław", "Gdańsk", "Poznań", "Remote"]

SCRAPE_COOLDOWN_MINUTES = 60   # cooldown between /scrape calls per user
JOBS_PAGE_SIZE = 5             # job cards sent per page in /jobs

# ── AI models ──────────────────────────────────────────────────────────────────

MODEL_SCORING       = "claude-haiku-4-5-20251001"   # fast, cheap, returns 1 int
MODEL_LETTER        = "claude-sonnet-4-6"           # quality matters for letters
MODEL_QUERY_BUILDER = "claude-sonnet-4-6"           # runs once per scrape
MODEL_FEEDBACK      = "claude-sonnet-4-6"           # resume feedback

# ── Scoring thresholds ─────────────────────────────────────────────────────────

DEFAULT_MIN_SCORE   = 7    # jobs shown in /jobs by default
HIGH_SCORE_ALERT    = 8    # threshold for "X high-score jobs" alert after scoring
LETTER_MIN_SCORE    = 7    # minimum score to generate a cover letter

# ── Resume ─────────────────────────────────────────────────────────────────────

RESUME_MIN_LENGTH = 100    # characters; shorter than this is rejected as invalid

# ── Database ───────────────────────────────────────────────────────────────────

JOB_EXPIRY_DAYS = 21       # pending jobs older than this are deleted by daily cleanup

# ── Telegram Mini App ──────────────────────────────────────────────────────────

import os as _os
WEBAPP_URL = _os.environ.get("WEBAPP_URL", "")  # e.g. https://your-service.railway.app
