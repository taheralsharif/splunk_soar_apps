#!/usr/bin/env python3
import argparse
import glob
import os
import subprocess
import sys
import tarfile
import tempfile

def lint_tgz(pattern):
    matches = glob.glob(pattern, recursive=True)
    if not matches:
        print(f"No .tgz files matched '{pattern}'")
        return False

    had_errors = False
    for tgz in matches:
        app_name = os.path.splitext(os.path.basename(tgz))[0]
        print(f"APP_NAME: {app_name}")
        workdir = tempfile.mkdtemp(prefix=f"{app_name}_")
        print(f"→ Extracting {tgz}")
        try:
            with tarfile.open(tgz, "r:gz") as tar:
                tar.extractall(path=workdir)
        except Exception as e:
            print(f"Error extracting {tgz}: {e}")
            had_errors = True
            continue

        # find the first *connector.py
        connector = None
        for root, _, files in os.walk(workdir):
            for fn in files:
                if fn.endswith("connector.py"):
                    connector = os.path.join(root, fn)
                    break
            if connector:
                break

        if not connector:
            print(f"No connector.py found in {tgz}")
            had_errors = True
            continue

        print(f"→ Running flake8 on {connector}")
        proc = subprocess.run(
            ["flake8", connector],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if proc.stdout:
            print(proc.stdout, end="")
        if proc.stderr:
            print(proc.stderr, end="", file=sys.stderr)
        if proc.returncode != 0:
            had_errors = True

    return had_errors

def main():
    parser = argparse.ArgumentParser(
        description="Extract each .tgz, find its connector, run flake8."
    )
    parser.add_argument(
        "patterns", nargs="+",
        help="Glob patterns (e.g. 'apps/**/*.tgz')"
    )
    args = parser.parse_args()

    overall_errors = False
    for p in args.patterns:
        if lint_tgz(p):
            overall_errors = True

    sys.exit(1 if overall_errors else 0)

if __name__ == "__main__":
    main()
