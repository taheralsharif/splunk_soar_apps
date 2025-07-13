import os
import tarfile
import tempfile
import shutil
import subprocess
import re

def run_git(cmd, check=True):
    print(f"Running git command: {' '.join(cmd)}")
    subprocess.run(cmd, check=check)

def extract_tgz(tgz_path, extract_to):
    with tarfile.open(tgz_path, "r:gz") as tar:
        tar.extractall(path=extract_to)

def lint_python_file(file_path):
    print(f"Linting: {file_path}")
    result = subprocess.run(["flake8", file_path], capture_output=True, text=True)
    if result.returncode != 0:
        print("Lint issues found:\n", result.stdout)
        return result.stdout
    print("No lint issues found.")
    return None

def promote_app():
    apps_dir = "apps"
    extracted_dir = "extracted_apps"

    for app_file in os.listdir(apps_dir):
        if not app_file.endswith(".tgz"):
            continue

        app_name = app_file.replace(".tgz", "")
        safe_app_name = re.sub(r"[^\w\-]", "_", app_name)
        branch_name = f"promote/{safe_app_name}"

        tgz_path = os.path.join(apps_dir, app_file)
        temp_dir = tempfile.mkdtemp()
        extract_path = os.path.join(temp_dir, app_name)

        os.makedirs(extract_path, exist_ok=True)
        extract_tgz(tgz_path, extract_path)

        # Locate connector.py
        connector_path = None
        for root, _, files in os.walk(extract_path):
            for file in files:
                if file.endswith("_connector.py"):
                    connector_path = os.path.join(root, file)
                    break

        # Git setup
        run_git(["git", "config", "--global", "user.email", "ci@yourdomain.com"])
        run_git(["git", "config", "--global", "user.name", "CI Bot"])
        run_git(["git", "checkout", "main"])
        run_git(["git", "checkout", "-b", branch_name])

        # Copy app to extracted dir
        extracted_app_dest = os.path.join(extracted_dir, app_name)
        if os.path.exists(extracted_app_dest):
            shutil.rmtree(extracted_app_dest)
        shutil.copytree(os.path.join(extract_path), extracted_app_dest)

        shutil.copy(tgz_path, os.path.join("apps", app_file))
        run_git(["git", "add", os.path.join(extracted_dir, app_name)])
        run_git(["git", "add", os.path.join("apps", app_file)])
        run_git(["git", "commit", "-m", f"Add extracted app '{app_name}' to extracted_apps/"])

        # Linting and adding results
        if connector_path:
            lint_results = lint_python_file(connector_path)
            if lint_results:
                lint_result_file = f"lint_result_{safe_app_name}.txt"
                with open(lint_result_file, "w") as f:
                    f.write(lint_results)
                run_git(["git", "add", lint_result_file])
                run_git(["git", "commit", "-m", f"Add lint results for {app_name}"])

        # Create PR
        subprocess.run([
            "gh", "pr", "create",
            "--base", "ready_for_prod",
            "--head", branch_name,
            "--title", f"Promote {app_name} to ready_for_prod",
            "--body", f"This PR promotes {app_name} to ready_for_prod with lint results."
        ], check=True)

        shutil.rmtree(temp_dir)

if __name__ == "__main__":
    promote_app()
