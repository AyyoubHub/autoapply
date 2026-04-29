# AutoApply — APEC Edition

**AutoApply** is a Python command-line tool that automates job hunting on [APEC](https://www.apec.fr).
It drives a real browser session with [Selenium](https://www.selenium.dev/) and
[undetected-chromedriver](https://github.com/ultrafunkamsterdam/undetected-chromedriver)
to search, score, and apply to job listings in a single run — no browser extensions,
no API keys, and no captcha hacks needed.

> [!WARNING]
> **JobTeaser support is experimental and not yet fully functional.**
> The APEC module is the stable, production-ready component of this project.
> The JobTeaser module is under active development and may not work reliably — it is
> listed in the menu for preview purposes only.

---

## How it works

AutoApply runs in two phases:

```
Phase 1 — Discovery
  For each keyword you enter:
    Browse APEC search results page-by-page
    Collect unique job URLs
    Score each job by how many of your keywords match it
    Stop early when a full page yields 0 new results

Phase 2 — Application (best matches first)
  For jobs scored highest:
    Skip if already applied (checks SQLite history.db)
    Skip if AI-rejected in a previous run (skips Gemini compute)
    Skip if keyword doesn't appear in the job description
    Skip if the job routes to an external site
    Click through the native APEC 3-step modal
    Detect and log the confirmation banner
```

This guarantees you always apply to the most relevant listings first, and never
re-apply to a job you already submitted.

---

## Features

- **Multi-keyword search** — enter several keywords at once; jobs that match more keywords rank higher.
- **SQLite History Tracking** — Persistent storage of every job found, its state (`Applied`, `AI Rejected`, `Failed`), and search context.
- **Smart Skip Policy** — Automatically skips jobs already processed or rejected by AI to save time and compute.
- **Force Reprocess Option** — Optional override at startup to re-evaluate previously seen or rejected jobs.
- **Date-range filter** — restrict discovery to last 24 h, 7 days, 30 days, or all time.
- **Contract filter** — CDI, CDD, Alternance, or Intérim.
- **Sort order** — by date or by APEC relevance score.
- **Configurable page cap** — for broad "all time" searches, limit how many pages to scan per keyword (`apec_max_pages_per_keyword` in config).
- **Already-applied detection** — uses SQLite database to ensure URL uniqueness and avoid duplicate applications.
- **External job skip** — jobs that redirect to a third-party site are never submitted.
- **Session crash recovery** — `InvalidSessionIdException` / `WebDriverException` are caught; the run ends cleanly rather than hanging.
- **Ctrl-C safe** — press Ctrl-C at any time for a clean exit with a final count.
- **Standardized Timezone** — All database entries and logs use **Europe/Paris** time for accurate auditing.

---

## Requirements

| Dependency | Version |
|------------|---------|
| Python | 3.9 or newer |
| Ungoogled Chromium *or* Google Chrome | Latest stable |
| See `requirements.txt` | `selenium ≥ 4.0`, `undetected-chromedriver`, `questionary`, `tzdata` |

---

## Setup

### 1. Clone and create a virtual environment

```bash
git clone https://github.com/AyyoubHub/autoapply.git
cd autoapply

python -m venv .venv
```

Activate it:

```bash
# macOS / Linux
source .venv/bin/activate

# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1
```

### 2. Run — everything else is automatic

```bash
python main.py
```

`main.py` includes a **first-run bootstrap** that runs silently on repeat launches:

| Step | What happens |
|------|--------------|
| **1** | Checks `requirements.txt` and installs any missing Python packages via `pip` |
| **2** | Creates `configs/config.json` (from the example) if it doesn't exist — prompts only for your email and APEC password |
| **3** | Downloads an isolated Ungoogled Chromium binary for your OS/architecture into `browser/chromium/` and saves the path to `config.json` automatically |

---

## Usage

From the project root:

```bash
python main.py
```

A menu lets you select the platform (APEC), then you answer a short series of prompts:

| Prompt | Description |
|--------|-------------|
| **Keywords** | Space or comma-separated terms. |
| **Force Reprocess** | `Yes/No`. If Yes, ignores history and re-evaluates all found jobs. |
| **Date range** | `Last 24 h` / `Last 7 days` / `Last 30 days` / `All time`. |
| **Contract type** | CDI, CDD, Alternance, or Intérim. |
| **Sort by** | `Date` (newest first) or `Score` (APEC relevance). |

---

## Project layout

```
autoapply/
├── main.py                          # Entry point — platform menu
├── requirements.txt                 # Python dependencies
├── history.db                       # ← created at runtime (SQLite database, gitignored)
├── scripts/
│   ├── apec.py                      # APEC automation engine
│   ├── jobteaser.py                 # JobTeaser automation (experimental)
│   ├── db_manager.py                # SQLite state and run tracking logic
│   ├── utils.py                     # Config loader, logging, ChromeDriver factory
│   ├── migrate_history.py           # Legacy JSON to SQLite migration tool
│   └── deduplicate_db.py            # DB maintenance: remove duplicate URLs
├── configs/
│   ├── config.example.json          # Template — copy to config.json
│   └── jobteaser.search.example.json
├── browser/                         # ← created by install_browser.py (gitignored)
├── logs/                            # ← created at runtime (gitignored)
├── scratch/                         # Legacy JSON history (backups)
└── tests/                           # Unit and integration tests
```

---

## Security

| What | Status |
|------|--------|
| `configs/config.json` (real credentials) | ✅ gitignored |
| `.env` (API keys) | ✅ gitignored |
| `history.db` (application history) | ✅ gitignored |
| `browser/` (binary, not source) | ✅ gitignored |
| `logs/` (runtime logs) | ✅ gitignored |

Never run `git add .` — always stage files explicitly to avoid accidentally
committing credentials or personal data.

---

## Disclaimer

This software is provided for **educational and personal use only**.  
Automating actions on third-party websites may violate their terms of service.  
You are solely responsible for how you use it — use only on accounts you own
and in line with each platform's terms and applicable law.
