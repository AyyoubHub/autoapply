# Tech Stack: AutoApply

## Core Languages & Runtimes
- **Python (>= 3.9):** The primary language for all automation scripts and the main application entry point.

## Browser Automation & Web Scraping
- **Selenium (>= 4.0):** Used for low-level browser interaction, page navigation, and element detection.
- **undetected-chromedriver:** A specialized ChromeDriver wrapper that bypasses most anti-bot detection systems (e.g., Cloudflare, Akamai).
- **Ungoogled Chromium:** The preferred browser engine for its clean profile and telemetry-free execution.

## Artificial Intelligence & LLMs
- **Google Gemini (via `google-genai`):** Used for advanced job description analysis and relevance checking.
- **Gemini-3.1-flash-lite:** The primary model for fast, low-latency semantic filtering.
- **Gemini-3.1-flash:** (Research phase) Used for complex LaTeX CV adaptation tasks.

## CLI & User Interface
- **questionary:** Provides the rich, interactive terminal interface for menus and user input.
- **Standard Python Logging:** Used for structured runtime logs (timestamped) in the `logs/` directory.

## Document Processing
- **Tectonic (optional):** A specialized LaTeX engine used for high-fidelity PDF compilation when generating tailored CVs.

## Environment & Configuration
- **.env:** Stores sensitive API keys (e.g., `GEMINI_API`).
- **configs/config.json:** Stores user credentials and platform-specific settings.
- **JSON (Local Scratch):** Used for local history and persistence (e.g., `apec_applied.json`).
