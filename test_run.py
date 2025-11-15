"""
# * Simple smoke test: Snapshot → Color → Restore workflow.
"""

import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

# * Resolve tools directory
PROJECT_ROOT = Path(__file__).resolve().parent
TOOLS_DIR = PROJECT_ROOT / "tools"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# * Load configuration from .env
ENV_PATH = PROJECT_ROOT / ".env"
load_dotenv(ENV_PATH)


def run_subprocess(command: list[str]) -> str:
    print(f"→ Running: {' '.join(command)}")
    result = subprocess.run(command, env=os.environ.copy(), check=False, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed with exit code {result.returncode}: {' '.join(command)}")
    return result.stdout


def main() -> None:
    input_path = PROJECT_ROOT / "input.json"
    if not input_path.exists():
        raise FileNotFoundError(f"No input file found at {input_path}")

    python_exec = sys.executable
    snapshot_script = str(TOOLS_DIR / "snapshot_input_colors.py")
    color_script = str(TOOLS_DIR / "function_to_color_things.py")
    restore_script = str(TOOLS_DIR / "restore_input_colors.py")

    print("# * Capturing current colors for each cell range.")
    snapshot_output = run_subprocess([python_exec, snapshot_script, str(input_path)])

    print("# * Applying test colors from input JSON.")
    run_subprocess([python_exec, color_script, str(input_path)])

    # * Extract snapshot ID from output (format: "Snapshot batch ID: <uuid>")
    snapshot_id = None
    input("enter to continue")
    for line in snapshot_output.split("\n"):
        if "Snapshot batch ID:" in line:
            snapshot_id = line.split("Snapshot batch ID:")[-1].strip()
            break
    
    if not snapshot_id:
        raise ValueError("Could not extract snapshot ID from snapshot tool output.")
    
    print(f"# * Restoring colors from snapshot {snapshot_id}.")
    run_subprocess([python_exec, restore_script, snapshot_id, str(input_path)])

    print("✔ Test run completed successfully.")


if __name__ == "__main__":
    main()


