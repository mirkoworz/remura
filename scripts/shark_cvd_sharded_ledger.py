"""Track B OFFLINE: bounded, non-destructive private CVD scan SQLite shards.

Optional prototype ONLY: not used by the server, scheduler or existing recorder.
A full immutable scan-attempt table is sealed locally, not pruned, before a
new SQLite shard accepts later ORIGINAL real-time observations. Each shard
retains the original v2 scan schema, including its session_prefix_hmac.
Sealed SQLite bytes are hashed and linked locally; no external attestation.
A full/shut-down period or absent slot remains UNKNOWN, never a CVD negative.

Requires a pre-existing private 0700 directory. No network, no secrets stored,
no broker API, no LIVE migration, no automatic deletion, no restore on VPS.
SQLite rollover is NOT one atomic multi-file transaction. An interrupted
transition can require manual recovery; no gap is retroactively filled.
"""
from __future__ import annotations

from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import tempfile
from urllib.parse import quote

from scripts import shark_cvd_scan_coverage as scan
from scripts import shark_cot_asof_witness as witness

SCHEMA="remura-private-cvd-scan-shards-v1"
META="research_cvd_shard_metadata"
META_TRIGGERS=("research_cvd_shard_meta_no_update",
               "research_cvd_shard_meta_no_delete")
SEAL_TRIGGER="research_cvd_shard_sealed_no_insert"
NAME=re.compile(r"^scan-(\d{6})\.sqlite3$")
HEX=re.compile(r"^[0-9a-f]{64}$")
PER_SHARD=scan.MAX_ROWS
MAX_SHARDS=64
MAX_SHARD_FILE_BYTES=64_000_000
MAX_SEAL_BYTES=2000


def _root(root):
    path=Path(root)
    if (path.is_symlink() or not path.is_dir()
            or stat.S_IMODE(path.stat().st_mode)&0o077):
        raise ValueError("private_0700_existing_directory_required")
    return path


def _name(index):
    return f"scan-{index:06d}.sqlite3"


def _seal_name(index):
    return f"scan-{index:06d}.seal.json"


@contextmanager
def _exclusive(root):
    folder=_root(root)
    flags=os.O_CREAT|os.O_RDWR|getattr(os,"O_NOFOLLOW",0)
    fd=os.open(folder/".cvd-shards.lock",flags,0o600)
    try:
        if stat.S_IMODE(os.fstat(fd).st_mode)&0o077:
            raise ValueError("cvd_shard_lock_permissions_unsafe")
        try:
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError("cvd_shard_writer_busy") from exc
        yield folder
    finally:
        os.close(fd)


def _digest(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size>MAX_SHARD_FILE_BYTES:
        raise ValueError("cvd_shard_file_untrusted_or_oversized")
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):
            h.update(block)
    return h.hexdigest()


def _readonly(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError("cvd_shard_missing_or_symlink")
    return sqlite3.connect("file:"+quote(str(path.resolve()),safe="/")+"?mode=ro",
                           uri=True,timeout=2)


def _metadata(db):
    row=db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                   (META,)).fetchone()
    if not row:
        raise ValueError("cvd_shard_metadata_missing")
    have={x[0] for x in db.execute(
        "SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name=?",
        (META,))}
    if not set(META_TRIGGERS).issubset(have):
        raise ValueError("cvd_shard_metadata_immutability_missing")
    rows=db.execute(f"SELECT seq,previous_sha256,row_cap,schema_version FROM {META} LIMIT 2").fetchall()
    if len(rows)!=1:
        raise ValueError("cvd_shard_metadata_not_unique")
    seq,previous,cap,version=rows[0]
    if version!=SCHEMA or cap!=PER_SHARD or type(seq) is not int:
        raise ValueError("cvd_shard_metadata_version_or_cap_mismatch")
    if previous is not None and (not isinstance(previous,str) or not HEX.fullmatch(previous)):
        raise ValueError("cvd_shard_previous_hash_invalid")
    return seq,previous


def _inspect(root, *, allow_pending_latest_seal=False, ignore_unpublished=False):
    if not ignore_unpublished and any(
            p.name.startswith(".cvd-init-") for p in root.iterdir()):
        raise ValueError("cvd_shard_unpublished_initialization_requires_recovery")
    names={}
    for p in root.iterdir():
        if p.name.startswith("scan-") and p.name.endswith(".sqlite3"):
            if p.is_symlink():
                raise ValueError("cvd_shard_symlink_forbidden")
            match=NAME.fullmatch(p.name)
            if not match:
                raise ValueError("cvd_shard_filename_invalid")
            seq=int(match[1])
            names[seq]=p
    if not names:
        if any(p.name.endswith(".seal.json") for p in root.iterdir()):
            raise ValueError("orphan_cvd_shard_seal")
        return [],{},0,None
    indexes=sorted(names)
    if indexes!=list(range(1,len(indexes)+1)) or len(indexes)>MAX_SHARDS:
        raise ValueError("cvd_shard_sequence_gap_or_limit")
    last_by_market={}
    segments=[]
    previous_seal=None
    total=0
    for seq in indexes:
        path=names[seq]
        if path.stat().st_size>MAX_SHARD_FILE_BYTES:
            raise ValueError("cvd_shard_size_limit")
        # With DELETE journal there must be no unresolved WAL carrying
        # extra writes that are not part of the hashed sealed DB file.
        if (Path(str(path)+"-wal").exists() or
                Path(str(path)+"-shm").exists()):
            raise ValueError("cvd_shard_wal_not_certified")
        with _readonly(path) as db:
            db.execute("PRAGMA query_only=ON")
            if db.execute("PRAGMA integrity_check").fetchone()[0]!="ok":
                raise ValueError("cvd_shard_integrity_check_failed")
            if not scan._protected(db):
                raise ValueError("cvd_scan_schema_missing")
            meta_seq,prev=_metadata(db)
            if meta_seq!=seq or prev!=previous_seal:
                raise ValueError("cvd_shard_hash_chain_broken")
            if db.execute("PRAGMA journal_mode").fetchone()[0]!="delete":
                raise ValueError("cvd_shard_journal_mode_unsafe")
            count=db.execute(f"SELECT count(*) FROM {scan.TABLE}").fetchone()[0]
            if not 0<=count<=PER_SHARD:
                raise ValueError("cvd_shard_capacity_corrupt")
            sealed=bool(db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='trigger' AND name=?",
                (SEAL_TRIGGER,)).fetchone())
            if seq!=indexes[-1] and not sealed:
                raise ValueError("cvd_shard_older_segment_unsealed")
            if sealed and count!=PER_SHARD:
                raise ValueError("cvd_shard_incomplete_seal")
            rows=db.execute(
                f"SELECT symbol,closed_at,attempted_at,state,source_hmac,"
                f"session_prefix_hmac,new_confirmations,reason,schema_version "
                f"FROM {scan.TABLE} ORDER BY closed_at,symbol")
            for symbol,closed,attempted,state,mac,prefix,count_new,reason,version in rows:
                at=witness._parse(closed)
                seen=witness._parse(attempted)
                if (symbol not in scan.PILOT or version!=scan.SCHEMA
                        or witness._iso(at)!=closed
                        or witness._iso(seen)!=attempted
                        or not at<=seen<=at+scan.GRACE
                        or (symbol in last_by_market and
                            at<=last_by_market[symbol])):
                    raise ValueError("cvd_shard_attempt_timestamps_or_order_corrupt")
                if state=="EVALUATED":
                    if (reason!="DETECTOR_OK" or type(count_new) is not int
                            or count_new<0 or not isinstance(mac,str)
                            or not HEX.fullmatch(mac)
                            or (prefix is not None and
                                (not isinstance(prefix,str) or not HEX.fullmatch(prefix)))):
                        raise ValueError("cvd_shard_evaluated_proof_corrupt")
                elif (state!="NOT_EVALUABLE" or count_new is not None
                      or prefix is not None or reason not in (
                          "SOURCE_ABSENT","DATA_INVALID","DATA_MISSING",
                          "DATA_STALE","DATA_PARTIAL","DATA_INSUFFICIENT")
                      or (mac is not None and
                          (not isinstance(mac,str) or not HEX.fullmatch(mac)))):
                    raise ValueError("cvd_shard_unknown_proof_corrupt")
                last_by_market[symbol]=at
        marker=root/_seal_name(seq)
        if marker.exists() or marker.is_symlink():
            if marker.is_symlink() or marker.stat().st_size>MAX_SEAL_BYTES:
                raise ValueError("cvd_shard_seal_file_invalid")
            try:
                doc=json.loads(marker.read_bytes())
            except (OSError,ValueError) as exc:
                raise ValueError("cvd_shard_seal_unreadable") from exc
            if (not sealed or set(doc)!={"schema","sequence","filename",
                                          "sha256","rows","previousSha256"}
                    or doc["schema"]!=SCHEMA or doc["sequence"]!=seq
                    or doc["filename"]!=path.name or doc["rows"]!=count
                    or doc["previousSha256"]!=prev or
                    not isinstance(doc["sha256"],str)
                    or not HEX.fullmatch(doc["sha256"])):
                raise ValueError("cvd_shard_seal_metadata_mismatch")
            if _digest(path)!=doc["sha256"]:
                raise ValueError("cvd_shard_sealed_bytes_changed")
            previous_seal=doc["sha256"]
        elif sealed and seq==indexes[-1] and allow_pending_latest_seal:
            # Crash after durable seal trigger, before its local manifest.
            # Only an EXPLICIT recovery may publish today's file hash.
            previous_seal=None
        elif sealed or seq!=indexes[-1]:
            raise ValueError("cvd_shard_seal_missing_fail_closed")
        else:
            previous_seal=None
        total+=count
        segments.append((seq,count,sealed))
    return segments,last_by_market,total,previous_seal


def _fsync_dir(folder):
    fd=os.open(folder,os.O_RDONLY|getattr(os,"O_DIRECTORY",0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _create(root,seq,previous):
    """Build a validated *unpublished* SQLite and no-clobber link it last.

    SIGKILL before os.link leaves no visible scan-NNNNNN database; a .cvd-init-
    temporary file may remain and must be explicitly recovered, not ignored.
    """
    if not 1<=seq<=MAX_SHARDS:
        raise ValueError("cvd_shard_sequence_capacity_reached")
    path=root/_name(seq)
    if path.exists() or path.is_symlink():
        raise FileExistsError("cvd_shard_never_overwrite")
    fd,temp=tempfile.mkstemp(prefix=".cvd-init-",suffix=".sqlite3",dir=root)
    staged=Path(temp)
    try:
        os.fchmod(fd,0o600)
        os.close(fd)
        fd=None
        with sqlite3.connect(staged,timeout=2) as db:
            if db.execute("PRAGMA journal_mode=DELETE").fetchone()[0]!="delete":
                raise ValueError("cvd_shard_delete_journal_required")
            db.execute("PRAGMA synchronous=FULL")
            scan.ensure_schema(db)
            with db:
                db.execute(f"""CREATE TABLE {META} (
                    seq INTEGER PRIMARY KEY,
                    previous_sha256 TEXT,
                    row_cap INTEGER NOT NULL,
                    schema_version TEXT NOT NULL
                )""")
                db.execute(f"INSERT INTO {META} VALUES (?,?,?,?)",
                           (seq,previous,PER_SHARD,SCHEMA))
                for op,name in zip(("UPDATE","DELETE"),META_TRIGGERS):
                    db.execute(f"""CREATE TRIGGER {name} BEFORE {op} ON {META}
                        BEGIN SELECT RAISE(ABORT,'immutable_shard_metadata'); END""")
            if db.execute("PRAGMA integrity_check").fetchone()[0]!="ok":
                raise ValueError("cvd_shard_unpublished_integrity_check_failed")
            if not scan._protected(db) or _metadata(db)!=(seq,previous):
                raise ValueError("cvd_shard_unpublished_metadata_invalid")
            if db.execute(f"SELECT count(*) FROM {scan.TABLE}").fetchone()[0]!=0:
                raise ValueError("cvd_shard_unpublished_not_empty")
        with staged.open("rb") as stream:
            os.fsync(stream.fileno())
        os.link(staged,path)  # atomic no-clobber publication
        _fsync_dir(root)
        return path
    finally:
        if fd is not None:
            os.close(fd)
        # Cleanup only *our own temporary initialization metadata*, never
        # actual scan attempts. SIGKILL may leave it: explicit recovery only.
        staged.unlink(missing_ok=True)


def _publish(root,path,payload):
    raw=(json.dumps(payload,sort_keys=True,separators=(",",":"),
                    ensure_ascii=True)+"\n").encode("ascii")
    fd,name=tempfile.mkstemp(prefix=".cvd-seal-",dir=root)
    tmp=Path(name)
    try:
        os.fchmod(fd,0o600)
        with os.fdopen(fd,"wb") as f:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
        os.link(tmp,path)  # no-clobber, never replace prior seal
    finally:
        tmp.unlink(missing_ok=True)
    parentfd=os.open(root,os.O_RDONLY|getattr(os,"O_DIRECTORY",0))
    try:
        os.fsync(parentfd)
    finally:
        os.close(parentfd)


def _seal(root,seq):
    path=root/_name(seq)
    with sqlite3.connect(path,timeout=2) as db:
        if db.execute(f"SELECT count(*) FROM {scan.TABLE}").fetchone()[0]!=PER_SHARD:
            raise ValueError("cvd_shard_not_full_cannot_seal")
        _,previous=_metadata(db)
        with db:
            db.execute(f"""CREATE TRIGGER IF NOT EXISTS {SEAL_TRIGGER}
                BEFORE INSERT ON {scan.TABLE}
                BEGIN SELECT RAISE(ABORT,'sealed_shard'); END""")
    digest=_digest(path)
    _publish(root,root/_seal_name(seq),{
        "schema":SCHEMA,"sequence":seq,"filename":path.name,
        "sha256":digest,"rows":PER_SHARD,"previousSha256":previous
    })
    return digest


def recover_interrupted_rollover(root, *, acknowledge=False):
    """EXPLICIT, conservative local-only recovery; never invents attempts.

    It can finish the last shard seal if its trigger and full scan rows are
    already durable. It can retain an unpublished initialization artifact
    with ZERO proven scan records under a new forensic filename, then allow
    a new initialization later. Anything ambiguous stays fail-closed.
    This does NOT repair hot journals, tampered historical seals or OCI data.
    """
    if acknowledge is not True:
        raise ValueError("explicit_recovery_acknowledgement_required")
    with _exclusive(root) as folder:
        staged=sorted(p for p in folder.iterdir()
                      if p.name.startswith(".cvd-init-"))
        if len(staged)>1:
            raise ValueError("multiple_unpublished_initializations_manual_review")
        for p in staged:
            if (p.is_symlink() or not p.is_file()
                    or stat.S_IMODE(p.stat().st_mode)&0o077
                    or p.stat().st_size>MAX_SHARD_FILE_BYTES):
                raise ValueError("unpublished_initialization_untrusted")
            if p.stat().st_size:
                with _readonly(p) as db:
                    if db.execute("PRAGMA integrity_check").fetchone()[0]!="ok":
                        raise ValueError("unpublished_initialization_corrupt")
                    if not scan._protected(db):
                        raise ValueError("unpublished_initialization_incomplete")
                    _metadata(db)
                    if db.execute(f"SELECT count(*) FROM {scan.TABLE}").fetchone()[0]!=0:
                        raise ValueError("unpublished_initialization_contains_scans")
            # Zero bytes or fully-formed empty SQLite: the staged file can
            # never have been used for record(); preserve it for forensics.
        segments,_,_,_=_inspect(
            folder,allow_pending_latest_seal=True,ignore_unpublished=True)
        for p in staged:
            retained=folder/("unpublished-retained-"+p.name[1:])
            os.link(p,retained)  # fail if evidence is already retained
            os.unlink(p)
        if staged:
            _fsync_dir(folder)
        if not segments:
            return {
                "status":"EMPTY_INITIALIZATION_RETAINED" if staged else "NOTHING_TO_RECOVER",
                "retainedUnpublishedFiles":len(staged),
                "sourceRowsDeleted":0,"attemptsReconstructed":0,
                "completeExternalAttestation":False,
            }
        seq,rows,sealed=segments[-1]
        marker=folder/_seal_name(seq)
        if sealed and not marker.exists() and not marker.is_symlink():
            # Same protected SQLite as before crash; the newly generated
            # SHA is from *recovery time*, not an earlier notarized hash.
            if rows!=PER_SHARD:
                raise ValueError("pending_seal_has_wrong_row_count")
            _seal(folder,seq)
            result="LAST_FULL_SHARD_SEAL_REPAIRED_LOCAL_ONLY"
        elif staged:
            result="UNPUBLISHED_EMPTY_INITIALIZATION_RETAINED"
        else:
            result="NOTHING_TO_RECOVER"
        _inspect(folder)
        return {
            "status":result,"retainedUnpublishedFiles":len(staged),
            "sourceRowsDeleted":0,"attemptsReconstructed":0,
            "completeExternalAttestation":False,
        }


def _report(segments,total):
    used=len(segments)
    last_rows=segments[-1][1] if segments else None
    return {
        "schema":SCHEMA,
        "status":("NO_SHARD_YET" if not segments else
                  "AT_GLOBAL_SHARD_LIMIT" if used==MAX_SHARDS and last_rows==PER_SHARD
                  else "LOCAL_SHARDED_LEDGER_ONLY"),
        "segments":used,
        "sealedSegments":sum(1 for _,_,sealed in segments if sealed),
        "totalObservedAttempts":total,
        "activeSegmentRows":last_rows,
        "maxRowsPerShard":PER_SHARD,
        "maxShards":MAX_SHARDS,
        "remainingTotalRows":MAX_SHARDS*PER_SHARD-total,
        "sourceRowsDeleted":0,
        "hasIndependentSignatureOrTimestamp":False,
        "missingCalendarSlotsRemainUnknown":True,
        "isCompleteOCIBackup":False,
        "liveDiskQuotaOrBillingVerified":False,
        "readyForVpsDeployment":False,
        "brokerCalls":0,"alertsEnabled":False,"ordersEnabled":False,
        "tradingEdgeEstablished":False,
    }


def verify(root):
    """Read-only validation of all segments, local byte-chain and capacity."""
    with _exclusive(root) as folder:
        segments,_,total,_=_inspect(folder)
        return _report(segments,total)


def record(root, *, symbol, slot_closed_at, source_document, secret, clock=None):
    """Explicit offline opt-in; append only CURRENT attempts, rolling at cap.

    Serializes this API via flock. A missing scan at crash/rollover is never
    fabricated on restart. External processes must not bypass this API.
    """
    closed=witness._parse(slot_closed_at)
    now=witness._clock(clock)
    if (symbol not in scan.PILOT or closed.second or closed.microsecond
            or closed.minute%15 or not closed<=now<=closed+scan.GRACE):
        raise ValueError("not_a_current_closed_m15_attempt")
    with _exclusive(root) as folder:
        segments,last_by_market,total,previous=_inspect(folder)
        if symbol in last_by_market and closed<=last_by_market[symbol]:
            raise ValueError("duplicate_or_backfilled_scan_across_shards")
        if not segments:
            path=_create(folder,1,None)
        else:
            seq,rows,sealed=segments[-1]
            if sealed or rows==PER_SHARD:
                if seq>=MAX_SHARDS:
                    raise ValueError("cvd_shard_sequence_capacity_reached")
                if not sealed:
                    previous=_seal(folder,seq)
                path=_create(folder,seq+1,previous)
            else:
                path=folder/_name(seq)
        with sqlite3.connect(path,timeout=2) as db:
            return scan.record(db,symbol=symbol,slot_closed_at=slot_closed_at,
                               source_document=source_document,
                               secret=secret,clock=now)
