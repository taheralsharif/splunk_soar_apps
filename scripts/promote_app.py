import os
import subprocess
import sys
import tarfile
from pathlib import Path
import shutil

APP_DIR = "apps"
EXTRACTED_DIR = "extracted_apps"

def run_git(cmd, check=True):
    print(f"Running git command: {' '.join(cmd)}")
    subprocess.run(cmd, check=check)

def extract_tgz(tgz_path, output_dir):
    with tarfile.open(tgz_path, "r:gz") as tar:
        tar.extractall(output_dir)

def lint_python_file(py_file):
    print(f"Linting: {py_file}")
    result = subprocess.run(["flake8", py_file], capture_output=True, text=True)
    return result.stdout.strip()

def promote_app():
    for file in os.listdir(APP_DIR):
        if file.endswith(".tgz"):
            app_name = file.replace(".tgz", "")
            tgz_path = os.path.join(APP_DIR, file)

            print(f"Processing {tgz_path}...")

            extracted_path = os.path.join(EXTRACTED_DIR, app_name)
            if os.path.exists(extracted_path):
                shutil.rmtree(extracted_path)

            os.makedirs(extracted_path, exist_ok=True)
            extract_tgz(tgz_path, extracted_path)

            # Find connector file
            connector_path = None
            for root, _, files in os.walk(extracted_path):
                for f in files:
                    if f.endswith("_connector.py"):
                        connector_path = os.path.join(root, f)
                        break

            if not connector_path:
                print(f"No connector file found in {app_name}. Skipping.")
                continue

            lint_result = lint_python_file(connector_path)
            lint_output_file = f"lint_result_{app_name}.txt"
            with open(lint_output_file, "w") as f:
                f.write(lint_result + "\n")

            # Set up git identity
            run_git(["git", "config", "--global", "user.email", "ci@yourdomain.com"])
            run_git(["git", "config", "--global", "user.name", "CI Bot"])

            # Create promotion branch
            branch_name = f"promote/{app_name}"
            run_git(["git", "checkout", "-b", branch_name])

            run_git(["git", "add", extracted_path])
            run_git(["git", "add", lint_output_file])
            run_git(["git", "commit", "-m", f"Promote {app_name} with lint results"])
            run_git(["git", "push", "-u", "origin", branch_name])

            # Open PR into ready_for_prod
            subprocess.run([
                "gh", "pr", "create",
                "--base", "ready_for_prod",
                "--head", branch_name,
                "--title", f"Promote {app_name} to ready_for_prod",
                "--body", f"This PR promotes {app_name} to ready_for_prod with lint results."
            ], check=True)

            print(f"✅ Created PR for {app_name}")

if __name__ == "__main__":
    promote_app()
