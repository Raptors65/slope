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


async def fetch_issue(
    owner: str,
    repo: str,
    issue_number: int,
    pat: str,
) -> tuple[str, str]:
    """Return (title, body) for the issue via GitHub REST."""
    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(url, headers=_headers(pat))
        r.raise_for_status()
        data = r.json()
    title = data.get("title")
    body = data.get("body")
    return (str(title or ""), str(body or ""))


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


def format_onboarding_map_comment_body(*, dashboard_base_url: str, run_id: str) -> str:
    """GFM comment: friendly link text, attribution footer, idempotency HTML comment (Phase 8)."""
    base = (dashboard_base_url or "").strip().rstrip("/") or "http://localhost:3000"
    url = f"{base}/runs/{run_id}"
    return (
        f"Your onboarding map is ready — **[open the dashboard]({url})**.\n\n"
        f"---\n\n"
        f"*Posted by **Slope**.*\n\n"
        f"{ONBOARDING_MAP_MARKER}"
    )


async def post_issue_comment(
    owner: str,
    repo: str,
    issue_number: int,
    pat: str,
    *,
    body: str,
) -> None:
    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}/comments"
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(url, headers=_headers(pat), json={"body": body})
        if not r.is_success:
            log.warning(
                "GitHub POST comment %s/%s#%s failed: %s %s — %s",
                owner,
                repo,
                issue_number,
                r.status_code,
                getattr(r, "reason_phrase", "") or "",
                (r.text or "")[:2000],
            )
        r.raise_for_status()
