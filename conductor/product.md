# Initial Concept
AutoApply is a sophisticated Python-based automation framework designed to streamline and enhance the job application process on professional platforms. By combining robust browser automation with advanced AI capabilities, AutoApply allows job seekers to maintain a high volume of applications without sacrificing the quality and personalization required to stand out in a competitive market.

# Product Definition: AutoApply

## Vision
To become the ultimate personal career assistant that handles the repetitive "drudgery" of job hunting, allowing candidates to focus on interviews and career growth while the tool ensures their profile reaches the right recruiters with the most relevant information.

## Current State & Capabilities
- **APEC (Production Ready):** This is the core, stable component. It currently automates job discovery, relevance scoring, and the "Easy Apply" process using your **already-uploaded APEC resume and profile**.
- **JobTeaser (Experimental/Under Development):** This module is currently **not fully functional** and is in the active development phase. It is included for preview and research purposes.
- **AI Integration (Gemini):** Used for advanced job description analysis and relevance checking before initiating applications.

## Target Audience
- **Efficiency-Focused Job Seekers:** Candidates who need to apply to a large number of positions on APEC quickly and reliably.
- **Quality-Focused Job Seekers:** Professionals who value tailored applications and want to leverage AI to highlight their most relevant skills for every single role.
- **Platform-Specific Users:** Individuals targeting major job boards like APEC who require specialized tools to bypass detection and manage their presence effectively.

## Core Value Propositions
- **Extreme Time Savings:** Automates the end-to-end flow from job discovery to final submission on APEC, eliminating hours of manual work.
- **Robustness & Reliability:** Built with `undetected-chromedriver` and smart DOM detection to navigate complex professional platforms while remaining undetected and recovering gracefully from session errors.
- **Semantic Job Matching:** Uses Google Gemini to dynamically analyze job descriptions against user-defined keywords to ensure high-quality applications.

## Key Features (Current)
- **Multi-Keyword Search & Ranking:** Discovers and prioritizes job offers on APEC based on their relevance to a set of user-defined keywords.
- **AI-Powered Relevance Filtering:** Uses Gemini to perform a "deep check" of job titles and descriptions to ensure a professional fit.
- **Resilient Automation:** Text-based button matching and a 3-step application modal chain built for stability.
- **External Link Collection:** Automatically identifies and saves job offers requiring application on company websites, enabling manual follow-up for non-"Easy Apply" roles.
- **Local Application History:** Remembers every job successfully applied to, ensuring you never double-apply or waste time on seen URLs.
- **Intelligent Onboarding:** Automated bootstrap with dynamic runtime configuration prompting and smart login retry mechanisms.

## Roadmap & Future Enhancements
- **Custom AI CV Adaptation:** Full integration of the LaTeX CV tailoring system (currently used for JobTeaser research) into the APEC workflow.
- **JobTeaser Stabilization:** Bringing the JobTeaser module to a production-ready state with full application support.
- **Multi-Platform Expansion:** Integrating other major boards such as LinkedIn and Welcome to the Jungle.
- **Advanced Form Filling:** Moving beyond "Easy Apply" to automate complex multi-page application forms.
- **Unified Application Dashboard:** A central interface to track all submitted applications and their status.
