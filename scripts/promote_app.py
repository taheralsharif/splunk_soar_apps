# promote_app.py
import os
import tarfile
import shutil
import subprocess
from pathlib import Path
import time
import sys

EXTRACTED_DIR = "extracted_apps"
APPS_DIR = "apps"


def run_git(cmd, check=True):
    print(f"Running git command: {' '.join(cmd)}")
    subprocess.run(cmd, check=check)


def extract_tgz(tgz_path, app_name):
    dest_path = os.path.join(EXTRACTED_DIR, app_name)
    os.makedirs(dest_path, exist_ok=True)
    with tarfile.open(tgz_path, "r:gz") as tar:
        tar.extractall(path=dest_path)
    print(f"Extracted {tgz_path} to {dest_path}")
    return dest_path


def lint_connector(app_path):
    lint_output = []
    for root, dirs, files in os.walk(app_path):
        for f in files:
            if f.endswith("_connector.py"):
                connector_path = os.path.join(root, f)
                print(f"Linting: {connector_path}")
                result = subprocess.run(["flake8", connector_path], capture_output=True, text=True)
                lint_output.append(result.stdout)
    return "\n".join(lint_output)


def get_latest_tgz():
    tgz_files = [os.path.join(APPS_DIR, f) for f in os.listdir(APPS_DIR) if f.endswith(".tgz")]
    if not tgz_files:
        raise FileNotFoundError("No .tgz files found in apps/ directory")
    return max(tgz_files, key=os.path.getmtime)


def promote_app():
    tgz_path = get_latest_tgz()
    app_file = os.path.basename(tgz_path)
    app_name = Path(app_file).stem.replace(" ", "_")

    # Extract and lint
    extracted_path = extract_tgz(tgz_path, app_name)
    lint_result = lint_connector(extracted_path)
    lint_file = f"lint_result_{app_name}.txt"
    with open(lint_file, "w") as f:
        f.write(lint_result if lint_result else "No lint issues found.")

    # Git operations
    run_git(["git", "config", "--global", "user.email", "ci@yourdomain.com"])
    run_git(["git", "config", "--global", "user.name", "CI Bot"])

    run_git(["git", "checkout", "main"])
    run_git(["git", "checkout", "-b", f"promote_{app_name}"])

    run_git(["git", "add", extracted_path])
    run_git(["git", "add", lint_file])
    run_git(["git", "commit", "-m", f"Promote {app_name} with lint results"])
    run_git(["git", "push", "origin", f"promote_{app_name}"])

    subprocess.run([
        "gh", "pr", "create",
        "--base", "ready_for_prod",
        "--head", f"promote_{app_name}",
        "--title", f"Promote {app_name} to ready_for_prod",
        "--body", f"Linting results are in {lint_file}."
    ], check=True)


if __name__ == "__main__":
    promote_app()
