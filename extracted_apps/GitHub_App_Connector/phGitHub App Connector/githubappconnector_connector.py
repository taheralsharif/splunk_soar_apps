#!/usr/bin/python
# -*- coding: utf-8 -*-
# -----------------------------------------
# Phantom App Connector: Upload SOAR .tgz to GitHub via API (with branch check)
# -----------------------------------------

import os
import requests
import base64
import phantom.app as phantom
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

class GithubAppConnectorConnector(BaseConnector):
    def __init__(self):
        super(GithubAppConnectorConnector, self).__init__()
        self._state = None
        self._soar_base_url = None

    def initialize(self):
        """Initialize state and config."""
        self._state = self.load_state()
        cfg = self.get_config()
        self._soar_base_url = cfg.get('soar_url')
        return phantom.APP_SUCCESS

    def finalize(self):
        """Save state."""
        self.save_state(self._state)
        return phantom.APP_SUCCESS

    def handle_action(self, param):
        action = self.get_action_identifier()
        if action == "upload_app_to_github":
            return self._handle_upload_app_to_github(param)
        elif action == "test_github_connection":
            return self._handle_test_github_connection(param)
        elif action == "test_connectivity":
            return self._handle_test_connectivity(param)
        return self.set_status(
            phantom.APP_ERROR,
            f"Unsupported action: {action}"
        )

    def _handle_test_connectivity(self, param):
        ar = self.add_action_result(ActionResult(dict(param)))
        try:
            r = requests.get(self._soar_base_url, verify=False)
            if r.status_code in (200, 204):
                return ar.set_status(phantom.APP_SUCCESS)
            return ar.set_status(phantom.APP_ERROR, f"SOAR API returned {r.status_code}")
        except Exception as e:
            return ar.set_status(phantom.APP_ERROR, f"Connectivity error: {e}")

    def _handle_test_github_connection(self, param):
        ar = self.add_action_result(ActionResult(dict(param)))
        cfg = self.get_config()
        github_token = cfg.get('github_token')
        if not github_token:
            return ar.set_status(phantom.APP_ERROR, "Missing github_token")
        headers = {"Authorization": f"token {github_token}"}
        try:
            r = requests.get("https://api.github.com/user", headers=headers)
            if r.status_code == 200:
                return ar.set_status(phantom.APP_SUCCESS)
            return ar.set_status(phantom.APP_ERROR, f"GitHub API returned {r.status_code}")
        except Exception as e:
            return ar.set_status(phantom.APP_ERROR, f"GitHub connectivity error: {e}")

    def _handle_upload_app_to_github(self, param):
        ar = self.add_action_result(ActionResult(dict(param)))
        app_id = param.get('app_id')
        if not app_id:
            return ar.set_status(phantom.APP_ERROR, "Missing 'app_id'")

        # Config values
        cfg = self.get_config()
        soar_token = cfg.get('soar_token')      # SOAR automation token
        soar_url = cfg.get('soar_url')          # e.g. https://soar.company.local
        github_token = cfg.get('github_token')  # GitHub PAT
        github_repo = cfg.get('github_repo')     # owner/repo
        github_branch = cfg.get('github_branch', 'from_soar_dev')

        if not all([soar_token, soar_url, github_token, github_repo]):
            return ar.set_status(
                phantom.APP_ERROR,
                "Missing config: soar_token/soar_url/github_token/github_repo"
            )

        gh_headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json"
        }

        # Verify repo exists
        repo_url = f"https://api.github.com/repos/{github_repo}"
        if requests.get(repo_url, headers=gh_headers).status_code != 200:
            return ar.set_status(phantom.APP_ERROR, f"Repository '{github_repo}' not found")

        # Verify branch exists
        branch_url = f"{repo_url}/branches/{github_branch}"
        if requests.get(branch_url, headers=gh_headers).status_code != 200:
            return ar.set_status(phantom.APP_ERROR, f"Branch '{github_branch}' not found in {github_repo}")

        # 3) Fetch SOAR metadata to get the real app name
        meta_url = f"{soar_url}/rest/app/{app_id}"
        meta_resp = requests.get(meta_url, headers={"ph-auth-token": soar_token}, verify=False)
        if meta_resp.status_code != 200:
            return ar.set_status(phantom.APP_ERROR, f"Failed to fetch app metadata: HTTP {meta_resp.status_code}")
        meta = meta_resp.json()
        app_name = meta.get('name') or meta.get('appname') or str(app_id)

        # 4) Download the .tgz using the app name
        dl_url = f"{soar_url}/rest/app_download/{app_id}"
        dl_resp = requests.get(dl_url, headers={"ph-auth-token": soar_token}, verify=False)
        if dl_resp.status_code != 200:
            return ar.set_status(phantom.APP_ERROR, f"Download failed: HTTP {dl_resp.status_code}")
        content = dl_resp.content
        filename = f"{app_name}.tgz"

        # 5) Prepare GitHub upload
        b64_content = base64.b64encode(content).decode('utf-8')
        path_on_repo = f"apps/{filename}"
        contents_url = f"{repo_url}/contents/{path_on_repo}"

        # 6) Check if the file exists (to get sha)
        existing = requests.get(contents_url + f"?ref={github_branch}", headers=gh_headers)
        sha = existing.json().get('sha') if existing.status_code == 200 else None

        # 7) Create or update file on GitHub
        payload = {
            "message": f"Upload SOAR app {app_name}",
            "content": b64_content,
            "branch": github_branch
        }
        if sha:
            payload['sha'] = sha

        put_resp = requests.put(contents_url, headers=gh_headers, json=payload)
        if put_resp.status_code not in (200, 201):
            return ar.set_status(
                phantom.APP_ERROR,
                f"GitHub upload failed: HTTP {put_resp.status_code} - {put_resp.text}"
            )

        link = put_resp.json().get('content', {}).get('html_url')
        ar.update_summary({"url": link})
        ar.add_data({"download_url": link})
        return ar.set_status(phantom.APP_SUCCESS)

    def main(self):
        # pylint: disable=no-member
        return super(GithubAppConnectorConnector, self).main()

if __name__ == '__main__':
    GithubAppConnectorConnector().main()
