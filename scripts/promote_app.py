import os
import shutil
import tarfile
import subprocess
import re

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

    # Copy .tgz file into apps/{app_name}/app_name.tgz
    app_dir = os.path.join(TGZ_DIR, app_name)
    os.makedirs(app_dir, exist_ok=True)
    shutil.copy(tgz_path, os.path.join(app_dir, f"{app_name}.tgz"))

    # Extract .tgz into extracted_apps/{app_name}/ph{app_name}
    extracted_app_dir = os.path.join(EXTRACTED_DIR, app_name, f"ph{app_name}")
    os.makedirs(os.path.dirname(extracted_app_dir), exist_ok=True)
    extract_app(tgz_path, extracted_app_dir)

    # Set Git identity for CI/CD if not set
    run_git(["git", "config", "--global", "user.email", "ci@yourdomain.com"])
    run_git(["git", "config", "--global", "user.name", "CI Bot"])

    # Git add and commit
    run_git(["git", "add", extracted_app_dir])
    run_git(["git", "add", app_dir])
    run_git(["git", "commit", "-m", f"Add extracted app '{app_name_raw}' to extracted_apps/"])

    return app_name

def main():
    # Process all .tgz files in the apps directory root
    tgz_files = [f for f in os.listdir(TGZ_DIR) if f.endswith(".tgz") and os.path.isfile(os.path.join(TGZ_DIR, f))]
    if not tgz_files:
        raise FileNotFoundError("No .tgz file found")

    for tgz_file in tgz_files:
        promote_to_ready_for_prod(tgz_file)

if __name__ == "__main__":
    main()
