"""FastAPI server for the Telegram Mini App.

Routes:
    GET  /app          — serve the Mini App HTML page
    GET  /api/jobs     — paginated job list (auth via Telegram initData HMAC)
    POST /api/skip     — mark job as skipped   (applied=2)
    POST /api/save     — mark job as interested (applied=3)
    POST /api/apply    — mark job as applied    (applied=1)
"""

import hashlib
import hmac
import json
import logging
import os
from urllib.parse import parse_qsl

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse

from config import DEFAULT_MIN_SCORE
from database import get_jobs_to_apply, mark_applied, mark_interested

logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = FastAPI(docs_url=None, redoc_url=None)


# ── Auth ───────────────────────────────────────────────────────────────────────

def _verify_init_data(init_data: str) -> dict:
    """Verify Telegram WebApp initData HMAC-SHA256 and return user dict."""
    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    hash_value = pairs.pop("hash", None)
    if not hash_value:
        raise ValueError("No hash in initData")

    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(pairs.items())
    )

    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    computed = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed, hash_value):
        raise ValueError("Invalid initData hash")

    user_json = pairs.get("user", "{}")
    return json.loads(user_json)


def _auth(request: Request) -> int:
    """Extract and validate chat_id from Authorization: tma <initData> header."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("tma "):
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    try:
        user = _verify_init_data(auth[4:])
        return int(user["id"])
    except (ValueError, KeyError) as e:
        raise HTTPException(status_code=401, detail=str(e))


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/app")
async def webapp_index():
    return FileResponse(os.path.join(BASE_DIR, "static", "index.html"))


@app.get("/api/jobs")
async def api_jobs(request: Request):
    chat_id = _auth(request)
    rows = get_jobs_to_apply(chat_id, min_score=DEFAULT_MIN_SCORE, limit=100, offset=0)
    jobs = []
    for row in rows:
        job_id, title, company, link, score, description, cover_letter, \
            salary_min, salary_max, salary_currency = row
        jobs.append({
            "id": job_id,
            "title": title or "",
            "company": company or "",
            "link": link or "",
            "score": score or 0,
            "description": (description or "")[:500],
            "cover_letter": cover_letter or "",
            "salary_min": salary_min,
            "salary_max": salary_max,
            "salary_currency": salary_currency,
        })
    return {"jobs": jobs}


@app.post("/api/skip")
async def api_skip(request: Request):
    chat_id = _auth(request)
    body = await request.json()
    mark_applied(int(body["job_id"]), chat_id, status=2)
    return {"ok": True}


@app.post("/api/save")
async def api_save(request: Request):
    chat_id = _auth(request)
    body = await request.json()
    mark_interested(int(body["job_id"]), chat_id)
    return {"ok": True}


@app.post("/api/apply")
async def api_apply(request: Request):
    chat_id = _auth(request)
    body = await request.json()
    mark_applied(int(body["job_id"]), chat_id, status=1)
    return {"ok": True}
