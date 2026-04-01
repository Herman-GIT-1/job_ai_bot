"""
PostgreSQL database tests for job_ai_bot.
Tests all public functions in database.py.
"""

import os
import sys
import time
import traceback
from dotenv import load_dotenv

load_dotenv()

# ── Setup ──────────────────────────────────────────────────────────────────────
results = []

def ok(name, detail=""):
    results.append(("PASS", name, detail))
    print(f"  [PASS] {name}" + (f" - {detail}" if detail else ""))

def fail(name, detail=""):
    results.append(("FAIL", name, detail))
    print(f"  [FAIL] {name}" + (f" - {detail}" if detail else ""))

def section(title):
    print(f"\n{'='*55}")
    print(f"  {title}")
    print(f"{'='*55}")

# ── Import database module ─────────────────────────────────────────────────────
section("1. Import & Connection Pool")
try:
    import database as db
    ok("import database")
except Exception as e:
    fail("import database", str(e))
    print("\nFATAL: cannot import database.py — aborting tests.")
    sys.exit(1)

# ── Test connection pool ───────────────────────────────────────────────────────
try:
    with db._get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            val = cur.fetchone()[0]
    if val == 1:
        ok("connection pool _get_conn()", "SELECT 1 returned 1")
    else:
        fail("connection pool _get_conn()", f"unexpected value: {val}")
except Exception as e:
    fail("connection pool _get_conn()", str(e))

# ── Test schema tables exist ───────────────────────────────────────────────────
section("2. Schema Verification")
try:
    with db._get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            tables = [r[0] for r in cur.fetchall()]

    for expected in ("jobs", "user_settings"):
        if expected in tables:
            ok(f"table '{expected}' exists")
        else:
            fail(f"table '{expected}' exists", f"found: {tables}")
except Exception as e:
    fail("schema tables check", str(e))

# ── Test columns ───────────────────────────────────────────────────────────────
try:
    with db._get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'jobs'
                ORDER BY ordinal_position
            """)
            jobs_cols = {r[0]: r[1] for r in cur.fetchall()}

            cur.execute("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'user_settings'
                ORDER BY ordinal_position
            """)
            us_cols = {r[0]: r[1] for r in cur.fetchall()}

    required_jobs = ["id", "chat_id", "title", "company", "link",
                     "tech_stack", "remote", "city", "score",
                     "cover_letter", "applied", "description"]
    for col in required_jobs:
        if col in jobs_cols:
            ok(f"jobs.{col} ({jobs_cols[col]})")
        else:
            fail(f"jobs.{col} MISSING")

    required_us = ["chat_id", "language", "resume_text"]
    for col in required_us:
        if col in us_cols:
            ok(f"user_settings.{col} ({us_cols[col]})")
        else:
            fail(f"user_settings.{col} MISSING")
except Exception as e:
    fail("columns check", str(e))

# ── Test unique index ──────────────────────────────────────────────────────────
try:
    with db._get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT indexname FROM pg_indexes
                WHERE tablename = 'jobs' AND indexname = 'idx_jobs_link_user'
            """)
            row = cur.fetchone()
    if row:
        ok("unique index idx_jobs_link_user exists")
    else:
        fail("unique index idx_jobs_link_user missing")
except Exception as e:
    fail("index check", str(e))

# ── Use isolated test chat_id ──────────────────────────────────────────────────
TEST_CHAT_ID = 999999999  # sentinel — will be cleaned up at the end

# ── Cleanup helper ─────────────────────────────────────────────────────────────
def cleanup():
    try:
        with db._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM jobs WHERE chat_id = %s", (TEST_CHAT_ID,))
                cur.execute("DELETE FROM user_settings WHERE chat_id = %s", (TEST_CHAT_ID,))
            conn.commit()
    except Exception:
        pass

cleanup()  # start clean

# ── user_settings functions ────────────────────────────────────────────────────
section("3. user_settings: get/set language")

try:
    lang = db.get_user_lang(TEST_CHAT_ID)
    if lang == "en":
        ok("get_user_lang returns 'en' for unknown user")
    else:
        fail("get_user_lang default", f"got '{lang}', expected 'en'")
except Exception as e:
    fail("get_user_lang unknown user", str(e))

try:
    db.set_user_lang(TEST_CHAT_ID, "ru")
    lang = db.get_user_lang(TEST_CHAT_ID)
    if lang == "ru":
        ok("set_user_lang + get_user_lang round-trip", "en->ru")
    else:
        fail("set_user_lang", f"got '{lang}'")
except Exception as e:
    fail("set_user_lang", str(e))

try:
    db.set_user_lang(TEST_CHAT_ID, "pl")
    lang = db.get_user_lang(TEST_CHAT_ID)
    if lang == "pl":
        ok("set_user_lang upsert works", "ru->pl")
    else:
        fail("set_user_lang upsert", f"got '{lang}'")
except Exception as e:
    fail("set_user_lang upsert", str(e))

# ── resume ─────────────────────────────────────────────────────────────────────
section("4. user_settings: get/set resume")

try:
    res = db.get_resume(TEST_CHAT_ID)
    if res is None:
        ok("get_resume returns None for new user (no resume)")
    else:
        fail("get_resume initial", f"expected None, got '{res[:30]}'")
except Exception as e:
    fail("get_resume unknown user", str(e))

SAMPLE_RESUME = "Python developer, 5 years experience."
try:
    db.set_resume(TEST_CHAT_ID, SAMPLE_RESUME)
    res = db.get_resume(TEST_CHAT_ID)
    if res == SAMPLE_RESUME:
        ok("set_resume + get_resume round-trip")
    else:
        fail("set_resume", f"got '{res}'")
except Exception as e:
    fail("set_resume", str(e))

try:
    new_resume = "Senior Python/Django, AWS, 8 years."
    db.set_resume(TEST_CHAT_ID, new_resume)
    res = db.get_resume(TEST_CHAT_ID)
    if res == new_resume:
        ok("set_resume upsert overwrites old resume")
    else:
        fail("set_resume upsert", f"got '{res}'")
except Exception as e:
    fail("set_resume upsert", str(e))

# ── save_job / get_jobs ────────────────────────────────────────────────────────
section("5. jobs: save_job + get_jobs")

SAMPLE_JOB = {
    "title": "Backend Developer",
    "company": "TestCorp",
    "link": "https://test.example.com/job/1",
    "tech_stack": "Python, Django",
    "remote": True,
    "city": "Warsaw",
    "description": "We need a backend dev.",
}

try:
    before = db.count_jobs(TEST_CHAT_ID)
    db.save_job(SAMPLE_JOB, TEST_CHAT_ID)
    after = db.count_jobs(TEST_CHAT_ID)
    if after == before + 1:
        ok("save_job inserts new job", f"count: {before}->{after}")
    else:
        fail("save_job insert", f"count: {before}→{after}")
except Exception as e:
    fail("save_job", str(e))

try:
    db.save_job(SAMPLE_JOB, TEST_CHAT_ID)
    count_dup = db.count_jobs(TEST_CHAT_ID)
    if count_dup == 1:
        ok("save_job ON CONFLICT does nothing (dedup by link+chat_id)")
    else:
        fail("save_job dedup", f"count={count_dup}, expected 1")
except Exception as e:
    fail("save_job dedup", str(e))

try:
    jobs = db.get_jobs(TEST_CHAT_ID)
    if len(jobs) == 1:
        j = jobs[0]
        if j[1] == "Backend Developer" and j[2] == "TestCorp":
            ok("get_jobs returns unscored job with correct data")
        else:
            fail("get_jobs data", f"title='{j[1]}', company='{j[2]}'")
    else:
        fail("get_jobs count", f"expected 1, got {len(jobs)}")
except Exception as e:
    fail("get_jobs", str(e))

# Save a second job for multi-record tests
JOB2 = dict(SAMPLE_JOB, title="Data Scientist", link="https://test.example.com/job/2",
            company="DataInc", tech_stack="Python, ML")
db.save_job(JOB2, TEST_CHAT_ID)

# ── update_job (score + cover letter) ─────────────────────────────────────────
section("6. jobs: update_job (score + cover_letter)")

try:
    jobs = db.get_jobs(TEST_CHAT_ID)
    job_id = jobs[0][0]
    db.update_job(job_id, TEST_CHAT_ID, 8, "Dear Hiring Manager...")
    # Confirm score is set
    with db._get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT score, cover_letter FROM jobs WHERE id = %s AND chat_id = %s",
                        (job_id, TEST_CHAT_ID))
            row = cur.fetchone()
    if row and row[0] == 8 and row[1] == "Dear Hiring Manager...":
        ok("update_job sets score and cover_letter")
    else:
        fail("update_job", f"row={row}")
except Exception as e:
    fail("update_job", str(e))

# Score second job too
try:
    all_j = db.get_jobs(TEST_CHAT_ID)
    if all_j:
        db.update_job(all_j[0][0], TEST_CHAT_ID, 9, "Letter for DS")
    ok("update_job second job")
except Exception as e:
    fail("update_job second", str(e))

# ── get_jobs_to_apply ──────────────────────────────────────────────────────────
section("7. jobs: get_jobs_to_apply")

try:
    to_apply = db.get_jobs_to_apply(TEST_CHAT_ID, min_score=7)
    if len(to_apply) == 2:
        ok("get_jobs_to_apply returns both jobs with score>=7")
    else:
        fail("get_jobs_to_apply count", f"expected 2, got {len(to_apply)}")
except Exception as e:
    fail("get_jobs_to_apply", str(e))

try:
    to_apply_high = db.get_jobs_to_apply(TEST_CHAT_ID, min_score=9)
    if len(to_apply_high) == 1:
        ok("get_jobs_to_apply min_score=9 filters correctly - 1 of 2 returned")
    else:
        fail("get_jobs_to_apply min_score filter", f"got {len(to_apply_high)}")
except Exception as e:
    fail("get_jobs_to_apply min_score", str(e))

# ── mark_applied ───────────────────────────────────────────────────────────────
section("8. jobs: mark_applied (applied / skipped)")

try:
    jobs_before = db.get_jobs_to_apply(TEST_CHAT_ID, min_score=7)
    first_id = jobs_before[0][0]
    db.mark_applied(first_id, TEST_CHAT_ID, status=1)
    jobs_after = db.get_jobs_to_apply(TEST_CHAT_ID, min_score=7)
    if len(jobs_after) == len(jobs_before) - 1:
        ok("mark_applied(status=1) removes job from to-apply list")
    else:
        fail("mark_applied status=1", f"before={len(jobs_before)}, after={len(jobs_after)}")
except Exception as e:
    fail("mark_applied status=1", str(e))

try:
    jobs_now = db.get_jobs_to_apply(TEST_CHAT_ID, min_score=7)
    second_id = jobs_now[0][0]
    db.mark_applied(second_id, TEST_CHAT_ID, status=2)
    jobs_final = db.get_jobs_to_apply(TEST_CHAT_ID, min_score=7)
    if len(jobs_final) == 0:
        ok("mark_applied(status=2) removes job from to-apply list")
    else:
        fail("mark_applied status=2", f"remaining={len(jobs_final)}")
except Exception as e:
    fail("mark_applied status=2", str(e))

# ── chat_id isolation ──────────────────────────────────────────────────────────
section("9. chat_id isolation (multi-user safety)")

OTHER_CHAT = 888888888
try:
    with db._get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM jobs WHERE chat_id = %s", (OTHER_CHAT,))
        conn.commit()

    other_job = dict(SAMPLE_JOB, link="https://test.example.com/job/other")
    db.save_job(other_job, OTHER_CHAT)

    my_jobs = db.count_jobs(TEST_CHAT_ID)
    other_jobs = db.count_jobs(OTHER_CHAT)

    if other_jobs == 1 and my_jobs == 2:
        ok("save_job isolates by chat_id", f"user1={my_jobs}, user2={other_jobs}")
    else:
        fail("chat_id isolation", f"user1={my_jobs}, user2={other_jobs}")

    # Cleanup other
    with db._get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM jobs WHERE chat_id = %s", (OTHER_CHAT,))
        conn.commit()
except Exception as e:
    fail("chat_id isolation", str(e))

# ── get_cover_letter / get_job_link ───────────────────────────────────────────
section("10. jobs: get_cover_letter + get_job_link")

try:
    with db._get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM jobs WHERE chat_id = %s LIMIT 1", (TEST_CHAT_ID,))
            row = cur.fetchone()
    if row:
        jid = row[0]
        letter = db.get_cover_letter(jid, TEST_CHAT_ID)
        if letter and len(letter) == 3:
            ok("get_cover_letter returns (title, company, text)")
        else:
            fail("get_cover_letter", f"got: {letter}")

        link = db.get_job_link(jid, TEST_CHAT_ID)
        if link and link.startswith("https://"):
            ok("get_job_link returns URL", link)
        else:
            fail("get_job_link", f"got: {link}")

        # Wrong chat_id returns None
        letter_wrong = db.get_cover_letter(jid, 111)
        link_wrong = db.get_job_link(jid, 111)
        if letter_wrong is None and link_wrong is None:
            ok("get_cover_letter + get_job_link return None for wrong chat_id")
        else:
            fail("chat_id guard on get functions")
    else:
        fail("no jobs to test get_cover_letter")
except Exception as e:
    fail("get_cover_letter/get_job_link", str(e))

# ── reset_scores ───────────────────────────────────────────────────────────────
section("11. jobs: reset_scores")

try:
    # Save a fresh pending job with a score, then reset it
    fresh_job = dict(SAMPLE_JOB, link="https://test.example.com/job/reset-test")
    db.save_job(fresh_job, TEST_CHAT_ID)
    with db._get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM jobs WHERE chat_id = %s AND link = %s",
                (TEST_CHAT_ID, fresh_job["link"])
            )
            fresh_id = cur.fetchone()[0]
    db.update_job(fresh_id, TEST_CHAT_ID, 7, "Some letter")

    # Confirm score is set
    with db._get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT score FROM jobs WHERE id = %s", (fresh_id,))
            score_before = cur.fetchone()[0]

    db.reset_scores(TEST_CHAT_ID)

    with db._get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT score, cover_letter FROM jobs WHERE id = %s", (fresh_id,))
            row = cur.fetchone()

    if score_before == 7 and row[0] is None and row[1] is None:
        ok("reset_scores nullifies score/cover_letter for pending jobs (applied=0)")
    else:
        fail("reset_scores", f"score_before={score_before}, after: score={row[0]}, letter={row[1]}")
except Exception as e:
    fail("reset_scores", str(e))

# ── get_stats ──────────────────────────────────────────────────────────────────
section("12. jobs: get_stats")

try:
    stats = db.get_stats(TEST_CHAT_ID)
    required_keys = ["total", "scored", "avg_score", "applied", "skipped"]
    for k in required_keys:
        if k not in stats:
            fail(f"get_stats missing key '{k}'")
        else:
            ok(f"get_stats['{k}'] = {stats[k]}")

    # 2 original jobs + 1 added in reset_scores test = 3
    if stats["total"] == 3:
        ok("get_stats total count correct", "3 jobs in DB")
    else:
        fail("get_stats total", f"expected 3, got {stats['total']}")

    if stats["applied"] == 1 and stats["skipped"] == 1:
        ok("get_stats applied=1, skipped=1 correct")
    else:
        fail("get_stats applied/skipped", f"applied={stats['applied']}, skipped={stats['skipped']}")
except Exception as e:
    fail("get_stats", str(e))

# ── CLI_CHAT_ID sentinel ───────────────────────────────────────────────────────
section("13. CLI_CHAT_ID sentinel")

try:
    if db.CLI_CHAT_ID == 0:
        ok("CLI_CHAT_ID == 0")
    else:
        fail("CLI_CHAT_ID", f"expected 0, got {db.CLI_CHAT_ID}")
except Exception as e:
    fail("CLI_CHAT_ID", str(e))

# ── Pool exhaustion (concurrent access) ───────────────────────────────────────
section("14. Connection pool — concurrent connections")

try:
    import threading
    errors = []

    def worker(n):
        try:
            with db._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT %s", (n,))
                    cur.fetchone()
        except Exception as e:
            errors.append(str(e))

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    if not errors:
        ok("8 concurrent threads all got connections successfully")
    else:
        fail("concurrent pool access", "; ".join(errors))
except Exception as e:
    fail("concurrent pool test", str(e))

# ── Cleanup ────────────────────────────────────────────────────────────────────
cleanup()

# ── Summary ────────────────────────────────────────────────────────────────────
print(f"\n{'='*55}")
print("  SUMMARY")
print(f"{'='*55}")

passed = sum(1 for r in results if r[0] == "PASS")
failed = sum(1 for r in results if r[0] == "FAIL")
total = len(results)

print(f"\n  Total : {total}")
print(f"  Passed: {passed}  OK")
print(f"  Failed: {failed}  FAIL")

if failed:
    print("\n  FAILED tests:")
    for r in results:
        if r[0] == "FAIL":
            print(f"    FAIL: {r[1]}" + (f" - {r[2]}" if r[2] else ""))

print(f"\n  {'ALL TESTS PASSED' if failed == 0 else 'SOME TESTS FAILED'}")
print()
