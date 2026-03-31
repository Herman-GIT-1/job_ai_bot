# rules/git.md

Read this before every commit.

---

## Commit format

```
<type>: <short description in English>
```

| Type | When |
|---|---|
| `fix` | Bug fix |
| `feat` | New feature or module |
| `refactor` | Restructuring, no behavior change |
| `docs` | README, CLAUDE.md, rules/ only |
| `chore` | Dependencies, .env.example, config |

One logical change = one commit. If the diff touches 3 unrelated things — split into 3 commits.

---

## Pre-commit checklist

Before running `git commit`, verify:

- [ ] `.env` is NOT staged (`git status` should not show it)
- [ ] `jobs.db` is NOT staged
- [ ] No API keys or tokens in any changed file
- [ ] No hardcoded `chat_id` values inside functions (use `CLI_CHAT_ID`)
- [ ] No `?` placeholders in SQL (must be `%s`)
- [ ] Every new DB function has `chat_id: int` param and `WHERE chat_id = %s`
- [ ] Every new user-facing string is in `strings.py` in all 3 languages
- [ ] Every new `_fetch_*` function wraps everything in try/except and returns [] on error

---

## What must never be committed

- `.env` — contains API keys
- `jobs.db` — local SQLite leftover, not used in production
- `__pycache__/` — should be in .gitignore
- Any file with a hardcoded `sk-ant-*` or `Bearer` token

If you accidentally commit a secret: rotate the key immediately, then use
`git filter-branch` or `git rebase` to remove it from history.

---

## .gitignore must include

```
.env
jobs.db
__pycache__/
*.pyc
.DS_Store
```

If any of these are missing — add them before the next commit.
