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
    Skip if already applied
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
- **Date-range filter** — restrict discovery to last 24 h, 7 days, 30 days, or all time.
- **Contract filter** — CDI, CDD, Alternance, or Intérim.
- **Sort order** — by date or by APEC relevance score.
- **Configurable page cap** — for broad "all time" searches, limit how many pages to scan per keyword (`apec_max_pages_per_keyword` in config).
- **Already-applied detection** — two independent DOM strategies skip jobs you've already submitted.
- **External job skip** — jobs that redirect to a third-party site are never submitted.
- **Session crash recovery** — `InvalidSessionIdException` / `WebDriverException` are caught; the run ends cleanly rather than hanging.
- **Ctrl-C safe** — press Ctrl-C at any time for a clean exit with a final count.
- **Timestamped logs** — every run writes a structured log to `logs/` (gitignored).

---

## Requirements

| Dependency | Version |
|------------|---------|
| Python | 3.9 or newer |
| Ungoogled Chromium *or* Google Chrome | Latest stable |
| See `requirements.txt` | `selenium ≥ 4.0`, `undetected-chromedriver`, `questionary` |

> **Why Ungoogled Chromium?**  
> It pairs well with `undetected-chromedriver` and avoids telemetry.  
> Google Chrome works too — just point `browser_executable_path` at it.

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

After the first run, all three steps complete in under a second and the platform menu appears immediately.

> **Manual browser install** — if you prefer to manage the browser yourself, or if you are on Linux, run the install script directly:
> ```bash
> python scripts/install_browser.py
> ```
> Then set `browser_executable_path` in `configs/config.json` to the printed path.

<details>
<summary>Manual browser install instructions</summary>

#### macOS

```bash
# Homebrew (system-wide — not isolated)
brew install --cask eloston-chromium

# Or download a .dmg directly from:
# https://github.com/ungoogled-software/ungoogled-chromium-macos/releases
```

#### Windows

Download the latest portable `.zip` from:
https://github.com/ungoogled-software/ungoogled-chromium-windows/releases

Extract anywhere (e.g. `C:\chromium\`) — no installer needed.

Executable path example: `C:\chromium\chrome.exe`

#### Linux

```bash
# Arch Linux (AUR)
yay -S ungoogled-chromium

# Debian / Ubuntu — follow the repo at:
# https://github.com/ungoogled-software/ungoogled-chromium-debian

# Flatpak (distro-independent)
flatpak install flathub com.github.Eloston.UngoogledChromium

# AppImage (portable — works on most distros)
# Download from https://github.com/ungoogled-software/ungoogled-chromium-binaries/releases
chmod +x ungoogled-chromium-*.AppImage
```

</details>

### 3. (Optional) Install Tectonic for PDF compilation

[Tectonic](https://tectonic-typesetting.github.io) is only needed if you use
the AI agent feature to compile adapted LaTeX CVs.  It is **not required** to
run the APEC automation.

<details>
<summary>Tectonic install instructions</summary>

#### macOS

```bash
# Homebrew
brew install tectonic

# Or via Cargo (requires Rust)
cargo install tectonic
```

#### Windows

```powershell
# winget
winget install tectonic-typesetting.tectonic

# Or via Cargo
cargo install tectonic

# Or download a pre-built binary from:
# https://github.com/tectonic-typesetting/tectonic/releases
```

#### Linux

```bash
# Cargo (recommended — works on any distro)
cargo install tectonic

# Ubuntu / Debian (may be older version)
sudo apt install tectonic

# Arch Linux (AUR)
yay -S tectonic-bin
```

</details>

---

## Usage

From the project root:

```bash
python main.py
```

A menu lets you select the platform (APEC), then you answer a short series of prompts:

| Prompt | Description |
|--------|-------------|
| **Keywords** | Space or comma-separated terms. Enter multiple for relevance scoring (e.g. `devops kubernetes`). Each keyword is searched separately; jobs appearing in more keyword results rank higher. |
| **Date range** | `Last 24 h` / `Last 7 days` / `Last 30 days` / `All time`. Date-filtered modes scan every page; "All time" uses the `apec_max_pages_per_keyword` cap from config. |
| **Contract type** | CDI, CDD, Alternance, or Intérim. |
| **Sort by** | `Date` (newest first) or `Score` (APEC relevance). |

---

## Configuration reference

`configs/config.json` — created from `configs/config.example.json`, **gitignored**.

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| `email` | string | ✅ | APEC account email |
| `apec_password` | string | ✅ | APEC account password |
| `jobteaser_password` | string | — | JobTeaser password (for that module only) |
| `browser_executable_path` | string | auto | Absolute path to Chrome or Chromium. **Set automatically** by the bootstrap on first run. Override manually to use a different browser. |
| `apec_max_pages_per_keyword` | integer | — | Max pages to scan per keyword when the **All time** date filter is chosen. Default: `3`. Ignored for date-filtered modes (those always scan all pages). |
| `cv_path` | string | — | Relative path to your base `.tex` CV (used by the AI agent). Default: `tex/default.tex`. |
| `form_data` | object | — | Personal details pre-filled in forms (JobTeaser module). Keys: `fullname`, `email`, `phone`, `github`, `linkedin`, `gender`. |

---

## Project layout

```
autoapply/
├── main.py                          # Entry point — platform menu
├── requirements.txt                 # Python dependencies
├── scripts/
│   ├── apec.py                      # APEC automation engine (two-phase)
│   ├── utils.py                     # Config loader, logging, ChromeDriver factory
│   └── install_browser.py           # One-shot browser downloader (stdlib only)
├── configs/
│   ├── config.example.json          # Template — copy to config.json
│   └── jobteaser.search.example.json
├── browser/                         # ← created by install_browser.py (gitignored)
│   └── chromium/
├── logs/                            # ← created at runtime (gitignored)
│   └── run_YYYY-MM-DD_HH-MM-SS.log
├── scratch/                         # Example output data (scraped job listings)
└── docs/                            # Research & URL analysis notes
```

---

## Security

| What | Status |
|------|--------|
| `configs/config.json` (real credentials) | ✅ gitignored |
| `.env` (API keys) | ✅ gitignored |
| `browser/` (binary, not source) | ✅ gitignored |
| `tex/` (personal CV files) | ✅ gitignored |
| `logs/` (runtime logs) | ✅ gitignored |
| `scratch/` (example output data) | ✅ committed — PII stripped |
| `docs/` (research notes) | ✅ committed — PII stripped |

Never run `git add .` — always stage files explicitly to avoid accidentally
committing credentials or personal data.

---

## Contributing

1. Fork the repository and create a branch for your change.
2. Keep commits focused — one logical change per commit.
3. Stage files explicitly (`git add <file>`) rather than `git add .`.
4. Open a pull request with a short description of the behavior change.

---

## Disclaimer

This software is provided for **educational and personal use only**.  
Automating actions on third-party websites may violate their terms of service.  
You are solely responsible for how you use it — use only on accounts you own
and in line with each platform's terms and applicable law.
