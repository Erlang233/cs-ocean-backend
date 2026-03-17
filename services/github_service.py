import os
import re
import httpx
from typing import Optional

_raw_token = os.getenv("GITHUB_TOKEN", "").split("#")[0].strip()
GITHUB_TOKEN = _raw_token if _raw_token and not _raw_token.startswith("ghp_...") else None

# Files to fetch from a repo for tech detection
TARGET_FILES = [
    "package.json",
    "requirements.txt",
    "Pipfile",
    "pyproject.toml",
    "go.mod",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "Cargo.toml",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    ".github/workflows",
    "Makefile",
    "terraform/main.tf",
    "k8s",
    "kubernetes",
]


def parse_github_url(url: str) -> tuple[str, str]:
    """Return (owner, repo) from a github.com URL."""
    match = re.search(r"github\.com/([^/]+)/([^/\s?#]+)", url)
    if not match:
        raise ValueError(f"Invalid GitHub URL: {url}")
    owner, repo = match.group(1), match.group(2).removesuffix(".git")
    return owner, repo


async def fetch_repo_files(github_url: str) -> dict[str, str]:
    """Fetch key config files from a public GitHub repo. Returns {filename: content}."""
    owner, repo = parse_github_url(github_url)
    headers = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    results: dict[str, str] = {}

    async with httpx.AsyncClient(timeout=30) as client:
        # First get the repo file tree (shallow)
        tree_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/HEAD?recursive=1"
        tree_resp = await client.get(tree_url, headers=headers)
        if tree_resp.status_code != 200:
            raise ValueError(f"Cannot access repo {owner}/{repo}: {tree_resp.status_code}")

        tree = tree_resp.json().get("tree", [])
        blob_paths = [item["path"] for item in tree if item["type"] == "blob"]

        # Match against target files
        to_fetch = []
        for target in TARGET_FILES:
            for path in blob_paths:
                if path == target or path.endswith("/" + target) or path.startswith(target + "/"):
                    to_fetch.append(path)
                    break  # one match per target

        # Fetch raw content for each matched file (limit to 10 files, 50KB each)
        for path in to_fetch[:10]:
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/HEAD/{path}"
            resp = await client.get(raw_url, headers=headers)
            if resp.status_code == 200:
                results[path] = resp.text[:50_000]  # cap at 50KB

    return results


# Source entry point patterns for deep analysis
_DEEP_TARGET_FILES = [
    "README.md",
    "README.rst",
    "src/index.ts",
    "src/index.tsx",
    "src/index.js",
    "src/main.ts",
    "src/main.tsx",
    "src/main.py",
    "src/app.py",
    "app.py",
    "main.py",
    "server.py",
    "index.js",
    "src/App.tsx",
    "src/App.ts",
    "src/App.jsx",
    # config files (same as shallow)
    "package.json",
    "requirements.txt",
    "pyproject.toml",
    "go.mod",
    "Cargo.toml",
    "Dockerfile",
    "docker-compose.yml",
]


async def fetch_repo_files_deep(github_url: str) -> dict[str, str]:
    """Fetch a richer set of files for deep project analysis."""
    owner, repo = parse_github_url(github_url)
    headers = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    results: dict[str, str] = {}

    async with httpx.AsyncClient(timeout=30) as client:
        tree_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/HEAD?recursive=1"
        tree_resp = await client.get(tree_url, headers=headers)
        if tree_resp.status_code != 200:
            raise ValueError(f"Cannot access repo {owner}/{repo}: {tree_resp.status_code}")

        tree = tree_resp.json().get("tree", [])
        blob_paths = [item["path"] for item in tree if item["type"] == "blob"]

        to_fetch: list[str] = []
        for target in _DEEP_TARGET_FILES:
            for path in blob_paths:
                if path == target or path.endswith("/" + target):
                    to_fetch.append(path)
                    break

        for path in to_fetch[:15]:  # max 15 files
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/HEAD/{path}"
            resp = await client.get(raw_url, headers=headers)
            if resp.status_code == 200:
                results[path] = resp.text[:30_000]  # cap at 30KB

    return results


def repo_name_from_url(github_url: str) -> str:
    owner, repo = parse_github_url(github_url)
    return f"{owner}/{repo}"
