import os
import tarfile
import shutil
import subprocess

APPS_DIR = "apps"
EXTRACTED_DIR = "extracted_apps"

def run_git(cmd, check=True):
    print("Running git command:", " ".join(cmd))
    subprocess.run(cmd, check=check)

def find_latest_tgz():
    tgzs = [f for f in os.listdir(APPS_DIR) if f.endswith(".tgz")]
    if not tgzs:
        raise FileNotFoundError("No .tgz file found in apps/")
    tgzs.sort(key=lambda f: os.path.getmtime(os.path.join(APPS_DIR, f)), reverse=True)
    return tgzs[0]

def extract_app(tgz_file):
    app_name = tgz_file.replace(".tgz", "").replace(" ", "_")
    extract_path = os.path.join(EXTRACTED_DIR, app_name)
    os.makedirs(extract_path, exist_ok=True)
    with tarfile.open(os.path.join(APPS_DIR, tgz_file), "r:gz") as tar:
        tar.extractall(path=extract_path)
    print(f"Extracted {tgz_file} to {extract_path}")
    return app_name, extract_path

def find_connector_py(app_path):
    for root, dirs, files in os.walk(app_path):
        for file in files:
            if file.endswith("_connector.py"):
                return os.path.join(root, file)
    raise FileNotFoundError("No *_connector.py file found.")

def lint_file(file_path, app_name):
    print(f"Linting: {file_path}")
    result = subprocess.run(["flake8", file_path], capture_output=True, text=True)
    lint_output = result.stdout.strip()
    if lint_output:
        print("Lint issues found:\n", lint_output)
    with open(f"lint_result_{app_name}.txt", "w") as f:
        f.write(lint_output or "No linting issues found.")
    return f"lint_result_{app_name}.txt"

def promote_app():
    tgz = find_latest_tgz()
    app_name, extracted_path = extract_app(tgz)
    connector_py = find_connector_py(extracted_path)
    lint_result_file = lint_file(connector_py, app_name)

    # Git config
    run_git(["git", "config", "--global", "user.email", "ci@yourdomain.com"])
    run_git(["git", "config", "--global", "user.name", "CI Bot"])

    # Create branch
    run_git(["git", "checkout", "main"])
    branch_name = f"promote_{app_name}"
    run_git(["git", "checkout", "-b", branch_name])

    # Add and commit extracted files + lint
    run_git(["git", "add", extracted_path])
    run_git(["git", "add", lint_result_file])
    run_git(["git", "commit", "-m", f"Promote {app_name} with lint results"])

    # Push with token
    repo_url = f"https://{os.environ['ACTIONS_PAT']}@github.com/taheralsharif/splunk_soar_apps.git"
    run_git(["git", "push", repo_url, branch_name])

    # Create PR
    subprocess.run([
        "gh", "pr", "create",
        "--base", "ready_for_prod",
        "--head", branch_name,
        "--title", f"Promote {app_name} to ready_for_prod",
        "--body", f"This PR promotes {app_name} to ready_for_prod with lint results."
    ], check=True)

if __name__ == "__main__":
    promote_app()
