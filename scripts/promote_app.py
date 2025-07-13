import os
import tarfile
import shutil
import subprocess
import sys
from pathlib import Path


def run_git(cmd):
    print(f"Running git command: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def extract_tgz(tgz_path, extract_to):
    with tarfile.open(tgz_path, "r:gz") as tar:
        tar.extractall(path=extract_to)


def get_connector_file(app_dir):
    for root, _, files in os.walk(app_dir):
        for f in files:
            if f.endswith("_connector.py"):
                return os.path.join(root, f)
    return None


def lint_connector(connector_file):
    print(f"Linting: {connector_file}")
    result = subprocess.run(["flake8", connector_file], capture_output=True, text=True)
    if result.returncode == 0:
        print("Lint passed.")
        return "Lint passed."
    else:
        print("Lint issues found:\n", result.stdout)
        return result.stdout


def promote_app():
    apps_dir = Path("apps")
    extracted_dir = Path("extracted_apps")

    for tgz_file in apps_dir.glob("*.tgz"):
        app_name = tgz_file.stem.replace(" ", "_")
        dest_dir = extracted_dir / app_name

        if dest_dir.exists():
            print(f"Skipping {app_name}, already extracted.")
            continue

        print(f"Processing {tgz_file}...")
        tmp_extract_path = Path("tmp_extract") / app_name
        tmp_extract_path.mkdir(parents=True, exist_ok=True)

        extract_tgz(tgz_file, tmp_extract_path)

        # Move the extracted dir with correct naming convention
        subfolders = list(tmp_extract_path.iterdir())
        if len(subfolders) != 1:
            print(f"Unexpected structure in {tgz_file}, skipping.")
            continue

        correct_name_dir = dest_dir / subfolders[0].name
        correct_name_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(subfolders[0]), correct_name_dir)

        # Git config
        run_git(["git", "config", "--global", "user.email", "ci@yourdomain.com"])
        run_git(["git", "config", "--global", "user.name", "CI Bot"])

        # Add extracted files to main
        run_git(["git", "add", str(dest_dir)])
        run_git(["git", "commit", "-m", f"Add extracted app '{app_name}' to extracted_apps/"])

        # Lint
        connector_file = get_connector_file(dest_dir)
        if connector_file:
            lint_results = lint_connector(connector_file)
            with open(f"lint_result_{app_name}.txt", "w") as f:
                f.write(lint_results)
            run_git(["git", "add", f"lint_result_{app_name}.txt"])
            run_git(["git", "commit", "-m", f"Add lint results for {app_name}"])
        else:
            print(f"No connector file found in {app_name}.")

        # Create PR from main to ready_for_prod using GitHub CLI
        subprocess.run(["gh", "pr", "create", "--base", "ready_for_prod", "--head", "main", 
                        "--title", f"Promote {app_name} to ready_for_prod", 
                        "--body", f"This PR promotes {app_name} to ready_for_prod with lint results."], check=True)


if __name__ == "__main__":
    promote_app()
