"""GitHub API helpers — bot version lookups only."""
import base64

import httpx

from app.settings import settings

_GH_API = "https://api.github.com"
_TIMEOUT = httpx.Timeout(30.0)


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
