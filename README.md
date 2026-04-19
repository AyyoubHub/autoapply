# AutoApply

**AutoApply** is a Python tool that automates browsing and applying on French job platforms. It drives a real Chrome session with [Selenium](https://www.selenium.dev/) and [undetected-chromedriver](https://github.com/ultrafunkamsterdam/undetected-chromedriver) to reduce friction when you already have accounts and want to apply to many listings in one session.

## What it does

- **Main entry point** (`main.py`) — pick a platform and answer prompts for keywords, filters, and session length.
- **Supported platforms** (see `main.py`): **APEC** and **JobTeaser**. HelloWork is present in the codebase but disabled in the menu until you wire it back in.
- **JobTeaser** — search behavior is driven by `configs/jobteaser.search.json` (easy apply / “candidature simplifiée” only). See `docs/jobteaser_url_analysis.md` and `docs/jobteaser_filters.md` for URL and filter details.
- **Logging** — each run writes a timestamped file under `logs/` (for example `logs/run_YYYY-MM-DD_HH-MM-SS.log`). The `logs/` directory is gitignored.

## Requirements

- **Python** 3.9 or newer (3.12+ is fine; `requirements.txt` includes `setuptools` for undetected-chromedriver compatibility).
- **Google Chrome** installed.
- **Accounts** on the platforms you use, with **email and password** login. Social logins (Google, LinkedIn, etc.) are not handled by the scripts.

On **Windows**, Chrome’s major version is read from the registry so the driver matches your browser. On other systems, undetected-chromedriver can auto-detect; if you see version mismatches, align Chrome and chromedriver or adjust the driver setup in `scripts/utils.py` (`create_driver`).

## Setup

1. **Clone** this repository and open a terminal at the project root.

2. **Create a virtual environment** (recommended):

   ```bash
   python -m venv .venv
   ```

   Activate it — on Windows (PowerShell):

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

   On macOS/Linux:

   ```bash
   source .venv/bin/activate
   ```

3. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

4. **Credentials** — copy the example config and fill in your details:

   ```bash
   copy configs\config.example.json configs\config.json
   ```

   On Linux/macOS use `cp` instead of `copy`. Edit `configs/config.json` with your email and passwords for each platform you use.

5. **JobTeaser search profile** (required for JobTeaser):

   ```bash
   copy configs\jobteaser.search.example.json configs\jobteaser.search.json
   ```

   Adjust filters, default keyword, timeout, etc. `configs/jobteaser.search.json` is gitignored so your preferences are not committed.

### Customizing `jobteaser.search.json`

Use **[`docs/jobteaser_filters.md`](docs/jobteaser_filters.md)** as the reference for allowed values. It describes each JobTeaser filter (contract type, languages, study level, remote work, sectors, job functions, etc.) and the strings or IDs the site expects. Copy those values into your `configs/jobteaser.search.json` so the JSON matches what the URL would use.

| Config key | What to read in `jobteaser_filters.md` |
|------------|----------------------------------------|
| `contracts` | **Contract Type** — list of `contract=` values (e.g. `cdi`, `cdd`). |
| `work_experience_code` | **Experience Level** — one of `young_graduate`, `three_to_five_years`, etc. *(Optional; omit or leave empty to skip.)* |
| `languages` | **Language** — list of codes (`fr`, `en`, …). |
| `study_levels` | **Study Levels** — single code as a string (`1`–`6`). |
| `remote_types` | **Remote Work** — `remote_partial` or `remote_full`, or `null` to omit. |
| `duration` | **Duration** — `3`, `6`, `9`, … as a string, or `null` to omit. |
| `company_business_type` | **Company Category** — `large`, `startup`, `sme`, … or `null` to omit. |
| `start_date` | **Start Date** — `0` or `YYYY_MM` (e.g. `2026_04`). |
| `job_function_ids` | **Job Function** — list of numeric IDs from the table (e.g. `30` for IT development). |
| `domain_ids` | **Company Sector** — list of numeric IDs from the table. |
| `job_category_ids` | Optional list of IDs — not listed in `jobteaser_filters.md`; see **`docs/jobteaser_url_analysis.md`** (job category) and copy IDs from the site when needed. |

Other keys in the example file:

- **`keyword`** — default text for the keyword prompt (you can still type another keyword when you run the app).
- **`sort`** — `recency` or `relevance` (see URL analysis notes in `docs/` if needed).
- **`timeout_minutes`** — default for the “max runtime” prompt in minutes.

Easy apply is always enforced in code (`candidacy_type=INTERNAL`); you do not set that in the JSON. After editing, keep the file valid JSON (quotes, commas, `null` vs empty arrays as in the example).

## Usage

From the **project root**:

```bash
python main.py
```

Choose **APEC** or **JobTeaser**, then follow the prompts (keyword, contract or other options, max runtime in minutes).

## Project layout

| Path | Purpose |
|------|---------|
| `main.py` | Application entry point; platform menu |
| `scripts/apec.py`, `scripts/jobteaser.py` | Platform-specific automation |
| `scripts/utils.py` | Config loading, logging, Chrome driver, JobTeaser URL helpers |
| `configs/config.example.json` | Template for credentials (copy to `config.json`) |
| `configs/jobteaser.search.example.json` | Template for JobTeaser filters (copy to `jobteaser.search.json`) |
| `docs/` | Notes on URLs and filters for some platforms |

## Contributing

1. Fork the repository and create a branch for your change.
2. Keep commits focused and describe what changed.
3. Open a pull request with a short summary of behavior and any new configuration.

## Disclaimer

This software is provided for **educational and personal use**. Automating actions on third-party websites may violate their terms of service. You are responsible for how you use it; use only on accounts you own and in line with each platform’s rules.
