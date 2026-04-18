"""Curated lists of company board identifiers for each ATS platform.

To add a company:
1. Find its career page (e.g., company.com/careers)
2. Identify the ATS from the job listing URL
3. Extract the board slug (the identifier in the API URL)
4. Add to the appropriate dict below

Verify a Greenhouse slug works:
  curl -s https://boards-api.greenhouse.io/v1/boards/{slug}/jobs | python -c \
      "import sys,json; print(len(json.load(sys.stdin).get('jobs',[])))"
"""

# Greenhouse: boards-api.greenhouse.io/v1/boards/{board_id}/jobs
# All entries below verified to return >0 jobs as of April 2026.
GREENHOUSE_BOARDS: dict[str, str] = {
    # Large international — remote-friendly, hiring in EU/Poland
    "canonical": "Canonical",
    "cloudflare": "Cloudflare",
    "datadog": "Datadog",
    "gitlab": "GitLab",
    "twilio": "Twilio",
    "elastic": "Elastic",
    "grafanalabs": "Grafana Labs",
    "figma": "Figma",
    "intercom": "Intercom",
    "unity3d": "Unity",
    "duolingo": "Duolingo",
    "pagerduty": "PagerDuty",
    "cockroachlabs": "Cockroach Labs",
    "newrelic": "New Relic",
    "samsara": "Samsara",
    "wikimedia": "Wikimedia Foundation",
}

# Lever: api.lever.co/v0/postings/{company}
# NOTE: Lever public API returns errors for most slugs as of April 2026.
# Add verified slugs here as they are found.
LEVER_COMPANIES: dict[str, str] = {}

# Workable: apply.workable.com/api/v3/accounts/{subdomain}/jobs (POST)
# NOTE: API returns 0 results for most tested slugs as of April 2026.
# Add verified slugs here as they are found.
WORKABLE_COMPANIES: dict[str, str] = {}
