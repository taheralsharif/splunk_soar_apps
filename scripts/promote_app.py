import os
import tarfile
import subprocess
import shutil
import glob
import re
from pathlib import Path
from github import Github
from github import InputGitAuthor

REPO_NAME = os.getenv("GITHUB_REPOSITORY")
BRANCH_MAIN = "main"
BRANCH_PROD = "ready_for_prod"
APPS_DIR = "apps"
EXTRACTED_DIR = "extracted_apps"
DEST_DIR = "apps"
TMP_DIR = "tmp_extract"

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
assert GITHUB_TOKEN, "Missing GitHub token"

g = Github(GITHUB_TOKEN)
repo = g.get_repo(REPO_NAME)

# List the first .tgz file in apps/
def get_new_tgz_file():
    for file in os.listdir(APPS_DIR):
        if file.endswith(".tgz"):
            return os.path.join(APPS_DIR, file)
    return None

# Extract .tgz into tmp dir and then copy to extracted_apps/ in main

def extract_tgz(tgz_path):
    app_name = os.path.splitext(os.path.basename(tgz_path))[0]
    tmp_path = Path(TMP_DIR)
    tmp_path.mkdir(exist_ok=True)

    with tarfile.open(tgz_path, "r:gz") as tar:
        tar.extractall(tmp_path)

    return app_name, tmp_path

# Find first connector .py file

def find_connector_file(extracted_path):
    return next(Path(extracted_path).rglob("*connector*.py"), None)

# Run flake8 linting and return output as string

def run_lint(file_path):
    result = subprocess.run(["flake8", file_path], capture_output=True, text=True)
    return result.stdout.strip() or "No issues found."

# Commit extracted app to extracted_apps/ in main branch

def commit_extracted_app(app_name, tmp_path):
    target_path = Path(EXTRACTED_DIR) / app_name
    if target_path.exists():
        shutil.rmtree(target_path)
    shutil.copytree(tmp_path, target_path)

    subprocess.run(["git", "config", "user.name", "github-actions"], check=True)
    subprocess.run(["git", "config", "user.email", "github-actions@github.com"], check=True)
    subprocess.run(["git", "add", EXTRACTED_DIR], check=True)
    subprocess.run(["git", "commit", "-m", f"Add extracted app {app_name} to {EXTRACTED_DIR}/"], check=True)
    subprocess.run(["git", "pull", "--rebase", "origin", BRANCH_MAIN], check=True)
    subprocess.run(["git", "push", "origin", BRANCH_MAIN], check=True)


# Create PR to ready_for_prod with app under apps/AppName/

def create_pr(app_name, tmp_path, lint_results):
    new_branch = f"promote/{app_name.replace(' ', '-').lower()}"

    base = repo.get_branch(BRANCH_PROD)
    repo.create_git_ref(ref=f"refs/heads/{new_branch}", sha=base.commit.sha)

    dest_path = Path(DEST_DIR) / app_name
    if dest_path.exists():
        shutil.rmtree(dest_path)
    shutil.copytree(tmp_path, dest_path)

    subprocess.run(["git", "fetch"], check=True)
    subprocess.run(["git", "checkout", new_branch], check=True)
    subprocess.run(["git", "add", str(dest_path)], check=True)
    subprocess.run(["git", "commit", "-m", f"Promote {app_name} to {DEST_DIR}/"], check=True)
    subprocess.run(["git", "push", "--set-upstream", "origin", new_branch], check=True)

    title = f"Promote: {app_name} to ready_for_prod"
    body = f"This PR promotes the {app_name} app to the production branch.\n\n**Lint Results** (`*connector*.py`):\n```\n{lint_results}\n```"
    repo.create_pull(title=title, body=body, head=new_branch, base=BRANCH_PROD)

# Main execution

def main():
    tgz_file = get_new_tgz_file()
    if not tgz_file:
        print("No .tgz file found in apps/")
        return

    app_name, tmp_path = extract_tgz(tgz_file)
    connector_file = find_connector_file(tmp_path)

    if not connector_file:
        print("No connector .py file found.")
        return

    lint_output = run_lint(str(connector_file))
    commit_extracted_app(app_name, tmp_path)
    create_pr(app_name, tmp_path, lint_output)

if __name__ == "__main__":
    main()
