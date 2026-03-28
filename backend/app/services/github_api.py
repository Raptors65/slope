import logging

import httpx

from app.constants import ONBOARDING_MAP_MARKER

log = logging.getLogger("slope.github")

GITHUB_ACCEPT = "application/vnd.github+json"
GITHUB_API_VERSION = "2022-11-28"


def _headers(pat: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {pat}",
        "Accept": GITHUB_ACCEPT,
        "X-GitHub-Api-Version": GITHUB_API_VERSION,
    }


async def issue_comments_contain_marker(
    owner: str,
    repo: str,
    issue_number: int,
    pat: str,
    *,
    marker: str = ONBOARDING_MAP_MARKER,
) -> bool:
    """Return True if any issue comment body contains the onboarding map marker."""
    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}/comments"
    page = 1
    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            r = await client.get(
                url,
                params={"per_page": 100, "page": page},
                headers=_headers(pat),
            )
            r.raise_for_status()
            batch: list = r.json()
            if not batch:
                return False
            for c in batch:
                body = c.get("body") or ""
                if marker in body:
                    log.info(
                        "Idempotency skip: marker already present on issue %s/%s#%s",
                        owner,
                        repo,
                        issue_number,
                    )
                    return True
            if len(batch) < 100:
                return False
            page += 1
