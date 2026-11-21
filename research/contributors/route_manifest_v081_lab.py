# REMURA Contributors v0.81 LAB — 21/11/2026 Europe/Rome.
# Static route/role/asset manifest only. NO network, tokens, runtime access or deployment.
"""Offline, fail-closed review of the pinned v0.78 private Worker routing contract."""
from __future__ import annotations
import json
from pathlib import Path
import re
import sys

from staging_source_lock_v079_lab import ROOT, verify_contract, SourceLockError

EXPECTED_ROUTES = {
    "/contributors/": ("contributors_recovery_v078_private_lab.html", "CONTRIBUTOR"),
    "/owner/": ("contributors_owner_recovery_v078_private_lab.html", "OWNER"),
    "/contributors/levels/": ("contributors_levels_v078_lab.html", "CONTRIBUTOR"),
    "/owner/levels/": ("owner_levels_v078_lab.html", "OWNER"),
}
EXPECTED_AREAS = {
    "RECOVERY": (
        "contributors_private_recovery_v076_lab.css", "recovery_portal_v072_lab.mjs",
        "secure_exit_v072_lab.mjs", "recovery_transport_v070_lab.mjs",
        "reconciliation_client_v065_lab.mjs", "amendment_client_v063_lab.mjs",
    ),
    "LEVELS": (
        "contributors_private_levels_v076_lab.css", "contributors_levels_ui_v076_lab.mjs",
        "contributors_candidate_client_v076_lab.mjs", "secure_exit_v072_lab.mjs",
        "owner_level_audit_ui_v077_lab.mjs", "owner_level_integrity_ui_v078_lab.mjs",
    ),
}
EXPECTED_API = {
    "READ_PATHS": (
        "/api/amendment/reconcile", "/api/amendment/mine",
        "/owner/amendment/reconcile-queue",
    ),
    "LEVEL_PATHS": (
        "/api/level-attempt/status", "/api/profile", "/api/catalog",
        "/api/receipts", "/owner/queue", "/owner/history", "/api/intent",
        "/api/submit", "/owner/review",
    ),
    "OWNER_AUDIT_PATHS": (
        "/owner/new-level/pending", "/owner/new-level/history",
        "/owner/new-level/audit-intent", "/owner/new-level/attest",
        "/owner/new-level/integrity",
    ),
}
OWNER_ONLY_ASSETS = frozenset({
    "owner_level_audit_ui_v077_lab.mjs", "owner_level_integrity_ui_v078_lab.mjs",
})
ROUTE_PATTERN = re.compile(r"'(/[^']+)':\s*\{file:'([^']+)',role:'([^']+)'\}")
STRING_PATTERN = re.compile(r"'([^']+)'")
MAX_SOURCE = 400_000

class ManifestError(ValueError):
    pass

def _block(source: str, pattern: str) -> str:
    m = re.search(pattern, source, re.S)
    if m is None:
        raise ManifestError("missing_contract_block")
    return m.group(1)

def _clean_residual(body: str, pattern: re.Pattern[str]) -> None:
    remainder = pattern.sub("", body)
    if remainder.strip(" \t\r\n,"):
        raise ManifestError("unexpected_contract_content")

def parse_routes(router: str) -> dict[str, tuple[str, str]]:
    body = _block(router, r"const ROUTE_CANDIDATES\s*=\s*Object\.freeze\(\{(.*?)\}\);")
    entries = ROUTE_PATTERN.findall(body)
    _clean_residual(body, ROUTE_PATTERN)
    if len(entries) != len(EXPECTED_ROUTES) or len({e[0] for e in entries}) != len(entries):
        raise ManifestError("route_duplicate_or_missing")
    result = {path: (file, role) for path, file, role in entries}
    if result != EXPECTED_ROUTES:
        raise ManifestError("route_role_file_drift")
    return result

def parse_string_list(body: str) -> tuple[str, ...]:
    values = tuple(STRING_PATTERN.findall(body))
    _clean_residual(body, STRING_PATTERN)
    if not values or len(values) != len(set(values)):
        raise ManifestError("empty_or_duplicate_items")
    return values

def parse_areas(router: str) -> dict[str, tuple[str, ...]]:
    areas = {
        name: parse_string_list(_block(router, rf"\b{name}:Object\.freeze\(\[([^\]]*)\]\)"))
        for name in EXPECTED_AREAS
    }
    if areas != EXPECTED_AREAS:
        raise ManifestError("area_asset_drift")
    if not OWNER_ONLY_ASSETS.issubset(set(areas["LEVELS"])):
        raise ManifestError("owner_assets_missing")
    # This restriction is enforced by the locked router; metadata alone cannot enforce it.
    if "match[1]!=='owner'" not in router or "'/owner/levels/'" not in router:
        raise ManifestError("owner_only_asset_guard_missing")
    return areas

def parse_api(router: str) -> dict[str, tuple[str, ...]]:
    found = {
        name: parse_string_list(_block(router, rf"\bconst {name}\s*=\s*new Set\(\[([^\]]*)\]\)"))
        for name in EXPECTED_API
    }
    if found != EXPECTED_API:
        raise ManifestError("api_allowlist_drift")
    paths = [path for group in found.values() for path in group]
    if len(set(paths)) != len(paths):
        raise ManifestError("api_allowlist_overlap")
    return found

def parse_asset_bundle(source: str, routes: dict, areas: dict) -> dict[str, str]:
    body = _block(source, r"export const privateAssetFilesV078=Object\.freeze\((\{.*\})\);\s*$")
    try:
        bundle = json.loads(body)
    except (TypeError, ValueError):
        raise ManifestError("asset_bundle_invalid_json") from None
    required = {name for name, role in routes.values()}
    required.update(file for files in areas.values() for file in files)
    if not isinstance(bundle, dict) or set(bundle) != required:
        raise ManifestError("bundle_missing_extra_assets")
    for route, (name, role) in routes.items():
        html = bundle[name]
        if not isinstance(html, str) or not html or len(html) > 120_000:
            raise ManifestError("bundle_invalid_page")
        if ('v0.78 LAB' not in html or '21/11/2026 16:56 CET' not in html
                or f'data-role="{role}"' not in html):
            raise ManifestError("page_version_or_role_drift")
    for name, value in bundle.items():
        if not isinstance(value, str) or not value or len(value) > 120_000:
            raise ManifestError("bundle_invalid_asset")
    return bundle

def review(root: Path = ROOT) -> dict[str, object]:
    if not isinstance(root, Path):
        raise ManifestError("invalid_root")
    try:
        locked = verify_contract(root=root)
        router_file = root / "research/contributors/private_worker_router_v078_lab.mjs"
        bundle_file = root / "research/contributors/private_assets_v078_lab.mjs"
        if router_file.stat().st_size > MAX_SOURCE or bundle_file.stat().st_size > MAX_SOURCE:
            raise ManifestError("oversized_source")
        router = router_file.read_text(encoding="utf-8")
        asset_source = bundle_file.read_text(encoding="utf-8")
        routes = parse_routes(router)
        areas = parse_areas(router)
        api = parse_api(router)
        bundle = parse_asset_bundle(asset_source, routes, areas)
    except (OSError, UnicodeError, SourceLockError) as exc:
        raise ManifestError("locked_source_unverifiable") from exc
    if locked.get("status") != "LAB_SOURCE_LOCK_MATCH":
        raise ManifestError("locked_source_unverified")
    return {
        "schema": "remura.contributors.route_manifest.v081.lab",
        "version": "0.81",
        "base_private_ui": "0.78",
        "pinned_source_files": 14,
        "pages": len(routes),
        "assets_including_pages": len(bundle),
        "api_allowlist_entries": sum(len(x) for x in api.values()),
        "route_roles": {route: role for route, (filename, role) in routes.items()},
        "source_status": "PINNED_GIT_BLOBS_MATCH",
        "runtime_policy_attested": False,
        "provider_access_attested": False,
        "decision": "NO_GO",
        "automatic_deploy_allowed": False,
        "requires_explicit_staging_authorization": True,
    }

def main(argv: list[str]) -> int:
    if argv != ["--check"]:
        print("REMURA_V081_MANIFEST=NO_GO_BAD_ARGUMENTS")
        return 2
    try:
        result = review()
    except ManifestError:
        print("REMURA_V081_MANIFEST=NO_GO_SOURCE_OR_CONTRACT_DRIFT")
        return 3
    print(json.dumps(result, sort_keys=True, ensure_ascii=True))
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
