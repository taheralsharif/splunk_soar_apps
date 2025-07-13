#!/usr/bin/env python3
import sys
import glob
import os
import tarfile
import tempfile
import subprocess

def main(pattern):
    # 1) find all matching .tgz, pick the newest
    tgzs = glob.glob(pattern)
    if not tgzs:
        print("No .tgz files found matching", pattern)
        sys.exit(1)
    latest = max(tgzs, key=lambda p: os.path.getmtime(p))
    app = os.path.basename(latest)[:-4]
    print(f"APP_NAME: {app}")

    # 2) extract into temp dir
    with tempfile.TemporaryDirectory() as tmp:
        with tarfile.open(latest, 'r:gz') as tar:
            tar.extractall(tmp)

        # 3) locate the first connector .py
        connector = None
        for root, _, files in os.walk(tmp):
            for f in files:
                if f.endswith("_connector.py"):
                    connector = os.path.join(root, f)
                    break
            if connector:
                break

        if not connector:
            print("No connector .py file found in", latest)
            sys.exit(0)

        print("→ Running ruff on", connector)
        # 4) run ruff, capture output (but never fail)
        result = subprocess.run(
            ["ruff", connector],
            capture_output=True,
            text=True
        )
        # print any findings
        if result.stdout:
            print(result.stdout.strip())
        if result.stderr:
            print(result.stderr.strip())

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: scripts/lint_connector.py '<glob-pattern>'")
        sys.exit(1)
    main(sys.argv[1])
