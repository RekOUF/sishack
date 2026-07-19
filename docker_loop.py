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
    account_set = bool(os.environ.get("SISELI_ACCOUNT"))
    password_set = bool(os.environ.get("SISELI_PASSWORD"))
    ha_url = os.environ.get("HA_URL", "<not set>")
    ha_token_set = bool(os.environ.get("HA_TOKEN"))
    print(f"[{datetime.now():%H:%M:%S}] sishack starting")
    print(f"[{datetime.now():%H:%M:%S}] interval={interval}min, account_set={account_set}, password_set={password_set}, ha_url={ha_url}, ha_token_set={ha_token_set}")
    # Run immediately on start, then every interval
    while True:
        try:
            run_once()
        except Exception as e:
            print(f"[{datetime.now():%H:%M:%S}] Error: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
        print(f"[{datetime.now():%H:%M:%S}] Sleeping {interval} minutes...")
        time.sleep(interval * 60)
