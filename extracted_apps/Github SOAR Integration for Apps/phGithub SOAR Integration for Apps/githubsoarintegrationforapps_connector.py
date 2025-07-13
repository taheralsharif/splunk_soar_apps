#!/usr/bin/python
# -*- coding: utf-8 -*-
# -----------------------------------------
# Phantom App Connector: Upload SOAR .tgz to GitHub via API
# Uses asset input fields for all credentials and settings
# Includes connectivity tests and masked debug output
# -----------------------------------------

import requests
import base64
import phantom.app as phantom
from phantom.action_result import ActionResult
from phantom.base_connector import BaseConnector

class GithubAppConnectorConnector(BaseConnector):
    def __init__(self):
        super(GithubAppConnectorConnector, self).__init__()
        self._state = None
        # Configurable fields initialized in initialize()
        self._soar_url = None
        self._soar_token = None
        self._github_token = None
        self._github_repo = None
        self._github_branch = None

    def initialize(self):
        """Load configuration from asset settings."""
        self._state = self.load_state()
        cfg = self.get_config()

        # Required inputs
        self._soar_url       = cfg.get('soar_url', '').strip()
        self._soar_token     = cfg.get('soar_token', '').strip()
        self._github_token   = cfg.get('github_token', '').strip()
        self._github_repo    = cfg.get('github_repo', '').strip()
        self._github_branch  = cfg.get('github_branch', 'main').strip() or 'main'

        # Mask tokens for safe debug logging
        def mask(tok):
            if not tok:
                return 'None'
            return f"{tok[:4]}...{tok[-4:]}" if len(tok) > 8 else tok

        self.save_progress(
            f"DEBUG Config: soar_url={self._soar_url}, "
            f"soar_token={mask(self._soar_token)}, "
            f"github_token={mask(self._github_token)}, "
            f"github_repo={self._github_repo}, "
            f"github_branch={self._github_branch}"
        )

        return phantom.APP_SUCCESS

    def finalize(self):
        """Save state."""
        self.save_state(self._state)
        return phantom.APP_SUCCESS

    def handle_action(self, param):
        action = self.get_action_identifier()
        if action == 'test_connectivity':
            return self._handle_test_connectivity(param)
        if action == 'test_github_connection':
            return self._handle_test_github_connection(param)
        if action == 'upload_app_to_github':
            return self._handle_upload_app_to_github(param)
        return self.set_status(phantom.APP_ERROR, f"Unsupported action: {action}")

    def _handle_test_connectivity(self, param):
        ar = self.add_action_result(ActionResult(dict(param)))
        if not self._soar_url:
            return ar.set_status(phantom.APP_ERROR, 'Missing SOAR URL in config')
        try:
            resp = requests.get(self._soar_url, verify=False)
            if resp.status_code in (200, 204):
                return ar.set_status(phantom.APP_SUCCESS)
            return ar.set_status(phantom.APP_ERROR, f"SOAR API returned {resp.status_code}")
        except Exception as e:
            return ar.set_status(phantom.APP_ERROR, f"Connectivity error: {e}")

    def _handle_test_github_connection(self, param):
        ar = self.add_action_result(ActionResult(dict(param)))
        if not self._github_token:
            return ar.set_status(phantom.APP_ERROR, 'Missing GitHub token in config')
        headers = {
            'Authorization': f"token {self._github_token}",
            'Accept': 'application/vnd.github.v3+json'
        }
        try:
            resp = requests.get('https://api.github.com/user', headers=headers)
            if resp.status_code == 200:
                return ar.set_status(phantom.APP_SUCCESS)
            return ar.set_status(phantom.APP_ERROR, f"GitHub API returned {resp.status_code}")
        except Exception as e:
            return ar.set_status(phantom.APP_ERROR, f"GitHub connectivity error: {e}")

    def _handle_upload_app_to_github(self, param):
        ar = self.add_action_result(ActionResult(dict(param)))
        app_id = param.get('app_id')
        if not app_id:
            return ar.set_status(phantom.APP_ERROR, "Missing parameter 'app_id'")

        # Validate config
        missing = []
        for fld in ('_soar_url', '_soar_token', '_github_token', '_github_repo'):
            if not getattr(self, fld):
                missing.append(fld)
        if missing:
            return ar.set_status(phantom.APP_ERROR, f"Missing config: {', '.join(missing)}")

        # GitHub headers
        gh_headers = {
            'Authorization': f"token {self._github_token}",
            'Accept': 'application/vnd.github.v3+json'
        }
        repo_api = f"https://api.github.com/repos/{self._github_repo}"

        # 1) Check GitHub access
        resp = requests.get(repo_api, headers=gh_headers)
        if resp.status_code != 200:
            return ar.set_status(phantom.APP_ERROR, f"GitHub pre-check failed: HTTP {resp.status_code}")

        # 2) Verify branch
        br = requests.get(f"{repo_api}/branches/{self._github_branch}", headers=gh_headers)
        if br.status_code != 200:
            return ar.set_status(phantom.APP_ERROR, f"Branch '{self._github_branch}' not found: HTTP {br.status_code}")

        # 3) Download TGZ from SOAR
        dl_url = f"{self._soar_url.rstrip('/')}/rest/app_download/{app_id}"
        dl = requests.get(dl_url, headers={'ph-auth-token': self._soar_token}, verify=False)
        if dl.status_code != 200:
            return ar.set_status(phantom.APP_ERROR, f"SOAR download failed: HTTP {dl.status_code}")
        content = dl.content

        # 4) Fetch metadata for app name
        meta_url = f"{self._soar_url.rstrip('/')}/rest/app/{app_id}"
        meta = requests.get(meta_url, headers={'ph-auth-token': self._soar_token}, verify=False)
        if meta.status_code == 200:
            app_name = meta.json().get('name') or str(app_id)
        else:
            app_name = str(app_id)
        filename = f"{app_name}.tgz"

        # 5) Encode content
        b64 = base64.b64encode(content).decode('utf-8')
        path = f"apps/{filename}"
        content_api = f"{repo_api}/contents/{path}"

        # 6) Get existing SHA if present
        existing = requests.get(f"{content_api}?ref={self._github_branch}", headers=gh_headers)
        sha = existing.json().get('sha') if existing.status_code == 200 else None

        # 7) Push to GitHub
        payload = {'message': f"Upload SOAR app {app_name}", 'content': b64, 'branch': self._github_branch}
        if sha:
            payload['sha'] = sha
        put = requests.put(content_api, headers=gh_headers, json=payload)
        if put.status_code not in (200, 201):
            return ar.set_status(phantom.APP_ERROR, f"GitHub upload failed: HTTP {put.status_code} - {put.text}")

        # 8) Return URL
        url = put.json().get('content', {}).get('html_url')
        ar.update_summary({'url': url})
        ar.add_data({'download_url': url})
        return ar.set_status(phantom.APP_SUCCESS)

if __name__ == '__main__':
    pass  # Execution via Phantom only
