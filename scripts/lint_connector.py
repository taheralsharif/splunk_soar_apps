#!/usr/bin/env python3
import sys
import glob
import os
import tarfile
import tempfile
import subprocess

def main(pattern):
    # 1. Find the newest .tgz
    tgz_files = glob.glob(pattern)
    if not tgz_files:
        print(f"No files matched '{pattern}'", file=sys.stderr)
        sys.exit(1)
    newest = max(tgz_files, key=os.path.getmtime)
    app_name = os.path.splitext(os.path.basename(newest))[0]

    print(f"APP_NAME: {app_name}")
    print(f"→ Extracting {newest}")

    # 2. Extract to tempdir
    with tempfile.TemporaryDirectory() as tmpdir:
        with tarfile.open(newest, "r:gz") as tar:
            tar.extractall(path=tmpdir)

        # 3. Locate *_connector.py
        connector = None
        for root, _, files in os.walk(tmpdir):
            for f in files:
                if f.endswith("_connector.py"):
                    connector = os.path.join(root, f)
                    break
            if connector:
                break

        if not connector:
            print("No *_connector.py found in the package!", file=sys.stderr)
            sys.exit(2)

        print(f"→ Running ruff on {connector}")

        # 4. Run ruff
        result = subprocess.run(
            ["ruff", "check", connector],
            capture_output=True,
            text=True,
        )

        # 5. Output ruff stdout/stderr
        if result.stdout:
            print(result.stdout.rstrip())
        if result.stderr:
            print(result.stderr.rstrip(), file=sys.stderr)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: lint_connector.py \"apps/*.tgz\"", file=sys.stderr)
        sys.exit(1)
    main(sys.argv[1])
