"""OWNER static shell adapter. Integration candidate only, not an authentication boundary.
All requests must already be on the existing protected OWNER origin.
Private API handlers and credentials remain outside this adapter.
"""
from pathlib import Path
from urllib.parse import urlsplit
import re

UI_PATHS = frozenset(["collaboratori.html","collaboratori.css","asset.html","assets/experience/frame-0.webp","assets/experience/frame-1.webp","assets/experience/frame-2.webp","assets/experience/frame-3.webp","assets/experience/frame-4.webp","assets/experience/frame-5.webp","assets/experience/frame-6.webp","assets/experience/frame-7.webp","assets/experience/frame-8.webp","assets/experience/intro.css","assets/experience/smf.webp","capital-cloud.js","case-audit-core.js","case-audit-ui.js","catalogo.html","cot-archive-entry.mjs","cot-history-core.mjs","cot-history.css","cot-history.mjs","cot-indices-core.js","cot-week-watch-core.js","cot-week-watch-ui.js","data/cot-history-public.json","data/myfxbook-history.json","data/myfxbook-latest.json","dual24-core.js","dual24-ui.js","experience-entry.mjs","experience.mjs","feed-health-core.js","fonti.html","forex.html","icon.svg","impostazioni.html","impostazioni.js","insights-core.js","insights.css","insights.js","manifest.webmanifest","market-audit-core.js","market-audit-ui.js","mercati.html","nav.css","nav.js","price-core.js","price-status-core.js","price.css","price.js","resource-health.css","resource-health.js","retail-archive-core.mjs","retail-archive-entry.mjs","retail-archive.css","retail-archive.mjs","retail.css","retail.js","sentiment-core.js","sentiment-trend-core.js","sentiment-trend.css","sentiment-trend.js","sources.css","sources.js","splash-mascot.webp","splash.css","splash.js","squalincome-diagnostics.js","squalincome-freshness-core.js","statistica-squali-core.js","statistica-squali.html","statistica-squali.js","stato-prezzi.html","stato-prezzi.js","weekly-quality-core.js","weekly-quality-ui.js","index.html","sw.js"])
RUNTIME_CONFIG = "capital-cloud-config.js"
SHA = re.compile(r"^[0-9a-f]{40}$")

def resolve_owner_shell(root, url_path, legacy_resolver):
    """Exact allowlist, no traversal, no fallback if an active release is invalid."""
    root = Path(root).resolve()
    location = root / "local" / "remura-ui"
    active = location / "active"
    # An absent activation pointer deliberately retains the existing server.
    if not active.is_symlink() and not active.exists():
        return legacy_resolver(url_path)
    try:
        path = urlsplit(url_path).path
        name = "index.html" if path == "/" else path.removeprefix("/")
        if not path.startswith("/") or (name not in UI_PATHS and name != RUNTIME_CONFIG):
            return None
        releases = (location / "releases").resolve(strict=True)
        if not active.is_symlink():
            return None
        release = active.resolve(strict=True)
        if release.parent != releases or not SHA.fullmatch(release.name) or not release.is_dir():
            return None
        # Preserve original runtime config; never copy from release package.
        if name == RUNTIME_CONFIG:
            return legacy_resolver(url_path)
        candidate = release / name
        target = candidate.resolve(strict=True)
        if target != candidate or not target.is_file() or not target.is_relative_to(release):
            return None
        return target
    except (OSError, RuntimeError, ValueError):
        return None
