import os
import sys

# Resolve platform modules from scripts/ when running as `python main.py` from repo root.
_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import questionary

# Set up logging once here so it is active for every platform's run()
from utils import setup_logging

setup_logging()

from apec import run as run_apec
from jobteaser import run as run_jobteaser

platforms = {
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
