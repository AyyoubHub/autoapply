# Product Guidelines: AutoApply

## Voice and Tone
- **Professional & Senior Engineer-like:** Interactions should be direct, professional, and clear. Avoid overly conversational or "buddy-like" language. Use technically accurate terms (e.g., "Initializing driver," "Session recovered," "Application submitted").
- **Direct and Clear:** Communicate what the tool is doing without fluff. Prioritize information that is relevant to the user's current context.

## User Experience (UX)
- **Rich Terminal Interface (TUI):** Leverage interactive elements like `questionary` for menus and prompts. Use color and formatting (within standard terminal constraints) to enhance readability and distinguish between different types of information (e.g., successes, warnings, errors).
- **Phased Progress Updates:** Provide high-level status updates at the beginning and end of major phases (Discovery, Application). Do not overwhelm the user with minute detail, but ensure they know the tool is active and making progress.
- **Intuitive Onboarding:** Maintain the current "bootstrap" approach where the tool handles its own environment setup, minimizing the manual steps required from the user.

## Communication & Logging
- **High-Level Messaging:** Focus on informing the user when a significant milestone is reached, such as starting a discovery for a new keyword or completing an application.
- **Structured Error Reporting:** When errors occur, report them clearly but concisely in the terminal, while maintaining more detailed logs in the `logs/` directory for debugging.

## Error Handling & Robustness
- **Self-Healing Strategy:** The tool should aim to be as robust as possible. If a non-fatal error occurs (e.g., a session crash, a failed button click), it should attempt to recover gracefully (e.g., by restarting the browser or skipping to the next job) rather than halting execution entirely.
- **Graceful Termination:** Ensure that user-initiated interruptions (like Ctrl-C) are handled cleanly, providing a final summary of actions taken before exiting.
- **Fail-Safe Operation:** Prioritize not breaking the user's workflow. If an advanced feature (like AI filtering) fails, fall back to a simpler, reliable method (like basic keyword matching) to ensure the core task is completed.
