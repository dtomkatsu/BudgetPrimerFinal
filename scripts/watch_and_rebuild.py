#!/usr/bin/env python3
"""
Watch key files and regenerate departmental reports on change, then run validations.

Usage:
  python scripts/watch_and_rebuild.py

Requires: watchdog (pip install watchdog)
"""
from __future__ import annotations
import subprocess
import sys
import time
from pathlib import Path

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
except ImportError:
    print("Missing dependency 'watchdog'. Install via: pip install watchdog")
    sys.exit(1)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = PROJECT_ROOT / "data/processed/budget_allocations_fy2026_post_veto.csv"
TARGET_SCRIPT = PROJECT_ROOT / "scripts/generate_departmental_reports.py"
VALIDATOR = PROJECT_ROOT / "scripts/validate_reports.py"
WATCH_PATHS = [
    PROJECT_ROOT / "scripts/generate_departmental_reports.py",
    PROJECT_ROOT / "budgetprimer/visualization",
]
DEBOUNCE_SEC = 0.5


def run(cmd: list[str]) -> int:
    print("$", " ".join(cmd))
    proc = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    return proc.returncode


def rebuild() -> None:
    print("=== Rebuilding departmental reports ===")
    rc = run([sys.executable, str(TARGET_SCRIPT), str(DATA_FILE)])
    if rc != 0:
        print("Build failed; skipping validation.")
        return
    print("=== Running validations ===")
    rc = run([sys.executable, str(VALIDATOR)])
    if rc != 0:
        print("Validations failed.")
    else:
        print("Build + validations succeeded.")


class ChangeHandler(FileSystemEventHandler):
    def __init__(self):
        super().__init__()
        self._last_time = 0.0

    def on_any_event(self, event):
        # Ignore directories
        if event.is_directory:
            return
        # Only watch .py files
        if not event.src_path.endswith('.py'):
            return
        now = time.time()
        if now - self._last_time < DEBOUNCE_SEC:
            return
        self._last_time = now
        print(f"Change detected: {event.src_path}")
        rebuild()


def main() -> None:
    print("Watching for changes...")
    # Initial build
    rebuild()

    observer = Observer()
    handler = ChangeHandler()
    for path in WATCH_PATHS:
        observer.schedule(handler, str(path), recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()
