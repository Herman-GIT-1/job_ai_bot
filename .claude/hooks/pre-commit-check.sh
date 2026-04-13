#!/bin/bash
# Hook: runs before git commit commands
# Checks for common mistakes before committing

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)

# Only act on git commit commands
if [[ "$COMMAND" != *"git commit"* && "$COMMAND" != *"git -C"*"commit"* ]]; then
  echo '{"continue": true}'
  exit 0
fi

ISSUES=""

# Check if .env is staged
if git diff --cached --name-only 2>/dev/null | grep -q '\.env$'; then
  ISSUES="${ISSUES}\n- .env is staged! Remove it with: git reset HEAD .env"
fi

# Check for hardcoded API keys in staged files
if git diff --cached 2>/dev/null | grep -qiE '(sk-ant-|Bearer [a-zA-Z0-9]{20,}|ANTHROPIC_API_KEY\s*=\s*["\x27]sk-)'; then
  ISSUES="${ISSUES}\n- Possible API key/token found in staged changes!"
fi

if [ -n "$ISSUES" ]; then
  cat <<EOF
{
  "continue": false,
  "reason": "Pre-commit check failed:${ISSUES}\nFix issues before committing."
}
EOF
  exit 2
fi

echo '{"continue": true}'
exit 0
