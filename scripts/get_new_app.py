#!/usr/bin/env python3
import sys
import glob
import os

# usage: get_new_app.py "<glob-pattern>"
pattern = sys.argv[1] if len(sys.argv) > 1 else "apps/**/*.tgz"

# find all matching .tgz (recursively)
matches = sorted(glob.glob(pattern, recursive=True))
if not matches:
    print(f"ERROR: no files match {pattern}", file=sys.stderr)
    sys.exit(1)

# take the last one
latest = matches[-1]
app_name = os.path.basename(latest)[:-4]  # strip “.tgz”

# emit just the app name
print(app_name)
