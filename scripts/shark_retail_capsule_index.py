"""Track B: OFFLINE private index for ORIGINAL Squalincome/retail capsules.

Only explicitly created ZIPs within one 0700 local directory. Verifies
per-ZIP causality, cross-pack duplicate decision IDs, reused receipt
consistency, and an immutable hash-chained series of index generations.
A crash-left .tmp is a blocker, NEVER cleaned or skipped automatically.
No source database, live service, cloud, API, encryption, external
attestation, off-host backup, pruning, trading or cron support.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import zipfile

from scripts import shark_retail_evidence_capsule as capsule

SCHEMA="remura-track-b-retail-capsule-private-index-v1"
STATUS="LOCAL_PRIVATE_INDEX_NOT_BACKUP"
INDEX_RE=re.compile(r"retail-index-(\d{6})\.json\Z")
MAX_PACKS=512
MAX_INDEX_BYTES=512_000
MAX_GENERATIONS=512
HEX=re.compile(r"[0-9a-f]{64}\Z")


def _canon(data):
    return (json.dumps(data,sort_keys=True,separators=(",",":"),
                       ensure_ascii=True,allow_nan=False)+"\n").encode("ascii")


def _sha(path):
    digest=hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b""):
            digest.update(chunk)
    return digest.hexdigest()


def _discover(folder):
    folder=Path(folder)
    if (not folder.is_dir() or folder.is_symlink()
            or folder.stat().st_mode&0o077):
        raise ValueError("private_0700_directory_required")
    packs=[]
    indexes={}
    for child in folder.iterdir():
        name=child.name
        if (name.startswith(".remura-retail-") and name.endswith(".tmp")):
            raise ValueError("incomplete_private_capsule_staging_requires_review")
        match=INDEX_RE.fullmatch(name)
        if match:
            if child.is_symlink() or not child.is_file():
                raise ValueError("unsafe_index_entry")
            indexes[int(match.group(1))]=child
        if child.suffix==".zip":
            if child.is_symlink() or not child.is_file():
                raise ValueError("unsafe_capsule_entry")
            packs.append(child)
    if len(packs)>MAX_PACKS or len(indexes)>MAX_GENERATIONS:
        raise ValueError("private_index_capacity_exceeded")
    return folder,sorted(packs,key=lambda p:p.name),indexes


def _scan(packs):
    entries=[]
    decision_ids=set()
    receipt_hashes={}
    for path in packs:
        report=capsule.verify_archive(path)
        ids=[]
        with zipfile.ZipFile(path,"r") as zipped:
            with zipped.open(capsule.CAPSULES) as source:
                for line in source:
                    data=json.loads(line)
                    ident=data["history"]["id"]
                    if type(ident) is not int or ident<=0 or ident in decision_ids:
                        raise ValueError("duplicate_original_history_across_packs")
                    decision_ids.add(ident)
                    ids.append(ident)
                    receipt=data["receipt"]
                    if receipt is not None:
                        witness=receipt["id"]
                        values=_canon({"receipt":receipt,"features":data["features"]})
                        digest=hashlib.sha256(values).hexdigest()
                        existing=receipt_hashes.setdefault(witness,digest)
                        if existing!=digest:
                            raise ValueError("conflicting_reused_retail_receipt")
        if ids!=sorted(ids) or len(ids)!=report["originalDecisionsPreserved"]:
            raise ValueError("original_pack_order_or_count_invalid")
        entries.append({
            "name":path.name,
            "sha256":_sha(path),
            "fileBytes":path.stat().st_size,
            "count":len(ids),
            "minOriginalId":ids[0],
            "maxOriginalId":ids[-1],
            "idsSha256":hashlib.sha256(_canon(ids)).hexdigest(),
            "complete":report["completeLocalNumericLinks"],
            "unknown":report["retailUnknownPreserved"],
        })
    if not entries:
        raise ValueError("no_private_capsules_to_index")
    return entries


def _read(path):
    if (not path.is_file() or path.is_symlink()
            or path.stat().st_mode&0o077
            or path.stat().st_size>MAX_INDEX_BYTES):
        raise ValueError("private_index_file_unsafe")
    raw=path.read_bytes()
    if not raw.endswith(b"\n"):
        raise ValueError("private_index_noncanonical")
    try:
        doc=json.loads(raw)
    except (ValueError,UnicodeError) as err:
        raise ValueError("private_index_invalid_json") from err
    if (type(doc) is not dict or set(doc)!={
            "schema","status","generation","entries","entriesSha256",
            "previousSha256","sourceDeleted","liveAuthorized",
            "externallySigned"}
            or doc["schema"]!=SCHEMA or doc["status"]!=STATUS
            or type(doc["generation"]) is not int
            or not 1<=doc["generation"]<=MAX_GENERATIONS
            or doc["sourceDeleted"] is not False
            or doc["liveAuthorized"] is not False
            or doc["externallySigned"] is not False
            or type(doc["entries"]) is not list
            or not 1<=len(doc["entries"])<=MAX_PACKS
            or hashlib.sha256(_canon(doc["entries"])).hexdigest()
               !=doc["entriesSha256"]):
        raise ValueError("invalid_private_index_manifest")
    for e in doc["entries"]:
        if (type(e) is not dict or set(e)!={
                "name","sha256","fileBytes","count","minOriginalId",
                "maxOriginalId","idsSha256","complete","unknown"}
                or type(e["name"]) is not str
                or Path(e["name"]).name!=e["name"]
                or not e["name"].endswith(".zip")
                or any(type(e[k]) is not int or e[k]<0 for k in (
                    "fileBytes","count","minOriginalId","maxOriginalId",
                    "complete","unknown"))
                or e["count"]<1 or e["minOriginalId"]<1
                or e["maxOriginalId"]<e["minOriginalId"]
                or e["count"]!=e["complete"]+e["unknown"]
                or not HEX.fullmatch(e["sha256"])
                or not HEX.fullmatch(e["idsSha256"])):
            raise ValueError("invalid_private_index_entry")
    names=[e["name"] for e in doc["entries"]]
    if names!=sorted(set(names)):
        raise ValueError("duplicate_or_unsorted_indexed_pack")
    return doc


def _validate_chain(indexes,entries,*,strict):
    if not indexes:
        if strict:
            raise ValueError("no_published_capsule_index")
        return None
    generations=sorted(indexes)
    if generations!=list(range(1,max(generations)+1)):
        raise ValueError("missing_index_generation")
    inventory={e["name"]:e for e in entries}
    last=None
    for generation in generations:
        path=indexes[generation]
        doc=_read(path)
        if (doc["generation"]!=generation or
                doc["previousSha256"]!=(
                    None if last is None else _sha(last))):
            raise ValueError("index_sha256_chain_broken")
        for entry in doc["entries"]:
            if inventory.get(entry["name"])!=entry:
                raise ValueError("indexed_original_capsule_missing_or_changed")
        if last is not None:
            before={e["name"]:e for e in _read(last)["entries"]}
            after={e["name"]:e for e in doc["entries"]}
            if (len(after)<=len(before) or any(
                    after.get(name)!=val for name,val in before.items())):
                raise ValueError("immutable_index_generation_rewritten")
        last=path
    if strict and _read(last)["entries"]!=entries:
        raise ValueError("new_capsule_not_in_published_index")
    return last


def verify_latest(private_dir):
    """Strict read-only verification: ALL ZIPs must be indexed."""
    folder,packs,indexes=_discover(private_dir)
    entries=_scan(packs)
    last=_validate_chain(indexes,entries,strict=True)
    return {
        "schema":SCHEMA,
        "status":"OFFLINE_PRIVATE_INDEX_VERIFIED_NOT_LIVE_GO",
        "generation":_read(last)["generation"],
        "packs":len(entries),
        "originalDecisions":sum(e["count"] for e in entries),
        "completeRetail":sum(e["complete"] for e in entries),
        "unknownRetail":sum(e["unknown"] for e in entries),
        "compressedBytes":sum(e["fileBytes"] for e in entries),
        "crossPackDuplicatesRejected":True,
        "notAnExternalTimestampOrSignature":True,
        "unobservedGapsNotCertified":True,
        "automaticPruningAuthorized":False,
        "offHostRestoreVerified":False,
        "liveAuthorized":False,
        "newAPICalls":0,
        "edgeEstablished":False,
    }


def publish_next(private_dir):
    """Manual-only atomic no-clobber append of a complete catalog snapshot."""
    folder,packs,indexes=_discover(private_dir)
    entries=_scan(packs)
    last=_validate_chain(indexes,entries,strict=False)
    if last is not None and len(_read(last)["entries"])>=len(entries):
        raise ValueError("no_new_capsule_to_index")
    generation=max(indexes,default=0)+1
    if generation>MAX_GENERATIONS:
        raise ValueError("index_generation_capacity_reached")
    target=folder/f"retail-index-{generation:06d}.json"
    if target.exists() or target.is_symlink():
        raise FileExistsError("index_generation_must_not_overwrite")
    doc={
        "schema":SCHEMA,"status":STATUS,"generation":generation,
        "entries":entries,
        "entriesSha256":hashlib.sha256(_canon(entries)).hexdigest(),
        "previousSha256":None if last is None else _sha(last),
        "sourceDeleted":False,"liveAuthorized":False,
        "externallySigned":False
    }
    blob=_canon(doc)
    if len(blob)>MAX_INDEX_BYTES:
        raise ValueError("index_manifest_capacity_exceeded")
    fd,filename=tempfile.mkstemp(prefix=".remura-retail-index-",
                                 suffix=".tmp",dir=str(folder))
    temp=Path(filename)
    try:
        os.fchmod(fd,0o600)
        with os.fdopen(fd,"wb") as f:
            f.write(blob)
            f.flush()
            os.fsync(f.fileno())
        os.link(temp,target)
    finally:
        temp.unlink(missing_ok=True)
    return verify_latest(folder)
