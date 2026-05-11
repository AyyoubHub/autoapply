# AutoApply

**AutoApply** is a Python CLI tool that automates job hunting on [APEC](https://www.apec.fr) and [JobTeaser](https://www.jobteaser.com).
It drives a real browser session with [Selenium](https://www.selenium.dev/) and [undetected-chromedriver](https://github.com/ultrafunkamsterdam/undetected-chromedriver) to discover, filter, and apply to job listings automatically — no browser extensions, no API keys required.

---

## How it works

```
Phase 1 — Discovery
  Browse job listings page by page
  Collect unique job URLs
  Stop early when a full page yields 0 new results
  (APEC) Score each job by how many keywords match — apply best matches first

Phase 2 — Application (per job)
  Skip if already processed in a previous run (checks SQLite autoapply.db)
  Skip if AI-rejected in a previous run (avoids re-spending Gemini quota)
  Skip if the job is only available via external redirect
  Click through the native application modal step by step
  Detect and log the confirmation banner
```

---

## Features

| Feature | Detail |
|---|---|
| **Multi-platform** | APEC and JobTeaser share a single `BaseJobPortal` architecture |
| **Smart skip policy** | SQLite tracks every job — applied and AI-rejected are never retried; failed jobs are |
| **Robust waits** | Explicit `WebDriverWait` conditions instead of bare sleeps |
| **Session recovery** | Automatic browser restart + re-login on crash without aborting the run |
| **First-run bootstrap** | Auto-installs pip dependencies, creates config, downloads Chromium |
| **Headless support** | Run fully in the background via `"headless": true` in config |
| **AI filtering (optional)** | Gemini can pre-screen jobs by semantic relevance — enable by adding `GEMINI_API` to `.env` |
| **Structured logging** | Timestamped per-run log files in `logs/` with platform-prefixed entries |

---

## Requirements

| Dependency | Version |
|---|---|
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

The **first-run bootstrap** handles everything silently on repeat launches:

| Step | What happens |
|---|---|
| **1** | Checks `requirements.txt` and installs any missing packages via `pip` |
| **2** | Creates `configs/config.json` from the example if it doesn't exist — prompts for credentials and form data |
| **3** | Downloads an isolated Ungoogled Chromium into `browser/chromium/` and saves the path to `config.json` |

---

## Usage

```bash
python main.py
```

A menu asks which platform to launch. You then answer a short series of prompts:

### APEC

| Prompt | Description |
|---|---|
| **Keywords** | Space or comma-separated terms. Jobs matching more keywords are prioritised. |
| **Date range** | `Last 24 h` / `Last 7 days` / `Last 30 days` / `All time` |
| **Contract type** | CDI, CDD, Alternance, Intérim |
| **Sort by** | `Date` (newest first) or `Score` (APEC relevance) |
| **Max runtime** | Time limit in minutes |
| **Force reprocess** | Re-evaluate jobs that were previously skipped or failed |

### JobTeaser

| Prompt | Description |
|---|---|
| **Keywords** | Search term(s) |
| **Contract type(s)** | Multi-select: CDI, CDD, Stage, Alternance, … |
| **Experience level(s)** | Multi-select: young graduate, 3–5 yrs, 6–10 yrs, … |
| **Remote preference** | Full remote / partial / on-site / no filter |
| **Job language(s)** | Français, English, or both |
| **Sort by** | Date or Relevance |
| **Max runtime** | Time limit in minutes |
| **Force reprocess** | Re-evaluate previously skipped jobs |

> **JobTeaser only applies to internal offers** (`Postuler` / `Candidature simplifiée`). External redirects are logged and skipped automatically.

---

## Configuration

All settings live in `configs/config.json` (created automatically on first run from `config.example.json`).

| Key | Description | Default |
|---|---|---|
| `apec_email` / `apec_password` | APEC login credentials | — |
| `jobteaser_email` / `jobteaser_password` | JobTeaser login credentials | — |
| `browser_executable_path` | Path to Chrome/Chromium binary | set by bootstrap |
| `headless` | Run browser in background | `false` |
| `apec_max_pages_per_keyword` | Max pages to scan in "All time" mode | `3` |
| `form_data.fullname` | Your full name (injected into application forms) | — |
| `form_data.phoneNumber` | Phone number in `+33XXXXXXXXX` format | — |
| `form_data.gender` | `"Homme"`, `"Femme"`, or `"Autre"` | — |
| `form_data.coverLetterContent` | Default cover letter text (used when the field is required) | `""` |
| `form_data.linkedin` | LinkedIn profile URL (optional) | — |
| `form_data.github` | GitHub profile URL (optional) | — |

### AI filtering (optional)

Add your Gemini API key to `.env` (copy `.env.example`):

```
GEMINI_API=your_key_here
```

When configured, Gemini screens each job description against your keywords before applying. Without a key the pipeline continues unfiltered.

---

## Project layout

```
autoapply/
├── main.py                          # Entry point — bootstrap + platform menu
├── requirements.txt
├── configs/
│   └── config.example.json          # Template — copy to config.json and fill in
├── scripts/
│   ├── base_portal.py               # Shared base class (loop, retries, DB, Selenium helpers)
│   ├── apec.py                      # APEC automation engine
│   ├── jobteaser.py                 # JobTeaser automation engine
│   ├── db_manager.py                # SQLite state and run tracking
│   ├── ai_agent.py                  # Gemini relevance filter (optional)
│   ├── utils.py                     # Config loader, logging, ChromeDriver factory
│   ├── install_browser.py           # Downloads Ungoogled Chromium
│   ├── deduplicate_db.py            # DB maintenance: remove duplicate URLs
│   ├── migrate_history.py           # Legacy JSON → SQLite migration
│   └── migrate_unique_url.py        # One-time DB schema migration
├── tests/                           # Unit and integration tests (pytest)
├── docs/                            # Internal analysis notes
├── browser/                         # ← created by bootstrap (gitignored)
├── logs/                            # ← created at runtime (gitignored)
└── scratch/                         # ← runtime cache (gitignored)
```

---

## Security

| What | Status |
|---|---|
| `configs/config.json` (credentials) | ✅ gitignored |
| `.env` (Gemini API key) | ✅ gitignored |
| `autoapply.db` (application history) | ✅ gitignored |
| `browser/` (binary) | ✅ gitignored |
| `logs/` and `scratch/` (runtime data) | ✅ gitignored |

> **Never run `git add .`** — always stage files explicitly.

---

## Running tests

```bash
# Activate the venv first
python -m pytest tests/ -v
```

Tests that require the browser (Selenium) are tagged and skipped automatically when `undetected-chromedriver` is unavailable outside the venv.

---

## Disclaimer

This software is provided for **educational and personal use only**.
Automating actions on third-party websites may violate their terms of service.
You are solely responsible for how you use it — use only on accounts you own and in line with each platform's terms and applicable law.
