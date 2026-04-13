---
paths:
  - "bot.py"
  - "strings.py"
---

# rules/bot.md

Read this before touching `bot.py` or `strings.py`.

---

## Never hardcode user-facing strings in bot.py

```python
# WRONG
await update.message.reply_text("Resume not found.")

# CORRECT
lang = get_user_lang(chat_id)
await update.message.reply_text(t(lang, "resume_not_found"))
```

Every string the user sees must live in `strings.py`.

---

## Adding a new string

Add the key to ALL THREE languages in `strings.py`. If a translation is missing,
`t()` falls back to English — but missing keys in `"en"` return the key name itself,
which will be visible to users.

```python
# strings.py — add to all three dicts
"en": {
    "my_new_key": "Something happened: {detail}",
},
"ru": {
    "my_new_key": "Произошло: {detail}",
},
"pl": {
    "my_new_key": "Coś się stało: {detail}",
},
```

Use `{named}` placeholders, never `{0}` or f-strings inside the string value.

Call with: `t(lang, "my_new_key", detail="value")`

---

## owner_only decorator

All command handlers must be wrapped with `@owner_only`.
This guards against strangers using the bot while it's in single-user mode.

When opening to multiple users (Priority 3), replace `owner_only` with `@allowed`
(whitelist) — do not remove the guard entirely without adding a replacement.

---

## Error handling in handlers

```python
@owner_only
async def cmd_scrape(update, context):
    try:
        # ... logic
    except Exception as e:
        lang = get_user_lang(update.effective_chat.id)
        await update.message.reply_text(t(lang, "error_generic", error=str(e)))
```

Never let raw exceptions bubble to the user.
Never expose internal paths, DB errors, or API keys in error messages.

---

## Inline buttons — callback_data format

Pattern: `action:param1:param2`

Examples currently used:
- `apply:{job_id}` — mark job as applied
- `skip:{job_id}` — mark job as skipped
- `letter:{job_id}` — send cover letter
- `lang:{code}` — set language
- `city:{name}` — set city for scrape

When adding new buttons: follow the same pattern, parse with `.split(":")`.

---

## Language detection

Always read language from DB at the start of a handler:

```python
chat_id = update.effective_chat.id
lang = get_user_lang(chat_id)
```

Never cache language in memory between handler calls — user may change it mid-session.

---

## Long operations — send "processing" message first

For scrape, score, and any operation >2s:

```python
msg = await update.message.reply_text(t(lang, "scrape_searching", city=city))
# ... do the work ...
await msg.edit_text(t(lang, "scrape_done", found=found, saved=saved))
```

This prevents Telegram from showing "bot is not responding".

---

## Adding a new language

1. Add full dict to `TEXTS` in `strings.py` (copy from `"en"`, translate all values)
2. Add inline button in `/language` handler: `InlineKeyboardButton("🇺🇦 UA", callback_data="lang:uk")`
3. Add `lang_set` string for the new language in all existing language dicts
4. Test: send `/language`, pick new language, send `/start` — all strings must appear
