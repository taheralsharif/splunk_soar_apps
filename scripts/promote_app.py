import os
import shutil
import tarfile
import subprocess
import re
import sys
import tempfile


def extract_app(tgz_path, extract_to):
    with tarfile.open(tgz_path, "r:gz") as tar:
        tar.extractall(path=extract_to)


def run_git(cmd, check=True):
    print(f"Running git command: {' '.join(cmd)}")
    subprocess.run(cmd, check=check)


def run_lint(app_path):
    try:
        output = subprocess.check_output(["flake8", app_path], text=True)
        return output.strip()
    except subprocess.CalledProcessError as e:
        return e.output.strip()


def promote_to_ready_for_prod(app_name):
    tgz_file = f"apps/{app_name}.tgz"
    if not os.path.exists(tgz_file):
        print(f"❌ Error: {tgz_file} not found.")
        sys.exit(1)

    # Extract and commit to `main`
    with tempfile.TemporaryDirectory() as tmp_extract:
        extract_app(tgz_file, tmp_extract)

        app_dirname = os.path.join(tmp_extract, f"ph{app_name}")
        dest_dir = os.path.join("extracted_apps", app_name, f"ph{app_name}")
        os.makedirs(os.path.dirname(dest_dir), exist_ok=True)
        shutil.copytree(app_dirname, dest_dir, dirs_exist_ok=True)

        run_git(["git", "add", dest_dir])
        run_git(["git", "commit", "-m", f"Add extracted app '{app_name}' to extracted_apps/"])
        run_git(["git", "push"])

    # Switch to `ready_for_prod`
    run_git(["git", "fetch", "origin"])
    run_git(["git", "checkout", "-B", "ready_for_prod", "origin/ready_for_prod"])

    # Create new promote branch
    new_branch = f"promote/{app_name.replace(' ', '-').lower()}"
    run_git(["git", "checkout", "-b", new_branch])

    # Copy from committed content, not from tgz
    src_dir = os.path.join("extracted_apps", app_name)
    dst_dir = os.path.join("promoted_apps", app_name)
    shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True)

    run_git(["git", "add", dst_dir])
    run_git(["git", "commit", "-m", f"Promote app '{app_name}' to ready_for_prod"])
    run_git(["git", "push", "-u", "origin", new_branch])

    return new_branch


def main():
    tgz_files = [f for f in os.listdir("apps") if f.endswith(".tgz")]
    if not tgz_files:
        print("❌ No .tgz files found in apps/")
        sys.exit(1)

    for tgz in tgz_files:
        app_name = os.path.splitext(tgz)[0]
        lint_results = run_lint(os.path.join("extracted_apps", app_name))
        if lint_results:
            print("Lint Results:\n", lint_results)

        new_branch = promote_to_ready_for_prod(app_name)
        print(f"✅ App '{app_name}' promoted on branch '{new_branch}'")


if __name__ == "__main__":
    main()
