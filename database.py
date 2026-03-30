import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "jobs.db")

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY,
    title TEXT,
    company TEXT,
    link TEXT UNIQUE,
    tech_stack TEXT,
    remote INTEGER DEFAULT 0,
    city TEXT,
    score INTEGER,
    cover_letter TEXT,
    applied INTEGER DEFAULT 0
)
""")

# Migration: add UNIQUE index for existing databases created without the constraint
cursor.execute(
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_jobs_link ON jobs (link)"
)

# Migration: add description column for existing databases
try:
    cursor.execute("ALTER TABLE jobs ADD COLUMN description TEXT DEFAULT ''")
except sqlite3.OperationalError:
    pass  # column already exists

cursor.execute("""
CREATE TABLE IF NOT EXISTS user_settings (
    chat_id INTEGER PRIMARY KEY,
    language TEXT NOT NULL DEFAULT 'en'
)
""")

conn.commit()


def get_user_lang(chat_id: int) -> str:
    row = conn.execute("SELECT language FROM user_settings WHERE chat_id=?", (chat_id,)).fetchone()
    return row[0] if row else "en"


def set_user_lang(chat_id: int, lang: str) -> None:
    conn.execute(
        "INSERT INTO user_settings (chat_id, language) VALUES (?, ?)"
        " ON CONFLICT(chat_id) DO UPDATE SET language=excluded.language",
        (chat_id, lang),
    )
    conn.commit()


def save_job(job):
    try:
        cursor.execute(
            "INSERT OR IGNORE INTO jobs (title, company, link, tech_stack, remote, city, description) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (job["title"], job["company"], job["link"],
             job.get("tech_stack", ""), int(job.get("remote", False)),
             job.get("city", ""), job.get("description", ""))
        )
        conn.commit()
    except Exception as e:
        print(f"[DB] save_job error: {e}")


def get_jobs():
    cursor.execute(
        "SELECT id, title, company, link, tech_stack, description FROM jobs WHERE score IS NULL"
    )
    return cursor.fetchall()


def get_jobs_to_apply(min_score: int = 7):
    cursor.execute(
        "SELECT id, title, company, link, score, description, cover_letter FROM jobs WHERE applied=0 AND score>=?",
        (min_score,)
    )
    return cursor.fetchall()


def mark_applied(job_id, status=1):
    """status: 1 = applied, 2 = skipped"""
    cursor.execute("UPDATE jobs SET applied=? WHERE id=?", (status, job_id))
    conn.commit()


def update_job(job_id, score, letter):
    cursor.execute(
        "UPDATE jobs SET score=?, cover_letter=? WHERE id=?",
        (score, letter, job_id)
    )
    conn.commit()


def get_cover_letter(job_id: int):
    cursor.execute("SELECT title, company, cover_letter FROM jobs WHERE id=?", (job_id,))
    row = cursor.fetchone()
    return row if row else None


def get_job_link(job_id: int):
    cursor.execute("SELECT link FROM jobs WHERE id=?", (job_id,))
    row = cursor.fetchone()
    return row[0] if row else None


def reset_scores():
    cursor.execute("UPDATE jobs SET score=NULL, cover_letter=NULL WHERE applied=0")
    conn.commit()


def count_jobs() -> int:
    return conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]


def get_stats():
    cursor.execute("SELECT COUNT(*) FROM jobs")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM jobs WHERE score IS NOT NULL")
    scored = cursor.fetchone()[0]
    cursor.execute("SELECT AVG(score) FROM jobs WHERE score IS NOT NULL")
    avg = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM jobs WHERE applied=1")
    applied = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM jobs WHERE applied=2")
    skipped = cursor.fetchone()[0]
    return {"total": total, "scored": scored, "avg_score": avg, "applied": applied, "skipped": skipped}