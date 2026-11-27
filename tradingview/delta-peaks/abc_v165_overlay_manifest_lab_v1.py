# REMURA v0.8.134 LAB — 17/11/2026 CET
"""Combine verified ABC Python overlay and original C UI preview, memory only.
No deployment, live inventory, installer, persistent artifact or real release stamp.
"""
import hashlib,json
from abc_overlay_transaction_lab_v1 import manifest,valid_blob,need,sha
UI=("index.html","asset.html","mercati.html","forex.html","catalogo.html","statistica-squali.html","stato-prezzi.html","fonti.html","impostazioni.html","nav.js","sw.js")
SERVER_PIN="b70b82f6b2752536b5bbe8c6493072c4b5cff982da0f35124beb60779b92d4ab"
def combined_manifest(before,after,ui_before,ui_after,*,synthetic=False):
    need(synthetic is True and len(before)==3 and len(after)==79)
    backend=manifest(before,after)
    need(sha(after["scripts/private_server.py"])==SERVER_PIN)
    need(type(ui_before) is dict and type(ui_after) is dict and set(ui_before)==set(ui_after)==set(UI))
    need(all(valid_blob(v) for rows in (ui_before,ui_after) for v in rows.values()))
    need(all(ui_after[p]!=ui_before[p] for p in UI))
    need(all(ui_after[p].count(b"nav.js?v=165")==1 and b"nav.js?v=164" not in ui_after[p] for p in UI[:9]))
    need(ui_after["nav.js"].count(b"DATA_ORA_REALE_SOLO_AL_RILASCIO")==1)
    need(b"document.body.prepend(release)" in ui_after["nav.js"])
    need(b"remura-shell-v79-v1.65-storage-diagnostic" in ui_after["sw.js"] and b'url.pathname.includes("/private-api/")' in ui_after["sw.js"])
    rows=tuple(sorted((*backend,*((p,sha(ui_before[p]),sha(ui_after[p])) for p in UI))))
    need(len(rows)==90 and sum(x[1] is not None for x in rows)==14)
    report={"schema":"remura.abc.v165.overlay.preview.lab.v1","changed_paths":90,"existing_paths":14,"new_paths":76,"versioned_pages":9,
            "overlay_manifest_sha256":hashlib.sha256(json.dumps(rows,separators=(",",":")).encode()).hexdigest(),
            "real_install_stamp_verified":False,"full_distribution_manifest_verified":False,"live_baseline_verified":False,
            "installer_available":False,"restore_verified":False,"autoupdater_reconciled":False,"release_authorized":False}
    return rows,report
