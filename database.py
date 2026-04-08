import logging
import os
from contextlib import contextmanager

import psycopg2
from psycopg2.pool import ThreadedConnectionPool

logger = logging.getLogger(__name__)

# Sentinel chat_id used by CLI (main.py) in single-user mode.
CLI_CHAT_ID = 0

DATABASE_URL = os.environ.get("DATABASE_URL", "")

# ── Connection pool ────────────────────────────────────────────────────────────

_pool: ThreadedConnectionPool | None = None


def _init_pool() -> None:
    global _pool
    _pool = ThreadedConnectionPool(minconn=2, maxconn=10, dsn=DATABASE_URL)


@contextmanager
def _get_conn():
    conn = _pool.getconn()
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    finally:
        _pool.putconn(conn)


# ── Schema ─────────────────────────────────────────────────────────────────────

def _apply_schema() -> None:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
CREATE TABLE IF NOT EXISTS jobs (
    id          BIGSERIAL PRIMARY KEY,
    chat_id     BIGINT NOT NULL,
    title       TEXT,
    company     TEXT,
    link        TEXT,
    tech_stack  TEXT,
    remote      INTEGER DEFAULT 0,
    city        TEXT,
    score       INTEGER,
    cover_letter TEXT,
    applied     INTEGER DEFAULT 0,
    description TEXT DEFAULT ''
)""")
            cur.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_jobs_link_user"
                " ON jobs (link, chat_id)"
            )
            cur.execute("""
CREATE TABLE IF NOT EXISTS user_settings (
    chat_id     BIGINT PRIMARY KEY,
    language    TEXT NOT NULL DEFAULT 'en',
    resume_text TEXT
)""")
            # Idempotent column migrations (PostgreSQL 9.6+ supports IF NOT EXISTS)
            for ddl in [
                "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS chat_id BIGINT",
                "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS description TEXT DEFAULT ''",
                "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS source TEXT",
                "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS salary_min INTEGER",
                "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS salary_max INTEGER",
                "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS salary_currency TEXT",
                "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS applied_at TIMESTAMPTZ",
                "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS job_status TEXT DEFAULT 'pending'",
                "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW()",
                "ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS resume_text TEXT",
                "ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS last_scrape_at TIMESTAMPTZ",
            ]:
                cur.execute(ddl)
        conn.commit()


_init_pool()
_apply_schema()


# ── User settings ──────────────────────────────────────────────────────────────

def get_user_lang(chat_id: int) -> str:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT language FROM user_settings WHERE chat_id = %s", (chat_id,)
            )
            row = cur.fetchone()
    return row[0] if row else "en"


def set_user_lang(chat_id: int, lang: str) -> None:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO user_settings (chat_id, language) VALUES (%s, %s)"
                " ON CONFLICT (chat_id) DO UPDATE SET language = EXCLUDED.language",
                (chat_id, lang),
            )
        conn.commit()


def get_resume(chat_id: int) -> str | None:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT resume_text FROM user_settings WHERE chat_id = %s", (chat_id,)
            )
            row = cur.fetchone()
    return row[0] if row else None


def get_last_scrape(chat_id: int):
    """Return last_scrape_at as aware datetime, or None if never scraped."""
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT last_scrape_at FROM user_settings WHERE chat_id = %s", (chat_id,)
            )
            row = cur.fetchone()
    return row[0] if row else None


def set_last_scrape(chat_id: int) -> None:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO user_settings (chat_id, last_scrape_at) VALUES (%s, NOW())"
                " ON CONFLICT (chat_id) DO UPDATE SET last_scrape_at = NOW()",
                (chat_id,),
            )
        conn.commit()


def set_resume(chat_id: int, text: str) -> None:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO user_settings (chat_id, resume_text) VALUES (%s, %s)"
                " ON CONFLICT (chat_id) DO UPDATE SET resume_text = EXCLUDED.resume_text",
                (chat_id, text),
            )
        conn.commit()


# ── Job operations (all scoped to chat_id) ────────────────────────────────────

def save_job(job: dict, chat_id: int) -> bool:
    """Insert job; returns True if a new row was created, False on duplicate or error."""
    try:
        with _get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO jobs"
                    " (chat_id, title, company, link, tech_stack, remote, city, description,"
                    "  source, salary_min, salary_max, salary_currency)"
                    " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                    " ON CONFLICT (link, chat_id) DO NOTHING",
                    (
                        chat_id,
                        job["title"],
                        job["company"],
                        job["link"],
                        job.get("tech_stack", ""),
                        int(job.get("remote", False)),
                        job.get("city", ""),
                        job.get("description", ""),
                        job.get("source"),
                        job.get("salary_min"),
                        job.get("salary_max"),
                        job.get("salary_currency"),
                    ),
                )
                inserted = cur.rowcount > 0
            conn.commit()
        return inserted
    except Exception as e:
        logger.error("save_job error: %s", e)
        return False


def get_jobs(chat_id: int) -> list:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, title, company, link, tech_stack, description"
                " FROM jobs WHERE chat_id = %s AND score IS NULL",
                (chat_id,),
            )
            return cur.fetchall()


def get_jobs_to_apply(
    chat_id: int, min_score: int = 7, limit: int = 5, offset: int = 0
) -> list:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, title, company, link, score, description, cover_letter,"
                "       salary_min, salary_max, salary_currency"
                " FROM jobs WHERE chat_id = %s AND applied = 0 AND score >= %s"
                " ORDER BY score DESC"
                " LIMIT %s OFFSET %s",
                (chat_id, min_score, limit, offset),
            )
            return cur.fetchall()


def count_jobs_to_apply(chat_id: int, min_score: int = 7) -> int:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM jobs"
                " WHERE chat_id = %s AND applied = 0 AND score >= %s",
                (chat_id, min_score),
            )
            return cur.fetchone()[0]


def mark_applied(job_id: int, chat_id: int, status: int = 1) -> None:
    """status: 1 = applied, 2 = skipped"""
    with _get_conn() as conn:
        with conn.cursor() as cur:
            applied_at_sql = ", applied_at = NOW()" if status == 1 else ""
            cur.execute(
                f"UPDATE jobs SET applied = %s, job_status = %s{applied_at_sql}"
                " WHERE id = %s AND chat_id = %s",
                (status, "applied" if status == 1 else "skipped", job_id, chat_id),
            )
        conn.commit()


def mark_interested(job_id: int, chat_id: int) -> None:
    """Mark job as saved/interested (applied=3)."""
    try:
        with _get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE jobs SET applied = 3, job_status = 'interested'"
                    " WHERE id = %s AND chat_id = %s",
                    (job_id, chat_id),
                )
            conn.commit()
    except Exception as e:
        logger.error("mark_interested error: %s", e)


def get_interested_jobs(chat_id: int) -> list:
    """Return saved/interested jobs (applied=3) ordered by score."""
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, title, company, link, score, cover_letter"
                " FROM jobs WHERE chat_id = %s AND applied = 3"
                " ORDER BY score DESC",
                (chat_id,),
            )
            return cur.fetchall()


def update_job_status(job_id: int, chat_id: int, job_status: str) -> None:
    """Update tracker status: 'interviewing', 'rejected', 'offer'."""
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE jobs SET job_status = %s WHERE id = %s AND chat_id = %s",
                (job_status, job_id, chat_id),
            )
        conn.commit()


def move_to_status(job_id: int, chat_id: int, job_status: str) -> None:
    """Move job to a tracker status, updating applied flag accordingly.

    interviewing/rejected/offer → applied=1 (counted as applied in stats)
    interested → applied=3 (back to saved list)
    """
    try:
        applied_val = 3 if job_status == "interested" else 1
        with _get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE jobs SET job_status = %s, applied = %s,"
                    " applied_at = COALESCE(applied_at, NOW())"
                    " WHERE id = %s AND chat_id = %s",
                    (job_status, applied_val, job_id, chat_id),
                )
            conn.commit()
    except Exception as e:
        logger.error("move_to_status error: %s", e)


def get_jobs_by_status(chat_id: int, job_status: str) -> list:
    """Return jobs with specific job_status for tracker tabs (ordered by applied_at)."""
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, title, company, link, score, job_status"
                " FROM jobs WHERE chat_id = %s AND job_status = %s"
                " ORDER BY applied_at DESC NULLS LAST, score DESC",
                (chat_id, job_status),
            )
            return cur.fetchall()


def get_applied_jobs(chat_id: int) -> list:
    """Return applied jobs ordered by applied_at for /tracker."""
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, title, company, link, score, job_status, applied_at"
                " FROM jobs WHERE chat_id = %s AND applied = 1"
                " ORDER BY applied_at DESC NULLS LAST",
                (chat_id,),
            )
            return cur.fetchall()


def update_job(job_id: int, chat_id: int, score: int, letter: str) -> None:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE jobs SET score = %s, cover_letter = %s"
                " WHERE id = %s AND chat_id = %s",
                (score, letter, job_id, chat_id),
            )
        conn.commit()


def get_cover_letter(job_id: int, chat_id: int):
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT title, company, cover_letter"
                " FROM jobs WHERE id = %s AND chat_id = %s",
                (job_id, chat_id),
            )
            row = cur.fetchone()
    return row if row else None


def get_job_link(job_id: int, chat_id: int) -> str | None:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT link FROM jobs WHERE id = %s AND chat_id = %s",
                (job_id, chat_id),
            )
            row = cur.fetchone()
    return row[0] if row else None


def reset_scores(chat_id: int) -> None:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE jobs SET score = NULL, cover_letter = NULL"
                " WHERE chat_id = %s AND applied = 0",
                (chat_id,),
            )
        conn.commit()


def delete_expired_jobs(days: int = 21) -> int:
    """Delete pending jobs (applied=0) older than `days` days. Returns number of deleted rows."""
    try:
        with _get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM jobs WHERE applied = 0"
                    " AND created_at < NOW() - INTERVAL '%s days'",
                    (days,),
                )
                deleted = cur.rowcount
            conn.commit()
        return deleted
    except Exception as e:
        logger.error("delete_expired_jobs error: %s", e)
        return 0


def count_jobs(chat_id: int) -> int:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM jobs WHERE chat_id = %s", (chat_id,)
            )
            return cur.fetchone()[0]


def get_stats(chat_id: int) -> dict:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            def q(sql: str, *args) -> any:
                cur.execute(sql, args)
                return cur.fetchone()[0]

            return {
                "total":      q("SELECT COUNT(*) FROM jobs WHERE chat_id = %s", chat_id),
                "scored":     q("SELECT COUNT(*) FROM jobs WHERE chat_id = %s AND score IS NOT NULL", chat_id),
                "avg_score":  q("SELECT AVG(score) FROM jobs WHERE chat_id = %s AND score IS NOT NULL", chat_id),
                "applied":    q("SELECT COUNT(*) FROM jobs WHERE chat_id = %s AND applied = 1", chat_id),
                "skipped":    q("SELECT COUNT(*) FROM jobs WHERE chat_id = %s AND applied = 2", chat_id),
                "interested": q("SELECT COUNT(*) FROM jobs WHERE chat_id = %s AND applied = 3", chat_id),
            }
