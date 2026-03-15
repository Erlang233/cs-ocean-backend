import os
import re
import httpx

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

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
    owner, repo = match.group(1), match.group(2).rstrip(".git")
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
