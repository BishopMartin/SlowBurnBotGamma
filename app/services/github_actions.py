"""GitHub Actions integration — workflow dispatch and status polling."""
import base64
import hashlib
import io
import json
import zipfile
from datetime import datetime, timezone

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


async def dispatch_workflow(
    build_id: str,
    user_id: str,
    client_id: int,
    api_url: str,
    activation_token: str,
    build_options: dict,
) -> None:
    """Trigger workflow_dispatch for a desktop build. Raises on failure."""
    config_json_b64 = base64.b64encode(
        json.dumps(build_options).encode()
    ).decode()

    payload = {
        "ref": "main",
        "inputs": {
            "build_id": build_id,
            "user_id": user_id,
            "client_id": str(client_id),
            "api_url": api_url,
            "activation_token": activation_token,
            "config_json_b64": config_json_b64,
        },
    }

    url = f"{_GH_API}/repos/{settings.github_repo}/actions/workflows/{settings.github_workflow_file}/dispatches"
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(url, json=payload, headers=_headers())
    if resp.status_code != 204:
        raise RuntimeError(
            f"GitHub dispatch failed: {resp.status_code} {resp.text[:200]}"
        )


async def find_run_for_build(build_id: str, created_after: datetime) -> str | None:
    """
    Find the GitHub Actions run ID for a dispatched build.

    GitHub dispatch returns 204 with no run_id, so we query recent runs and
    match on the run name (workflow sets name: "build-{build_id}").
    """
    since = created_after.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    url = (
        f"{_GH_API}/repos/{settings.github_repo}/actions/workflows"
        f"/{settings.github_workflow_file}/runs"
    )
    params = {"created": f">={since}", "per_page": 20}
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(url, params=params, headers=_headers())
    if resp.status_code != 200:
        return None
    runs = resp.json().get("workflow_runs", [])
    target_name = f"build-{build_id}"
    for run in runs:
        if run.get("name") == target_name or build_id in run.get("name", ""):
            return str(run["id"])
    return None


async def get_workflow_run(run_id: str) -> dict:
    """Fetch a single workflow run object from GitHub."""
    url = f"{_GH_API}/repos/{settings.github_repo}/actions/runs/{run_id}"
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(url, headers=_headers())
    resp.raise_for_status()
    return resp.json()


async def download_artifact(run_id: str, artifact_name: str) -> tuple[bytes, str]:
    """
    Download a named artifact from a completed workflow run.

    Returns (exe_bytes, sha256_hex). The artifact zip is extracted in memory.
    """
    list_url = f"{_GH_API}/repos/{settings.github_repo}/actions/runs/{run_id}/artifacts"
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        list_resp = await client.get(list_url, headers=_headers())
    list_resp.raise_for_status()

    artifacts = list_resp.json().get("artifacts", [])
    target = next((a for a in artifacts if a["name"] == artifact_name), None)
    if target is None:
        raise FileNotFoundError(
            f"Artifact '{artifact_name}' not found in run {run_id}"
        )

    download_url = target["archive_download_url"]
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(120.0), follow_redirects=True
    ) as client:
        dl_resp = await client.get(download_url, headers=_headers())
    dl_resp.raise_for_status()

    # Artifact is a zip; extract the first .exe inside
    with zipfile.ZipFile(io.BytesIO(dl_resp.content)) as zf:
        exe_names = [n for n in zf.namelist() if n.lower().endswith(".exe")]
        if not exe_names:
            raise FileNotFoundError("No .exe found inside artifact zip")
        exe_bytes = zf.read(exe_names[0])

    sha256 = hashlib.sha256(exe_bytes).hexdigest()
    return exe_bytes, sha256
