#!/usr/bin/env python3
# REMURA v0.8.152 LAB — 18/11/2026, sessione successiva alle 11:13 CET
"""Verify owner attestation of the exact existing v1.65 candidate.
Nonprivileged offline LAB only. No installation, no maintenance approval.
"""
import argparse,hashlib,json,os,stat,subprocess,tempfile
from pathlib import Path
import abc_v165_stage_bundle_v1 as stage
import abc_prices_recovery_v2 as recovery

BUNDLE="6804531c819ec16af972755b042394ac5c9acee23b7c03f70a09ab765369cfcc"
BUNDLE_BYTES=1771520
SCHEMA="remura.release.candidate.attestation.v1"
def need(condition):
    if not condition:raise ValueError("RELEASE_ATTESTATION_GATE")
def statement():
    return stage.canonical({"schema":SCHEMA,"project":"REMURA","release":"1.65",
        "manifest_sha256":stage.PIN,"bundle_sha256":BUNDLE,"bundle_bytes":BUNDLE_BYTES,
        "scope":"155_application_files_candidate_only",
        "maintenance_authorized":False,"install_authorized":False})
def verify_attestation(keyring,signer,signature):
    need(os.geteuid()!=0)
    recovery.private_dir(keyring)
    secret=recovery.gpg(keyring,"--with-colons","--list-secret-keys",stdout=subprocess.PIPE).stdout
    need(not any(line.startswith((b"sec:",b"ssb:")) for line in secret.splitlines()))
    recovery.verify_signature(keyring,statement(),signature,signer)
    return {"schema":SCHEMA,"status":"OWNER_CANDIDATE_ATTESTATION_VERIFIED",
            "owner_signature_verified":True,"bundle_on_target_verified":False,
            "maintenance_authorized":False,"install_authorized":False}
def verify_bundle_attestation(path,keyring,signer,signature):
    result=verify_attestation(keyring,signer,signature)
    report=stage.inspect_bundle(path)
    need(report["bundle_sha256"]==BUNDLE and report["bundle_bytes"]==BUNDLE_BYTES)
    return {**result,"status":"OWNER_ATTESTED_CANDIDATE_BYTES_VERIFIED",
            "bundle_on_target_verified":True,
            "coherent_locked_snapshot":False}
def read_sig(path):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        s=os.fstat(fd)
        need(stat.S_ISREG(s.st_mode) and 0<s.st_size<=16384)
        with os.fdopen(os.dup(fd),"rb") as f:b=f.read(16385)
        z=os.fstat(fd)
        need(len(b)==s.st_size and (s.st_size,s.st_mtime_ns,s.st_ctime_ns)==(z.st_size,z.st_mtime_ns,z.st_ctime_ns))
        return b
    finally:os.close(fd)
def main():
    p=argparse.ArgumentParser(description=__doc__)
    g=p.add_mutually_exclusive_group(required=True)
    g.add_argument("--statement",action="store_true")
    g.add_argument("--verify",type=Path,metavar="SIGNATURE")
    p.add_argument("--keyring",type=Path);p.add_argument("--signer")
    p.add_argument("--bundle",type=Path)
    a=p.parse_args()
    try:
        need(os.geteuid()!=0)
        if a.statement:
            need(a.keyring is None and a.signer is None and a.bundle is None)
            # Exact bytes, deliberately no trailing newline.
            import sys
            sys.stdout.buffer.write(statement())
        else:
            need(a.keyring is not None and a.signer is not None)
            sig=read_sig(a.verify)
            result=(verify_bundle_attestation(a.bundle,a.keyring,a.signer,sig) if a.bundle
                    else verify_attestation(a.keyring,a.signer,sig))
            print(json.dumps(result,sort_keys=True))
    except (OSError,ValueError,subprocess.SubprocessError,TypeError,KeyError):
        print('{"status":"STOP_RELEASE_ATTESTATION","install_authorized":false}')
        return 2
    return 0
if __name__=="__main__":raise SystemExit(main())
