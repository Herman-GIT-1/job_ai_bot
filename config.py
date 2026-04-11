"""Centralised configuration constants.

All hard-coded values that were previously scattered across modules live here.
Import with:  from config import CITIES, JOBS_PAGE_SIZE, ...
"""

# ── Telegram bot behaviour ─────────────────────────────────────────────────────

CITIES = ["Warszawa", "Kraków", "Wrocław", "Gdańsk", "Poznań", "Remote"]

SCRAPE_COOLDOWN_MINUTES = 60   # cooldown between /scrape calls per user
JOBS_PAGE_SIZE = 5             # job cards sent per page in /jobs

# ── AI models ──────────────────────────────────────────────────────────────────

MODEL_SCORING       = "claude-haiku-4-5-20251001"   # fast, cheap, returns 1 int
MODEL_LETTER        = "claude-sonnet-4-6"           # quality matters for letters
MODEL_QUERY_BUILDER = "claude-sonnet-4-6"           # runs once per scrape
MODEL_FEEDBACK      = "claude-sonnet-4-6"           # resume feedback

# ── Scoring thresholds ─────────────────────────────────────────────────────────

DEFAULT_MIN_SCORE   = 6    # jobs shown in /jobs by default
HIGH_SCORE_ALERT    = 8    # threshold for "X high-score jobs" alert after scoring
LETTER_MIN_SCORE    = 7    # minimum score to generate a cover letter

# ── Resume ─────────────────────────────────────────────────────────────────────

RESUME_MIN_LENGTH = 100    # characters; shorter than this is rejected as invalid

# ── Database ───────────────────────────────────────────────────────────────────

JOB_EXPIRY_DAYS = 21       # pending jobs older than this are deleted by daily cleanup

# ── Telegram Mini App ──────────────────────────────────────────────────────────

import os as _os
WEBAPP_URL = _os.environ.get("WEBAPP_URL", "")  # e.g. https://your-service.railway.app

# ── Domain keyword registry ────────────────────────────────────────────────────
# Used by scraper._extract_tech() to populate the tech_stack field on each job.
# Organised by domain so it's easy to extend. The flat TECH_KEYWORDS list is
# derived automatically — import only TECH_KEYWORDS in other modules.

DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "it_languages": [
        "Python", "Java", "JavaScript", "TypeScript", "PHP", "Ruby",
        "C#", "C++", "Go", "Rust", "Kotlin", "Swift", "Scala", "Dart",
    ],
    "it_web": [
        "React", "Vue", "Angular", "Node.js", "Next.js", "Django",
        "Flask", "FastAPI", "Spring", "Rails", "Laravel", ".NET", "REST API",
        "GraphQL", "HTML", "CSS",
    ],
    "it_infra": [
        "Docker", "Kubernetes", "Git", "CI/CD", "Linux", "AWS", "GCP",
        "Azure", "Terraform", "Ansible", "Jenkins", "GitHub Actions",
    ],
    "it_databases": [
        "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch",
        "Cassandra", "SQLite", "Oracle", "SQL Server",
    ],
    "data_analytics": [
        "SQL", "pandas", "NumPy", "scikit-learn", "TensorFlow", "PyTorch",
        "R", "Spark", "Hadoop", "Airflow", "dbt", "Jupyter", "Databricks",
        "Snowflake", "BigQuery", "SPSS", "SAS", "Alteryx",
    ],
    "data_visualization": [
        "Tableau", "Power BI", "Looker", "Qlik", "Google Data Studio",
        "Excel", "Power Query", "VBA",
    ],
    "finance_banking": [
        "Bloomberg", "Reuters", "SWIFT", "Murex", "SAP", "Temenos",
        "Kondor", "Misys", "Access", "MiFID", "EMIR", "AML", "KYC",
        "IFRS", "Basel", "FATCA", "CFA", "FRM", "CPA",
        "reconciliation", "settlement", "treasury", "derivatives",
        "fixed income", "equity", "FX", "hedge fund", "trade finance",
    ],
    "accounting": [
        "Xero", "QuickBooks", "SAP FI", "Oracle Financials",
        "accounts payable", "accounts receivable", "GAAP", "ACCA",
    ],
    "marketing": [
        "Google Analytics", "Google Ads", "Facebook Ads", "Meta Ads",
        "HubSpot", "Salesforce", "Mailchimp", "SEO", "SEM", "CRM",
        "WordPress", "Shopify", "Semrush", "Ahrefs", "Hootsuite",
        "Buffer", "Adobe Analytics", "Google Tag Manager",
    ],
    "design": [
        "Figma", "Adobe XD", "Sketch", "InVision", "Photoshop",
        "Illustrator", "After Effects", "Premiere Pro", "Canva",
        "Zeplin", "Principle", "Balsamiq", "Axure",
    ],
    "management_ops": [
        "Jira", "Confluence", "Asana", "Trello", "Monday.com", "Notion",
        "Agile", "Scrum", "Kanban", "Lean", "Six Sigma", "PMP", "PRINCE2",
        "ERP", "SAP ERP", "Oracle ERP", "MS Project",
    ],
    "hr": [
        "Workday", "BambooHR", "Greenhouse", "Lever", "Taleo",
        "SAP SuccessFactors", "ATS", "HRIS", "LinkedIn Recruiter",
    ],
    "legal_compliance": [
        "GDPR", "compliance", "due diligence", "contract management",
        "regulatory reporting", "risk management",
    ],
    "logistics_supply": [
        "SAP MM", "SAP WM", "WMS", "ERP", "supply chain",
        "procurement", "inventory management",
    ],
}

# Flat list consumed by scraper._extract_tech() — add new domains above, not here.
TECH_KEYWORDS: list[str] = [kw for domain in DOMAIN_KEYWORDS.values() for kw in domain]
