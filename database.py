import sqlite3

conn = sqlite3.connect("jobs.db")
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

conn.commit()


def save_job(job):
    try:
        cursor.execute(
            "INSERT OR IGNORE INTO jobs (title, company, link, tech_stack, remote, city) VALUES (?, ?, ?, ?, ?, ?)",
            (job["title"], job["company"], job["link"],
             job.get("tech_stack", ""), int(job.get("remote", False)), job.get("city", ""))
        )
        conn.commit()
    except Exception as e:
        print(f"[DB] save_job error: {e}")


def get_jobs():
    cursor.execute(
        "SELECT id, title, company, link, tech_stack FROM jobs WHERE score IS NULL"
    )
    return cursor.fetchall()


def get_jobs_to_apply():
    cursor.execute(
        "SELECT id, title, company, link, cover_letter FROM jobs WHERE applied=0 AND score>=7"
    )
    return cursor.fetchall()


def mark_applied(job_id):
    cursor.execute("UPDATE jobs SET applied=1 WHERE id=?", (job_id,))
    conn.commit()


def update_job(job_id, score, letter):
    cursor.execute(
        "UPDATE jobs SET score=?, cover_letter=? WHERE id=?",
        (score, letter, job_id)
    )
    conn.commit()


def get_stats():
    cursor.execute("SELECT COUNT(*) FROM jobs")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM jobs WHERE score IS NOT NULL")
    scored = cursor.fetchone()[0]
    cursor.execute("SELECT AVG(score) FROM jobs WHERE score IS NOT NULL")
    avg = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM jobs WHERE applied=1")
    applied = cursor.fetchone()[0]
    return {"total": total, "scored": scored, "avg_score": avg, "applied": applied}