#!/usr/bin/env python3
"""Test giteapy SDK merge functionality with httpx for other operations."""

import time
import base64
import httpx
import giteapy
from giteapy.rest import ApiException

# Configuration
GITEA_URL = "http://localhost:3001"
TOKEN = "f10f946e4af76ad8ece8f80f507ddb9183dbad05"
OWNER = "cahoots-bot"
REPO = f"test-giteapy-{int(time.time())}"

# HTTP headers for direct API calls
HEADERS = {
    "Authorization": f"token {TOKEN}",
    "Content-Type": "application/json"
}

# Setup giteapy for merge
config = giteapy.Configuration()
config.host = f"{GITEA_URL}/api/v1"
config.api_key['access_token'] = TOKEN
client = giteapy.ApiClient(config)
repo_api = giteapy.RepositoryApi(client)


def api_request(method, path, json_data=None):
    """Make HTTP request to Gitea API."""
    url = f"{GITEA_URL}/api/v1{path}"
    with httpx.Client(timeout=30.0) as client:
        response = client.request(method, url, headers=HEADERS, json=json_data)
        return response


def main():
    print(f"=== Testing giteapy SDK Merge ===")
    print(f"Repo: {REPO}")
    print()

    try:
        # Step 1: Create repository
        print("Step 1: Creating repository...")
        response = api_request("POST", "/user/repos", {
            "name": REPO,
            "description": "Test repo for giteapy merge",
            "private": True,
            "auto_init": True,
            "default_branch": "main"
        })
        if response.status_code != 201:
            print(f"  Failed: {response.status_code} - {response.text}")
            return
        print(f"  Created: {response.json()['full_name']}")
        time.sleep(2)  # Wait for initialization

        # Step 2: Create feature branch
        print("Step 2: Creating feature branch...")
        response = api_request("POST", f"/repos/{OWNER}/{REPO}/branches", {
            "new_branch_name": "feature-test",
            "old_branch_name": "main"
        })
        if response.status_code != 201:
            print(f"  Failed: {response.status_code} - {response.text}")
            api_request("DELETE", f"/repos/{OWNER}/{REPO}")
            return
        print(f"  Created branch: {response.json()['name']}")

        # Step 3: Add a file to the feature branch
        print("Step 3: Adding file to feature branch...")
        content = base64.b64encode(b"Hello from giteapy!").decode()
        response = api_request("POST", f"/repos/{OWNER}/{REPO}/contents/giteapy-test.txt", {
            "content": content,
            "message": "Add test file via giteapy",
            "branch": "feature-test"
        })
        if response.status_code != 201:
            print(f"  Failed: {response.status_code} - {response.text}")
            api_request("DELETE", f"/repos/{OWNER}/{REPO}")
            return
        print(f"  Created file, commit: {response.json()['commit']['sha'][:8]}")

        # Step 4: Create PR
        print("Step 4: Creating pull request...")
        response = api_request("POST", f"/repos/{OWNER}/{REPO}/pulls", {
            "title": "Test PR from giteapy",
            "head": "feature-test",
            "base": "main",
            "body": "Testing merge via giteapy SDK"
        })
        if response.status_code != 201:
            print(f"  Failed: {response.status_code} - {response.text}")
            api_request("DELETE", f"/repos/{OWNER}/{REPO}")
            return
        pr = response.json()
        print(f"  Created PR #{pr['number']}")
        print(f"  State: {pr['state']}, Mergeable: {pr.get('mergeable')}")

        # Step 5: Wait a moment for PR to be ready
        print("Step 5: Waiting for PR to be ready...")
        time.sleep(2)

        # Check PR status
        response = api_request("GET", f"/repos/{OWNER}/{REPO}/pulls/{pr['number']}")
        pr = response.json()
        print(f"  State: {pr['state']}, Mergeable: {pr.get('mergeable')}, Merged: {pr.get('merged')}")

        # Step 6: Merge PR using giteapy SDK
        print("Step 6: Merging PR using giteapy SDK...")
        merge_body = giteapy.MergePullRequestOption(
            do="merge",
            merge_message_field="Merge via giteapy SDK test"
        )

        try:
            repo_api.repo_merge_pull_request(
                owner=OWNER,
                repo=REPO,
                index=pr['number'],
                body=merge_body
            )
            print("  Merge API call succeeded!")

            # Verify merge
            response = api_request("GET", f"/repos/{OWNER}/{REPO}/pulls/{pr['number']}")
            pr = response.json()
            print(f"  PR merged: {pr.get('merged')}")
            if pr.get('merge_commit_sha'):
                print(f"  Merge commit: {pr.get('merge_commit_sha')[:8]}")

        except ApiException as e:
            print(f"  Merge failed with {e.status}: {e.body}")

            # Check if actually merged
            response = api_request("GET", f"/repos/{OWNER}/{REPO}/pulls/{pr['number']}")
            pr = response.json()
            if pr.get('merged'):
                print(f"  But PR is actually merged! Commit: {pr.get('merge_commit_sha')[:8]}")
            else:
                print(f"  PR not merged. State: {pr.get('state')}")

        # Step 7: Cleanup
        print()
        print("Step 7: Cleaning up...")
        api_request("DELETE", f"/repos/{OWNER}/{REPO}")
        print(f"  Deleted {REPO}")

        print()
        print("=== Test Complete ===")

    except Exception as e:
        print(f"Error: {e}")
        # Try to cleanup
        try:
            api_request("DELETE", f"/repos/{OWNER}/{REPO}")
        except:
            pass
        raise


if __name__ == "__main__":
    main()
