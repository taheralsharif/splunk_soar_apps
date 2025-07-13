import os
import shutil
import tarfile
import subprocess
import re
import uuid

EXTRACTED_DIR = "extracted_apps"
TGZ_DIR = "apps"

def run_git(cmd, check=True):
    print(f"Running git command: {' '.join(cmd)}")
    subprocess.run(cmd, check=check)

def extract_app(tgz_path, target_dir):
    with tarfile.open(tgz_path, "r:gz") as tar:
        tar.extractall(path=target_dir)

def promote_to_ready_for_prod(tgz_file):
    if not os.path.exists(TGZ_DIR):
        raise FileNotFoundError(f"Directory '{TGZ_DIR}' not found")

    tgz_path = os.path.join(TGZ_DIR, tgz_file)
    if not os.path.exists(tgz_path):
        raise FileNotFoundError(f".tgz file not found at path: {tgz_path}")

    app_name_raw = os.path.splitext(tgz_file)[0]
    app_name = re.sub(r"\W+", "_", app_name_raw)
    branch_name = f"promote/{app_name}_{uuid.uuid4().hex[:6]}"

    # Configure Git identity
    run_git(["git", "config", "--global", "user.email", "ci@yourdomain.com"])
    run_git(["git", "config", "--global", "user.name", "CI Bot"])

    # Create new branch
    run_git(["git", "checkout", "-b", branch_name])

    # Copy to /apps/APP/APP.tgz
    app_dir = os.path.join(TGZ_DIR, app_name)
    os.makedirs(app_dir, exist_ok=True)
    shutil.copy(tgz_path, os.path.join(app_dir, f"{app_name}.tgz"))

    # Extract to extracted_apps/APP/phAPP
    extracted_app_dir = os.path.join(EXTRACTED_DIR, app_name, f"ph{app_name}")
    os.makedirs(os.path.dirname(extracted_app_dir), exist_ok=True)
    extract_app(tgz_path, extracted_app_dir)

    # Add and commit
    run_git(["git", "add", extracted_app_dir])
    run_git(["git", "add", app_dir])
    run_git(["git", "commit", "-m", f"Add extracted app '{app_name_raw}' to extracted_apps/"])
    run_git(["git", "push", "-u", "origin", branch_name])

    return app_name_raw, branch_name

def create_pr(app_name_raw, branch_name):
    # Use GitHub CLI to create PR
    subprocess.run([
        "gh", "pr", "create",
        "--title", f"Promote SOAR App: {app_name_raw}",
        "--body", f"Auto-promotion of {app_name_raw} into extracted_apps.",
        "--head", branch_name,
        "--base", "main"
    ], check=True)

def main():
    tgz_files = [f for f in os.listdir(TGZ_DIR) if f.endswith(".tgz") and os.path.isfile(os.path.join(TGZ_DIR, f))]
    if not tgz_files:
        raise FileNotFoundError("No .tgz file found in apps/")

    for tgz_file in tgz_files:
        app_name_raw, branch_name = promote_to_ready_for_prod(tgz_file)
        create_pr(app_name_raw, branch_name)

if __name__ == "__main__":
    main()
