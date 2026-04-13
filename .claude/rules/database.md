---
paths:
  - "database.py"
---

# rules/database.md

Read this before touching `database.py` or writing any SQL.

---

## The one rule that cannot be broken

Every public function takes `chat_id: int`. Every query filters by it.

```python
# WRONG — will mix data between users
def get_jobs():
    cur.execute("SELECT * FROM jobs")

# CORRECT
def get_jobs(chat_id: int) -> list:
    cur.execute("SELECT * FROM jobs WHERE chat_id = %s", (chat_id,))
```

If you write a query without `WHERE chat_id = %s` and user context exists — stop and fix it.

---

## Placeholders

Always `%s`. Never `?`. This is PostgreSQL, not SQLite.

```python
# WRONG
cur.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))

# CORRECT
cur.execute("SELECT * FROM jobs WHERE id = %s", (job_id,))
```

---

## Inserts — use ON CONFLICT, never INSERT OR IGNORE

```python
# WRONG — SQLite syntax, doesn't work in PostgreSQL
cur.execute("INSERT OR IGNORE INTO jobs ...")

# CORRECT
cur.execute("""
    INSERT INTO jobs (chat_id, title, link)
    VALUES (%s, %s, %s)
    ON CONFLICT (link, chat_id) DO NOTHING
""", (chat_id, title, link))
```

---

## Connection pool

Never create a new connection manually. Always use `_get_conn()`:

```python
# WRONG
conn = psycopg2.connect(DATABASE_URL)

# CORRECT
with _get_conn() as conn:
    with conn.cursor() as cur:
        cur.execute(...)
    conn.commit()
```

Pool is `ThreadedConnectionPool(minconn=2, maxconn=10)`.
Always commit after writes. Never commit inside a loop — batch writes, commit once.

---

## CLI sentinel

`CLI_CHAT_ID = 0` is used by `main.py` for CLI mode.
Never hardcode 0 inside functions. Import it: `from database import CLI_CHAT_ID`.

---

## Adding a new column

Always use `ADD COLUMN IF NOT EXISTS` so migrations are idempotent:

```python
cur.execute("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS my_col TEXT DEFAULT ''")
```

Add the migration inside `_apply_schema()` — it runs on every startup.

---

## Error handling in DB functions

```python
def save_job(job: dict, chat_id: int) -> None:
    try:
        with _get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(...)
            conn.commit()
    except Exception as e:
        print(f"[DB] save_job error: {e}")
        # Never re-raise — DB errors must not crash the pipeline
```

Read functions (get_*) can let exceptions propagate — callers handle them.
Write functions (save_*, update_*, mark_*) must catch and log.
