import os

import requests


class GitHubClient:
    def __init__(self):
        self.token = os.getenv("GITHUB_TOKEN")
        self.repo = os.getenv("GITHUB_REPOSITORY")

        if not self.token:
            raise ValueError("GITHUB_TOKEN is missing")

        if not self.repo:
            raise ValueError(
                "GITHUB_REPOSITORY is missing. Example: username/driftbounty-lite"
            )

        self.base_url = f"https://api.github.com/repos/{self.repo}"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def issue_exists(self, title: str) -> bool:
        url = f"{self.base_url}/issues"
        params = {
            "state": "open",
            "labels": "driftbounty",
        }

        response = requests.get(url, headers=self.headers, params=params, timeout=10)
        response.raise_for_status()

        for issue in response.json():
            if issue.get("title") == title:
                return True

        return False

    def create_issue(self, title: str, body: str):
        if self.issue_exists(title):
            print(f"Issue already exists: {title}")
            return

        url = f"{self.base_url}/issues"
        payload = {
            "title": title,
            "body": body,
            "labels": ["driftbounty", "kubernetes-drift"],
        }

        response = requests.post(url, headers=self.headers, json=payload, timeout=10)
        response.raise_for_status()

        print(f"Created GitHub issue: {title}")
