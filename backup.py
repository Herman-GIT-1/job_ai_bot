"""
Database backup: psycopg2 → SQL INSERT statements → gzip → Telegram.

No external tools required (no pg_dump). Works in any Python environment.

Can be called:
  - programmatically: await send_backup(bot, admin_chat_id)
  - as a standalone script: python backup.py
"""

import datetime
import gzip
import io
import logging
import os

import psycopg2
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL", "")
ADMIN_CHAT_ID = int(os.environ.get("TELEGRAM_CHAT_ID", "0"))

# Tables to back up, in dependency order (user_settings before jobs due to chat_id usage).
_TABLES = ["user_settings", "jobs"]


def _quote(value) -> str:
    """Minimal SQL quoting for backup output."""
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)
    # Strings: escape single quotes and backslashes
    escaped = str(value).replace("\\", "\\\\").replace("'", "''")
    return f"'{escaped}'"


def _dump_table(cur, table: str) -> str:
    """Return SQL INSERT statements for all rows in table."""
    cur.execute(f"SELECT * FROM {table}")  # noqa: S608 — internal, no user input
    rows = cur.fetchall()
    if not rows:
        return f"-- {table}: 0 rows\n"

    cols = [desc[0] for desc in cur.description]
    col_list = ", ".join(cols)
    lines = [f"-- {table}: {len(rows)} rows"]
    for row in rows:
        vals = ", ".join(_quote(v) for v in row)
        lines.append(
            f"INSERT INTO {table} ({col_list}) VALUES ({vals})"
            f" ON CONFLICT DO NOTHING;"
        )
    return "\n".join(lines) + "\n"


def create_backup_bytes() -> tuple[bytes, str]:
    """Connect to DB, dump all tables as SQL, return (gzipped bytes, filename)."""
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor() as cur:
            date_str = datetime.datetime.utcnow().strftime("%Y-%m-%d_%H-%M")
            header = (
                f"-- Job Bot backup · {date_str} UTC\n"
                f"-- Tables: {', '.join(_TABLES)}\n\n"
            )
            parts = [header]
            for table in _TABLES:
                parts.append(_dump_table(cur, table))
                parts.append("\n")
            sql_text = "".join(parts).encode("utf-8")
    finally:
        conn.close()

    buf = io.BytesIO()
    filename = f"backup_{date_str}.sql.gz"
    with gzip.GzipFile(filename=filename, mode="wb", fileobj=buf) as gz:
        gz.write(sql_text)
    logger.info("Backup created: %s (%d rows total, %d bytes compressed)",
                filename, sum(p.count("INSERT") for p in parts), len(buf.getvalue()))
    return buf.getvalue(), filename


async def send_backup(bot, chat_id: int) -> None:
    """Create backup and send as document. Reports errors back to chat_id."""
    try:
        data, filename = create_backup_bytes()
        await bot.send_document(
            chat_id=chat_id,
            document=io.BytesIO(data),
            filename=filename,
            caption=f"DB backup · {filename}",
        )
        logger.info("Backup sent: %s (%d bytes)", filename, len(data))
    except Exception as e:
        logger.error("Backup failed: %s", e)
        await bot.send_message(chat_id=chat_id, text=f"Backup failed: {e}")


if __name__ == "__main__":
    import asyncio
    from telegram import Bot

    logging.basicConfig(level=logging.INFO)
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    asyncio.run(send_backup(Bot(token), ADMIN_CHAT_ID))
