import os
import subprocess
import tarfile
import shutil
from pathlib import Path

def run_git(cmd, check=True):
    print(f"Running git command: {' '.join(cmd)}")
    subprocess.run(cmd, check=check)

def extract_tgz(tgz_path, extract_to):
    with tarfile.open(tgz_path, "r:gz") as tar:
        tar.extractall(path=extract_to)
    print(f"Extracted {tgz_path} to {extract_to}")

def lint_connector(connector_path, output_file):
    print(f"Linting: {connector_path}")
    with open(output_file, "w") as f:
        subprocess.run(["flake8", connector_path], stdout=f, stderr=subprocess.STDOUT)

def promote_app():
    apps_dir = "apps"
    extract_dir = "extracted_apps"

    latest_tgz = max(Path(apps_dir).glob("*.tgz"), key=lambda p: p.stat().st_mtime)
    app_file = latest_tgz.name
    app_name = app_file.replace(".tgz", "").replace(" ", "_")
    tgz_path = os.path.join(apps_dir, app_file)
    app_extract_path = os.path.join(extract_dir, app_name)

    extract_tgz(tgz_path, app_extract_path)

    connector_files = list(Path(app_extract_path).rglob("*_connector.py"))
    if not connector_files:
        raise FileNotFoundError("No connector file found.")

    connector_path = str(connector_files[0])
    lint_output_file = f"lint_result_{app_name}.txt"
    lint_connector(connector_path, lint_output_file)

    run_git(["git", "config", "--global", "user.email", "ci@yourdomain.com"])
    run_git(["git", "config", "--global", "user.name", "CI Bot"])
    run_git(["git", "checkout", "main"])
    run_git(["git", "pull"])

    branch_name = f"promote_{app_name}"
    run_git(["git", "checkout", "-b", branch_name])

    run_git(["git", "add", app_extract_path])
    run_git(["git", "add", lint_output_file])
    run_git(["git", "commit", "-m", f"Promote {app_name} with lint results"])

    token = os.getenv("GITHUB_TOKEN")
    repo_url = f"https://{token}@github.com/taheralsharif/splunk_soar_apps.git"
    run_git(["git", "push", repo_url, branch_name])

if __name__ == "__main__":
    promote_app()
