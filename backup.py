"""
Database backup: pg_dump → gzip → send to ADMIN_CHAT_ID via Telegram.

Can be called:
  - as a standalone script: python backup.py
  - programmatically: run_backup(bot, admin_chat_id)
"""

import datetime
import gzip
import io
import logging
import os
import subprocess

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL", "")
ADMIN_CHAT_ID = int(os.environ.get("TELEGRAM_CHAT_ID", "0"))


def _dump_db() -> bytes:
    """Run pg_dump and return raw SQL bytes. Raises on failure."""
    result = subprocess.run(
        ["pg_dump", DATABASE_URL],
        capture_output=True,
        check=True,
    )
    return result.stdout


def create_backup_bytes() -> tuple[bytes, str]:
    """Return (gzipped SQL bytes, filename). Raises on pg_dump failure."""
    sql = _dump_db()
    buf = io.BytesIO()
    date_str = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    filename = f"backup_{date_str}.sql.gz"
    with gzip.GzipFile(filename=filename, mode="wb", fileobj=buf) as gz:
        gz.write(sql)
    return buf.getvalue(), filename


async def send_backup(bot, chat_id: int) -> None:
    """Compress DB and send as document. Reports errors back to chat_id."""
    try:
        data, filename = create_backup_bytes()
        await bot.send_document(
            chat_id=chat_id,
            document=io.BytesIO(data),
            filename=filename,
            caption=f"DB backup · {filename}",
        )
        logger.info("Backup sent: %s (%d bytes compressed)", filename, len(data))
    except Exception as e:
        logger.error("Backup failed: %s", e)
        await bot.send_message(chat_id=chat_id, text=f"Backup failed: {e}")


if __name__ == "__main__":
    import asyncio
    import os
    from telegram import Bot

    logging.basicConfig(level=logging.INFO)
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    asyncio.run(send_backup(Bot(token), ADMIN_CHAT_ID))
