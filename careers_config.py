"""Configuration for corporate career page scrapers.

Each entry specifies the ATS platform and the parameters needed to query
the company's job feed.

To find a Workday URL for a new company:
1. Go to company's careers page and open a job listing
2. Look for "myworkdayjobs.com" in the URL
3. The URL pattern is:
   https://{tenant}.{instance}.myworkdayjobs.com/en-US/{site_name}/job/...
4. The API endpoint is:
   https://{tenant}.{instance}.myworkdayjobs.com/wday/cxs/{tenant}/{site_name}/jobs
5. Test: curl -s -X POST "<endpoint>" -H "Content-Type: application/json" \\
   -d '{"appliedFacets":{},"limit":1,"offset":0,"searchText":"intern"}'
"""

# Workday-based companies — verified API endpoints
WORKDAY_COMPANIES: list[dict] = [
    {
        "company": "Shell",
        "tenant": "shell",
        "instance": "wd3",
        "site": "ShellCareers",
    },
]

# SuccessFactors / custom career sites — each needs per-company parsing
# NOTE: These require individual research per company.
# Add entries as API endpoints are discovered and verified.
CUSTOM_CAREER_SITES: list[dict] = []
