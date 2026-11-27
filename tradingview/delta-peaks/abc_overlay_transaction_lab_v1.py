# REMURA v0.8.132 LAB — 17/11/2026 CET
"""Offline ABC Python overlay transaction rehearsal, never a release installer.
Only in-memory byte maps; no target paths, subprocess, services or database.
"""
import hashlib
from pathlib import PurePosixPath
MAX_FILES=100
MAX_BYTES=16*1024*1024
def need(ok):
    if not ok:raise ValueError("ABC_BUNDLE_DENIED")
def sha(b):return hashlib.sha256(b).hexdigest()
def valid_path(p):
    return type(p) is str and len(p)<=200 and p.startswith("scripts/") and p.endswith(".py") and len(PurePosixPath(p).parts)==2 and str(PurePosixPath(p))==p and not p.split("/")[1].startswith(".")
def valid_blob(b):return type(b) is bytes and 0<len(b)<=2*1024*1024
def manifest(original,candidate):
    need(type(original) is dict and type(candidate) is dict and 1<=len(candidate)<=MAX_FILES)
    need(set(original)<=set(candidate))
    need(all(valid_path(p) and valid_blob(b) for rows in (original,candidate) for p,b in rows.items()))
    need(sum(map(len,candidate.values()))<=MAX_BYTES and sum(map(len,original.values()))<=MAX_BYTES)
    return tuple((p,sha(original[p]) if p in original else None,sha(candidate[p])) for p in sorted(candidate))
def rehearse(original,candidate,expected,*,fail_after=None,synthetic=False):
    need(synthetic is True)
    actual=manifest(original,candidate);need(type(expected) is tuple and expected==actual)
    need(fail_after is None or (type(fail_after) is int and 0<=fail_after<=len(actual)))
    target=dict(original);backup=dict(original)
    for index,(p,before,after) in enumerate(actual):
        if fail_after==index:break
        need((sha(target[p]) if p in target else None)==before)
        target[p]=candidate[p];need(sha(target[p])==after)
    if fail_after is not None:
        for p,before,_ in actual:
            if before is None:target.pop(p,None)
            else:target[p]=backup[p]
        need(target==original)
        return {"status":"SYNTHETIC_ROLLBACK_VERIFIED","restored":len(original),"added_removed":len(candidate)-len(original),"release_authorized":False}
    need(target==candidate)
    return {"status":"SYNTHETIC_OVERLAY_VERIFIED","files":len(candidate),"release_authorized":False}
