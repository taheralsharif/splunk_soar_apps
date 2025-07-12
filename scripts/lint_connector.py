#!/usr/bin/env python3
import glob
import os
import sys
import tarfile
import subprocess

def extract_tgz(tgz_path, extract_dir):
    os.makedirs(extract_dir, exist_ok=True)
    with tarfile.open(tgz_path, 'r:gz') as tar:
        tar.extractall(path=extract_dir)
    return extract_dir

def find_connector_py(root_dir):
    for dirpath, _, files in os.walk(root_dir):
        for f in files:
            if f.endswith('_connector.py'):
                return os.path.join(dirpath, f)
    return None

def lint_connector(tgz_pattern):
    matches = glob.glob(tgz_pattern)
    if not matches:
        print(f"No .tgz files matched '{tgz_pattern}'", file=sys.stderr)
        sys.exit(1)

    # if multiple, lint each
    for tgz in matches:
        print(f"→ Extracting {tgz}")
        extract_dir = os.path.join('/tmp', os.path.basename(tgz).replace('.tgz',''))
        extract_tgz(tgz, extract_dir)

        connector = find_connector_py(extract_dir)
        if not connector:
            print(f"ERROR: No connector file found in {tgz}", file=sys.stderr)
            sys.exit(1)

        print(f"→ Running flake8 on {connector}")
        proc = subprocess.run(['flake8', connector], capture_output=True, text=True)
        if proc.returncode != 0:
            print(proc.stdout, file=sys.stderr)
            sys.exit(proc.returncode)
        print("✔ Lint passed!")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: lint_connector.py <path/to/apps/*.tgz>", file=sys.stderr)
        sys.exit(1)
    pattern = sys.argv[1]
    lint_connector(pattern)
