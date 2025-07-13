#!/usr/bin/env python3
import glob
import os
import sys

def main():
    if len(sys.argv) != 2:
        print("Usage: get_new_app.py <glob_pattern>", file=sys.stderr)
        sys.exit(1)

    pattern = sys.argv[1]
    # find all matching tgz files, recursively
    files = glob.glob(pattern, recursive=True)
    if not files:
        # nothing to do
        sys.exit(0)

    # pick the file with the latest modification time
    latest = max(files, key=os.path.getmtime)
    # strip path and .tgz extension
    name = os.path.splitext(os.path.basename(latest))[0]
    print(name)

if __name__ == "__main__":
    main()
