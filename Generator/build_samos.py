"""Build every SamOS output with one command."""

import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "Generator"
PUBLIC = ROOT / "public"


def run(script: str, *arguments: str) -> None:
    subprocess.run([sys.executable, str(GENERATOR / script), *arguments], check=True)


def main() -> None:
    run("validate_config.py")
    run("planner.py")
    run("reminders.py")
    run("calendar.py")
    run("dashboard.py")
    PUBLIC.mkdir(exist_ok=True)
    shutil.copyfile(ROOT / "Dashboard" / "Reminders.ics", PUBLIC / "Reminders.ics")
    print("SamOS build complete.")


if __name__ == "__main__":
    main()
