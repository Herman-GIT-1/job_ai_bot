import os
from contextlib import contextmanager

import psycopg2
from psycopg2.pool import ThreadedConnectionPool

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
                "ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS resume_text TEXT",
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

def save_job(job: dict, chat_id: int) -> None:
    try:
        with _get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO jobs"
                    " (chat_id, title, company, link, tech_stack, remote, city, description)"
                    " VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
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
                    ),
                )
            conn.commit()
    except Exception as e:
        print(f"[DB] save_job error: {e}")


def get_jobs(chat_id: int) -> list:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, title, company, link, tech_stack, description"
                " FROM jobs WHERE chat_id = %s AND score IS NULL",
                (chat_id,),
            )
            return cur.fetchall()


def get_jobs_to_apply(chat_id: int, min_score: int = 7) -> list:
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, title, company, link, score, description, cover_letter"
                " FROM jobs WHERE chat_id = %s AND applied = 0 AND score >= %s",
                (chat_id, min_score),
            )
            return cur.fetchall()


def mark_applied(job_id: int, chat_id: int, status: int = 1) -> None:
    """status: 1 = applied, 2 = skipped"""
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE jobs SET applied = %s WHERE id = %s AND chat_id = %s",
                (status, job_id, chat_id),
            )
        conn.commit()


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
                "total":     q("SELECT COUNT(*) FROM jobs WHERE chat_id = %s", chat_id),
                "scored":    q("SELECT COUNT(*) FROM jobs WHERE chat_id = %s AND score IS NOT NULL", chat_id),
                "avg_score": q("SELECT AVG(score) FROM jobs WHERE chat_id = %s AND score IS NOT NULL", chat_id),
                "applied":   q("SELECT COUNT(*) FROM jobs WHERE chat_id = %s AND applied = 1", chat_id),
                "skipped":   q("SELECT COUNT(*) FROM jobs WHERE chat_id = %s AND applied = 2", chat_id),
            }
