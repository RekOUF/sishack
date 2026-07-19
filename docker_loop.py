#!/usr/bin/env python3
"""Docker loop: run Siseli scraper + HA push every 5 minutes."""

import os
import subprocess
import sys
import time
from datetime import datetime

PUSH_SCRIPT = os.path.join(os.path.dirname(__file__), "siseli_ha_push.py")


def run_once():
    print(f"[{datetime.now():%H:%M:%S}] Running Siseli HA push...")
    result = subprocess.run(
        [sys.executable, PUSH_SCRIPT],
        capture_output=True,
        text=True,
        timeout=120,
    )
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode


if __name__ == "__main__":
    interval = int(os.environ.get("INTERVAL_MINUTES", "5"))
    # Run immediately on start, then every interval
    while True:
        try:
            run_once()
        except Exception as e:
            print(f"[{datetime.now():%H:%M:%S}] Error: {e}", file=sys.stderr)
        print(f"[{datetime.now():%H:%M:%S}] Sleeping {interval} minutes...")
        time.sleep(interval * 60)
