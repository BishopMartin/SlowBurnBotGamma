"""GitHub API helpers — bot version lookups only."""
import base64
import logging

import httpx

from app.settings import settings

_GH_API = "https://api.github.com"
_TIMEOUT = httpx.Timeout(30.0)
_log = logging.getLogger(__name__)


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


async def get_main_branch_bot_version() -> str | None:
    """Read BOT_VERSION from burnBot_version.py on the HEAD of the main branch."""
    url = f"{_GH_API}/repos/{settings.github_repo}/contents/bot-client/burnBot_version.py"
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(url, headers=_headers())
    if resp.status_code != 200:
        return None
    try:
        content = base64.b64decode(resp.json()["content"]).decode()
        for line in content.splitlines():
            if line.startswith("BOT_VERSION"):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return None


async def ghcr_image_has_tag(tag: str) -> bool:
    """Return True if slowburnbot-client:{tag} exists in GHCR.

    Uses the OCI distribution spec manifest check (ghcr.io/v2/…) which works
    with repo-scoped tokens (no read:packages scope required). Falls back to
    the GitHub Packages REST API if the OCI check itself errors.
    """
    owner, repo_name = settings.github_repo.lower().split("/", 1)
    image = f"{owner}/{repo_name}/slowburnbot-client"

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        # Exchange the GitHub PAT for a GHCR registry token.
        # GHCR maps repo read access → package read access, so this works
        # without an explicit read:packages scope on the PAT.
        basic = base64.b64encode(f"{owner}:{settings.github_token}".encode()).decode()
        token_resp = await client.get(
            f"https://ghcr.io/token?service=ghcr.io&scope=repository:{image}:pull",
            headers={"Authorization": f"Basic {basic}"},
        )
        if token_resp.status_code == 200:
            registry_token = token_resp.json().get("token", "")
            manifest_resp = await client.head(
                f"https://ghcr.io/v2/{image}/manifests/{tag}",
                headers={
                    "Authorization": f"Bearer {registry_token}",
                    "Accept": "application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.v2+json",
                },
            )
            if manifest_resp.status_code == 200:
                return True
            _log.info("GHCR manifest HEAD returned %s for %s:%s", manifest_resp.status_code, image, tag)
        else:
            _log.warning("GHCR token exchange failed: HTTP %s — %s", token_resp.status_code, token_resp.text[:200])

    # Fallback: GitHub Packages REST API (requires read:packages scope)
    package = f"{repo_name}%2Fslowburnbot-client"
    url = f"{_GH_API}/users/{owner}/packages/container/{package}/versions?per_page=100"
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(url, headers=_headers())
    if resp.status_code != 200:
        _log.warning("GitHub Packages API returned %s for %s (token may lack read:packages scope)", resp.status_code, package)
        return False
    try:
        for version in resp.json():
            tags = version.get("metadata", {}).get("container", {}).get("tags", [])
            if tag in tags:
                return True
    except Exception:
        pass
    return False
