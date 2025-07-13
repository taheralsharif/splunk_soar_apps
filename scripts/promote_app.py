import os
import tarfile
import subprocess
import shutil
from pathlib import Path
from github import Github

REPO_NAME = os.getenv("GITHUB_REPOSITORY")
BRANCH_MAIN = "main"
BRANCH_PROD = "ready_for_prod"
EXTRACTED_DIR = "extracted_apps"
DEST_DIR = "apps"
TMP_DIR = "tmp_extract"
TMP_CACHE_DIR = "tmp_cache"

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
assert GITHUB_TOKEN, "Missing GitHub token"

g = Github(GITHUB_TOKEN)
repo = g.get_repo(REPO_NAME)

def get_new_tgz_file():
    apps_path = Path(DEST_DIR)
    if not apps_path.exists():
        print("apps/ directory does not exist.")
        return None
    for file in apps_path.iterdir():
        if file.suffix == ".tgz":
            return file
    return None

def extract_tgz(tgz_path):
    app_name = os.path.splitext(tgz_path.name)[0]
    tmp_path = Path(TMP_DIR)
    if tmp_path.exists():
        shutil.rmtree(tmp_path)
    tmp_path.mkdir(exist_ok=True)

    with tarfile.open(tgz_path, "r:gz") as tar:
        tar.extractall(tmp_path)

    return app_name, tmp_path

def find_connector_file(extracted_path):
    return next(Path(extracted_path).rglob("*connector*.py"), None)

def run_lint(file_path):
    result = subprocess.run(["flake8", file_path], capture_output=True, text=True)
    return result.stdout.strip() or "No issues found."

def commit_extracted_app_to_main(app_name, tmp_path):
    extracted_target = Path(EXTRACTED_DIR) / app_name
    if extracted_target.exists():
        shutil.rmtree(extracted_target)

    interior_dirs = list(tmp_path.iterdir())
    extracted_target.mkdir(parents=True)
    for item in interior_dirs:
        shutil.copytree(item, extracted_target / item.name)

    subprocess.run(["git", "config", "user.name", "github-actions"], check=True)
    subprocess.run(["git", "config", "user.email", "github-actions@github.com"], check=True)
    subprocess.run(["git", "add", str(extracted_target)], check=True)
    subprocess.run(["git", "commit", "-m", f"Add extracted app '{app_name}' to {EXTRACTED_DIR}/"], check=True)
    subprocess.run(["git", "push"], check=True)

def promote_to_ready_for_prod(app_name, tmp_path, cached_tgz_path):
    subprocess.run(["git", "fetch"], check=True)
    subprocess.run(["git", "checkout", BRANCH_PROD], check=True)

    app_tgz_dest = Path(DEST_DIR) / f"{app_name}.tgz"
    shutil.copy(cached_tgz_path, app_tgz_dest)

    extracted_target = Path(EXTRACTED_DIR) / app_name
    if extracted_target.exists():
        shutil.rmtree(extracted_target)

    interior_dirs = list(tmp_path.iterdir())
    extracted_target.mkdir(parents=True)
    for item in interior_dirs:
        shutil.copytree(item, extracted_target / item.name)

    subprocess.run(["git", "add", str(app_tgz_dest)], check=True)
    subprocess.run(["git", "add", str(extracted_target)], check=True)
    subprocess.run(["git", "commit", "-m", f"Promote '{app_name}' to {BRANCH_PROD}"], check=True)
    subprocess.run(["git", "push"], check=True)

def main():
    tgz_file = get_new_tgz_file()
    if not tgz_file:
        print("No .tgz file found")
        return

    # Save a cached copy of tgz file in tmp_cache/
    tmp_cache_path = Path(TMP_CACHE_DIR)
    tmp_cache_path.mkdir(exist_ok=True)
    cached_tgz_path = tmp_cache_path / tgz_file.name
    shutil.copy(tgz_file, cached_tgz_path)

    app_name, tmp_path = extract_tgz(tgz_file)
    connector_file = find_connector_file(tmp_path)

    if connector_file:
        lint_output = run_lint(str(connector_file))
        print("Lint Results:\n", lint_output)
    else:
        print("No connector file found, skipping lint.")

    commit_extracted_app_to_main(app_name, tmp_path)
    promote_to_ready_for_prod(app_name, tmp_path, cached_tgz_path)

if __name__ == "__main__":
    main()
