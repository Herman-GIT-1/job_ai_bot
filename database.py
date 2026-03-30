import os
import sqlite3
from contextlib import contextmanager
from queue import Queue

DB_PATH = os.path.join(os.path.dirname(__file__), "jobs.db")

# Sentinel chat_id used by CLI (main.py) in single-user mode.
CLI_CHAT_ID = 0

# ── Connection pool ────────────────────────────────────────────────────────────

_POOL_SIZE = 5
_pool: Queue = Queue(maxsize=_POOL_SIZE)


def _init_pool() -> None:
    for _ in range(_POOL_SIZE):
        c = sqlite3.connect(DB_PATH, check_same_thread=False)
        c.execute("PRAGMA journal_mode=WAL")
        _pool.put(c)


@contextmanager
def _get_conn():
    conn = _pool.get()
    try:
        yield conn
    finally:
        _pool.put(conn)


# ── Schema ─────────────────────────────────────────────────────────────────────

def _apply_schema() -> None:
    with _get_conn() as conn:
        conn.execute("""
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY,
    chat_id INTEGER NOT NULL,
    title TEXT,
    company TEXT,
    link TEXT,
    tech_stack TEXT,
    remote INTEGER DEFAULT 0,
    city TEXT,
    score INTEGER,
    cover_letter TEXT,
    applied INTEGER DEFAULT 0,
    description TEXT DEFAULT ''
)
""")
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_jobs_link_user ON jobs (link, chat_id)"
        )
        conn.execute("""
CREATE TABLE IF NOT EXISTS user_settings (
    chat_id INTEGER PRIMARY KEY,
    language TEXT NOT NULL DEFAULT 'en',
    resume_text TEXT
)
""")

        # ── Migrations for existing databases ──────────────────────────────
        for ddl in [
            "ALTER TABLE jobs ADD COLUMN chat_id INTEGER",
            "ALTER TABLE jobs ADD COLUMN description TEXT DEFAULT ''",
            "ALTER TABLE user_settings ADD COLUMN resume_text TEXT",
        ]:
            try:
                conn.execute(ddl)
            except sqlite3.OperationalError:
                pass  # column already exists

        conn.execute("DROP INDEX IF EXISTS idx_jobs_link")
        conn.commit()


_init_pool()
_apply_schema()


# ── User settings ──────────────────────────────────────────────────────────────

def get_user_lang(chat_id: int) -> str:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT language FROM user_settings WHERE chat_id=?", (chat_id,)
        ).fetchone()
    return row[0] if row else "en"


def set_user_lang(chat_id: int, lang: str) -> None:
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO user_settings (chat_id, language) VALUES (?, ?)"
            " ON CONFLICT(chat_id) DO UPDATE SET language=excluded.language",
            (chat_id, lang),
        )
        conn.commit()


def get_resume(chat_id: int) -> str | None:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT resume_text FROM user_settings WHERE chat_id=?", (chat_id,)
        ).fetchone()
    return row[0] if row else None


def set_resume(chat_id: int, text: str) -> None:
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO user_settings (chat_id, resume_text) VALUES (?, ?)"
            " ON CONFLICT(chat_id) DO UPDATE SET resume_text=excluded.resume_text",
            (chat_id, text),
        )
        conn.commit()


# ── Job operations (all scoped to chat_id) ─────────────────────────────────────

def save_job(job: dict, chat_id: int) -> None:
    try:
        with _get_conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO jobs "
                "(chat_id, title, company, link, tech_stack, remote, city, description) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
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
        return conn.execute(
            "SELECT id, title, company, link, tech_stack, description "
            "FROM jobs WHERE chat_id=? AND score IS NULL",
            (chat_id,),
        ).fetchall()


def get_jobs_to_apply(chat_id: int, min_score: int = 7) -> list:
    with _get_conn() as conn:
        return conn.execute(
            "SELECT id, title, company, link, score, description, cover_letter "
            "FROM jobs WHERE chat_id=? AND applied=0 AND score>=?",
            (chat_id, min_score),
        ).fetchall()


def mark_applied(job_id: int, chat_id: int, status: int = 1) -> None:
    """status: 1 = applied, 2 = skipped"""
    with _get_conn() as conn:
        conn.execute(
            "UPDATE jobs SET applied=? WHERE id=? AND chat_id=?",
            (status, job_id, chat_id),
        )
        conn.commit()


def update_job(job_id: int, chat_id: int, score: int, letter: str) -> None:
    with _get_conn() as conn:
        conn.execute(
            "UPDATE jobs SET score=?, cover_letter=? WHERE id=? AND chat_id=?",
            (score, letter, job_id, chat_id),
        )
        conn.commit()


def get_cover_letter(job_id: int, chat_id: int):
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT title, company, cover_letter FROM jobs WHERE id=? AND chat_id=?",
            (job_id, chat_id),
        ).fetchone()
    return row if row else None


def get_job_link(job_id: int, chat_id: int) -> str | None:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT link FROM jobs WHERE id=? AND chat_id=?",
            (job_id, chat_id),
        ).fetchone()
    return row[0] if row else None


def reset_scores(chat_id: int) -> None:
    with _get_conn() as conn:
        conn.execute(
            "UPDATE jobs SET score=NULL, cover_letter=NULL WHERE chat_id=? AND applied=0",
            (chat_id,),
        )
        conn.commit()


def count_jobs(chat_id: int) -> int:
    with _get_conn() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM jobs WHERE chat_id=?", (chat_id,)
        ).fetchone()[0]


def get_stats(chat_id: int) -> dict:
    with _get_conn() as conn:
        def q(sql, *args):
            return conn.execute(sql, args).fetchone()[0]
        return {
            "total":     q("SELECT COUNT(*) FROM jobs WHERE chat_id=?", chat_id),
            "scored":    q("SELECT COUNT(*) FROM jobs WHERE chat_id=? AND score IS NOT NULL", chat_id),
            "avg_score": q("SELECT AVG(score) FROM jobs WHERE chat_id=? AND score IS NOT NULL", chat_id),
            "applied":   q("SELECT COUNT(*) FROM jobs WHERE chat_id=? AND applied=1", chat_id),
            "skipped":   q("SELECT COUNT(*) FROM jobs WHERE chat_id=? AND applied=2", chat_id),
        }
