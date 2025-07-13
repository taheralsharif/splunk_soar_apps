import os
import subprocess
import tarfile
import glob

def run_git(cmd):
    print(f"Running git command: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)

def main():
    # Find the latest .tgz
    tgz_files = sorted(glob.glob("apps/*.tgz"), key=os.path.getmtime)
    if not tgz_files:
        raise FileNotFoundError("No .tgz files found in apps/")
    tgz_path = tgz_files[-1]

    app_name = os.path.basename(tgz_path).replace(".tgz", "").replace(" ", "_")
    extracted_path = f"extracted_apps/{app_name}"

    # Git setup
    run_git(["git", "config", "user.email", "ci@yourdomain.com"])
    run_git(["git", "config", "user.name", "CI Bot"])

    run_git(["git", "fetch", "origin"])
    run_git(["git", "checkout", "-b", f"promote_{app_name}", "origin/ready_for_prod"])

    # Extract .tgz
    os.makedirs(extracted_path, exist_ok=True)
    with tarfile.open(tgz_path, "r:gz") as tar:
        tar.extractall(extracted_path)
    print(f"Extracted {tgz_path} to {extracted_path}")

    # Lint connector
    connector_path = None
    for root, _, files in os.walk(extracted_path):
        for file in files:
            if file.endswith("_connector.py"):
                connector_path = os.path.join(root, file)
                break
        if connector_path:
            break

    if not connector_path:
        raise FileNotFoundError("No *_connector.py file found in extracted app.")

    lint_result_path = f"lint_result_{app_name}.txt"
    print(f"Linting: {connector_path}")
    with open(lint_result_path, "w") as f:
        subprocess.run(["flake8", connector_path], stdout=f, stderr=subprocess.STDOUT)

    # Stage files
    run_git(["git", "add", tgz_path])
    run_git(["git", "add", extracted_path])
    run_git(["git", "add", lint_result_path])
    run_git(["git", "commit", "-m", f"Promote {app_name} with lint results"])

    # Push
    repo_url = f"https://{os.environ['GH_TOKEN']}@github.com/{os.environ['GITHUB_REPOSITORY']}.git"
    run_git(["git", "push", repo_url, f"promote_{app_name}"])

    # Optional: create PR if gh CLI installed
    try:
        subprocess.run([
            "gh", "pr", "create",
            "--title", f"Promote {app_name} to ready_for_prod",
            "--body", f"Auto-generated PR for {app_name}",
            "--base", "ready_for_prod",
            "--head", f"promote_{app_name}"
        ], check=True)
    except FileNotFoundError:
        print("GitHub CLI (gh) not found; skipping PR creation.")

if __name__ == "__main__":
    main()
