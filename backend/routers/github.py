from fastapi import APIRouter, HTTPException
import httpx
import os
from typing import List, Optional

import schemas

router = APIRouter(prefix="/github", tags=["github"])

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")


async def github_request(endpoint: str, params: dict = None):
    """Make authenticated request to GitHub API"""
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://api.github.com{endpoint}",
            headers=headers,
            params=params,
            timeout=30.0
        )
        if resp.status_code == 401:
            raise HTTPException(status_code=401, detail="GitHub token invalid or missing")
        if resp.status_code == 403:
            raise HTTPException(status_code=403, detail="GitHub rate limit exceeded")
        resp.raise_for_status()
        return resp.json()


@router.get("/status")
async def github_status():
    """Check if GitHub integration is configured"""
    return {
        "configured": bool(GITHUB_TOKEN),
        "message": "GitHub token configured" if GITHUB_TOKEN else "Set GITHUB_TOKEN environment variable"
    }


@router.get("/repos", response_model=List[schemas.GitHubRepo])
async def list_repos(
    per_page: int = 100,
    sort: str = "updated",
    type: str = "owner"
):
    """List authenticated user's repositories"""
    if not GITHUB_TOKEN:
        raise HTTPException(status_code=400, detail="GitHub token not configured")

    data = await github_request("/user/repos", {
        "per_page": per_page,
        "sort": sort,
        "type": type
    })

    return [
        schemas.GitHubRepo(
            name=repo["name"],
            full_name=repo["full_name"],
            description=repo.get("description"),
            html_url=repo["html_url"],
            updated_at=repo.get("updated_at")
        )
        for repo in data
    ]


@router.get("/repos/{owner}/{repo}")
async def get_repo(owner: str, repo: str):
    """Get details for a specific repository"""
    data = await github_request(f"/repos/{owner}/{repo}")
    return schemas.GitHubRepo(
        name=data["name"],
        full_name=data["full_name"],
        description=data.get("description"),
        html_url=data["html_url"],
        updated_at=data.get("updated_at")
    )


@router.get("/repos/{owner}/{repo}/issues")
async def get_repo_issues(owner: str, repo: str, state: str = "open"):
    """Get issues for a repository (can be imported as tasks)"""
    data = await github_request(f"/repos/{owner}/{repo}/issues", {
        "state": state,
        "per_page": 100
    })
    return [
        {
            "number": issue["number"],
            "title": issue["title"],
            "body": issue.get("body"),
            "state": issue["state"],
            "labels": [l["name"] for l in issue.get("labels", [])],
            "created_at": issue["created_at"],
            "updated_at": issue["updated_at"]
        }
        for issue in data
        if "pull_request" not in issue  # Filter out PRs
    ]
