import os
import tarfile
import glob
import subprocess

def extract_app(tgz_path, output_dir):
    print(f"Extracting {tgz_path} to {output_dir}")
    with tarfile.open(tgz_path, "r:gz") as tar:
        tar.extractall(output_dir)

def lint_connector(app_name, extracted_path):
    connector_files = glob.glob(os.path.join(extracted_path, "ph*", "*_connector.py"))
    if not connector_files:
        print(f"No connector found in {extracted_path}")
        return

    connector_file = connector_files[0]
    print(f"Linting: {connector_file}")

    result = subprocess.run(["flake8", connector_file], capture_output=True, text=True)
    lint_output = result.stdout or "No lint issues found."

    lint_file = f"lint_result_{app_name}.txt"
    with open(lint_file, "w") as f:
        f.write(lint_output)

    print(f"Lint results written to {lint_file}")

if __name__ == "__main__":
    tgz_files = glob.glob("apps/*.tgz")
    if not tgz_files:
        print("No .tgz app files found in apps/")
        exit(1)

    tgz_path = tgz_files[-1]
    app_name = os.path.basename(tgz_path).replace(".tgz", "").replace(" ", "_")
    output_dir = os.path.join("extracted_apps", app_name)

    os.makedirs(output_dir, exist_ok=True)
    extract_app(tgz_path, output_dir)
    lint_connector(app_name, output_dir)
