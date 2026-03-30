import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "jobs.db")

# Sentinel chat_id used by CLI (main.py) in single-user mode.
# When multi-user is fully deployed, CLI tools will be deprecated in favour of the bot.
CLI_CHAT_ID = 0

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
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

# Unique per (link, chat_id) — same job can be saved for different users
cursor.execute(
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_jobs_link_user ON jobs (link, chat_id)"
)

cursor.execute("""
CREATE TABLE IF NOT EXISTS user_settings (
    chat_id INTEGER PRIMARY KEY,
    language TEXT NOT NULL DEFAULT 'en',
    resume_text TEXT
)
""")

# ── Migrations for existing single-user databases ──────────────────────────

# Add chat_id column to jobs if missing (old schema had no chat_id)
try:
    cursor.execute("ALTER TABLE jobs ADD COLUMN chat_id INTEGER")
except sqlite3.OperationalError:
    pass  # already exists

# Add description column if missing
try:
    cursor.execute("ALTER TABLE jobs ADD COLUMN description TEXT DEFAULT ''")
except sqlite3.OperationalError:
    pass

# Add resume_text column to user_settings if missing
try:
    cursor.execute("ALTER TABLE user_settings ADD COLUMN resume_text TEXT")
except sqlite3.OperationalError:
    pass

# Drop old single-column unique index (replaced by idx_jobs_link_user above)
cursor.execute("DROP INDEX IF EXISTS idx_jobs_link")

conn.commit()


# ── User settings ──────────────────────────────────────────────────────────

def get_user_lang(chat_id: int) -> str:
    row = conn.execute(
        "SELECT language FROM user_settings WHERE chat_id=?", (chat_id,)
    ).fetchone()
    return row[0] if row else "en"


def set_user_lang(chat_id: int, lang: str) -> None:
    conn.execute(
        "INSERT INTO user_settings (chat_id, language) VALUES (?, ?)"
        " ON CONFLICT(chat_id) DO UPDATE SET language=excluded.language",
        (chat_id, lang),
    )
    conn.commit()


def get_resume(chat_id: int) -> str | None:
    row = conn.execute(
        "SELECT resume_text FROM user_settings WHERE chat_id=?", (chat_id,)
    ).fetchone()
    return row[0] if row else None


def set_resume(chat_id: int, text: str) -> None:
    conn.execute(
        "INSERT INTO user_settings (chat_id, resume_text) VALUES (?, ?)"
        " ON CONFLICT(chat_id) DO UPDATE SET resume_text=excluded.resume_text",
        (chat_id, text),
    )
    conn.commit()


# ── Job operations (all scoped to chat_id) ────────────────────────────────

def save_job(job: dict, chat_id: int) -> None:
    try:
        cursor.execute(
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
    cursor.execute(
        "SELECT id, title, company, link, tech_stack, description "
        "FROM jobs WHERE chat_id=? AND score IS NULL",
        (chat_id,),
    )
    return cursor.fetchall()


def get_jobs_to_apply(chat_id: int, min_score: int = 7) -> list:
    cursor.execute(
        "SELECT id, title, company, link, score, description, cover_letter "
        "FROM jobs WHERE chat_id=? AND applied=0 AND score>=?",
        (chat_id, min_score),
    )
    return cursor.fetchall()


def mark_applied(job_id: int, chat_id: int, status: int = 1) -> None:
    """status: 1 = applied, 2 = skipped"""
    cursor.execute(
        "UPDATE jobs SET applied=? WHERE id=? AND chat_id=?",
        (status, job_id, chat_id),
    )
    conn.commit()


def update_job(job_id: int, chat_id: int, score: int, letter: str) -> None:
    cursor.execute(
        "UPDATE jobs SET score=?, cover_letter=? WHERE id=? AND chat_id=?",
        (score, letter, job_id, chat_id),
    )
    conn.commit()


def get_cover_letter(job_id: int, chat_id: int):
    cursor.execute(
        "SELECT title, company, cover_letter FROM jobs WHERE id=? AND chat_id=?",
        (job_id, chat_id),
    )
    row = cursor.fetchone()
    return row if row else None


def get_job_link(job_id: int, chat_id: int) -> str | None:
    cursor.execute(
        "SELECT link FROM jobs WHERE id=? AND chat_id=?",
        (job_id, chat_id),
    )
    row = cursor.fetchone()
    return row[0] if row else None


def reset_scores(chat_id: int) -> None:
    cursor.execute(
        "UPDATE jobs SET score=NULL, cover_letter=NULL WHERE chat_id=? AND applied=0",
        (chat_id,),
    )
    conn.commit()


def count_jobs(chat_id: int) -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM jobs WHERE chat_id=?", (chat_id,)
    ).fetchone()[0]


def get_stats(chat_id: int) -> dict:
    def q(sql, *args):
        return cursor.execute(sql, args).fetchone()[0]

    return {
        "total":   q("SELECT COUNT(*) FROM jobs WHERE chat_id=?", chat_id),
        "scored":  q("SELECT COUNT(*) FROM jobs WHERE chat_id=? AND score IS NOT NULL", chat_id),
        "avg_score": q("SELECT AVG(score) FROM jobs WHERE chat_id=? AND score IS NOT NULL", chat_id),
        "applied": q("SELECT COUNT(*) FROM jobs WHERE chat_id=? AND applied=1", chat_id),
        "skipped": q("SELECT COUNT(*) FROM jobs WHERE chat_id=? AND applied=2", chat_id),
    }
