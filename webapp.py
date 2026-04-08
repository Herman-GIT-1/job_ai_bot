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

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, RedirectResponse

from config import DEFAULT_MIN_SCORE
from database import (
    get_jobs_to_apply, get_interested_jobs, mark_applied, mark_interested,
    get_jobs_by_status, move_to_status,
)

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


def _auth(init_data: str = Query(default="", alias="init_data")) -> int:
    """Validate Telegram initData from query param and return chat_id."""
    if not init_data:
        raise HTTPException(status_code=401, detail="initData is empty — open via Telegram")
    try:
        user = _verify_init_data(init_data)
        return int(user["id"])
    except (ValueError, KeyError) as e:
        logger.warning("Auth failed: %s | token_len=%d | init_data_len=%d",
                       e, len(BOT_TOKEN), len(init_data))
        raise HTTPException(status_code=401, detail=str(e))


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return RedirectResponse(url="/app")


@app.get("/app")
async def webapp_index():
    return FileResponse(os.path.join(BASE_DIR, "static", "index.html"))


@app.get("/api/jobs")
async def api_jobs(chat_id: int = Depends(_auth)):
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
async def api_skip(request: Request, chat_id: int = Depends(_auth)):
    body = await request.json()
    mark_applied(int(body["job_id"]), chat_id, status=2)
    return {"ok": True}


@app.post("/api/save")
async def api_save(request: Request, chat_id: int = Depends(_auth)):
    body = await request.json()
    mark_interested(int(body["job_id"]), chat_id)
    return {"ok": True}


@app.post("/api/apply")
async def api_apply(request: Request, chat_id: int = Depends(_auth)):
    body = await request.json()
    mark_applied(int(body["job_id"]), chat_id, status=1)
    return {"ok": True}


_TRACKER_STATUSES = {"interviewing", "rejected", "offer", "applied"}


@app.get("/api/tracker")
async def api_tracker(status: str = Query(...), chat_id: int = Depends(_auth)):
    if status not in _TRACKER_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")
    rows = get_jobs_by_status(chat_id, status)
    jobs = []
    for row in rows:
        job_id, title, company, link, score, job_status = row
        jobs.append({
            "id": job_id,
            "title": title or "",
            "company": company or "",
            "link": link or "",
            "score": score or 0,
            "job_status": job_status or "",
        })
    return {"jobs": jobs}


@app.post("/api/status")
async def api_set_status(request: Request, chat_id: int = Depends(_auth)):
    body = await request.json()
    status = body.get("status", "")
    allowed = {"interviewing", "rejected", "offer", "interested"}
    if status not in allowed:
        raise HTTPException(status_code=400, detail="Invalid status")
    move_to_status(int(body["job_id"]), chat_id, status)
    return {"ok": True}


@app.get("/api/saved")
async def api_saved(chat_id: int = Depends(_auth)):
    rows = get_interested_jobs(chat_id)
    jobs = []
    for row in rows:
        job_id, title, company, link, score, cover_letter = row
        jobs.append({
            "id": job_id,
            "title": title or "",
            "company": company or "",
            "link": link or "",
            "score": score or 0,
            "cover_letter": cover_letter or "",
        })
    return {"jobs": jobs}
