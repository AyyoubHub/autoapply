import sys
import os

# Ensure the scripts/ directory is on the path regardless of where the
# script is launched from (fixes ModuleNotFoundError when running via
# `python scripts/launcher.py` from the project root).
sys.path.insert(0, os.path.dirname(__file__))

import questionary

# Set up logging once here so it is active for every platform's run()
from utils import setup_logging
setup_logging()

# Local imports
from hellowork import run as run_hellowork
from apec import run as run_apec
from jobteaser import run as run_jobteaser

# Platform menu
platforms = {
    "HelloWork": run_hellowork,
    "APEC": run_apec,
    "JobTeaser": run_jobteaser,
}

selected_run = questionary.select(
    "Choose a job platform to launch:",
    choices=[
        questionary.Choice(title=name, value=fn)
        for name, fn in platforms.items()
    ],
).ask()

selected_run()