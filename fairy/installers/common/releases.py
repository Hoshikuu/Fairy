"""Pinned GitHub release lookup and asset metadata validation."""
import re
import requests

# =========================================================
# RELEASE AND ASSET SELECTION
# =========================================================


def get_release(*, api_url, tag, headers):
    """Fetch and validate exactly the pinned release."""
    response = requests.get(api_url, headers=headers, timeout=20)
    response.raise_for_status()
    release = response.json()
    if release.get("tag_name") != tag or release.get("draft"):
        raise RuntimeError(f"GitHub did not return the expected non-draft release {tag}.")
    return release


def asset_info(asset, *, prefix, tag):
    url = asset["browser_download_url"]
    if not url.startswith(prefix):
        raise RuntimeError(f"Unexpected asset URL outside {tag}: {url}")
    digest = asset.get("digest") or ""
    sha256 = digest.removeprefix("sha256:") if digest.startswith("sha256:") else None
    return {"name": asset["name"], "url": url, "size": int(asset["size"]), "sha256": sha256}


def find_exact_asset(release, filename, *, prefix, tag):
    for asset in release.get("assets", []):
        if asset["name"].lower() == filename.lower():
            return asset_info(asset, prefix=prefix, tag=tag)
    return None


def version_tuple(version):
    match = re.match(r"(\d+)(?:\.(\d+))?", version)
    if not match:
        return 0, 0
    return int(match.group(1)), int(match.group(2) or 0)
