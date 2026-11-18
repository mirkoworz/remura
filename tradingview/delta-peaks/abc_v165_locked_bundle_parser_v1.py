# REMURA v0.8.160 LAB — 18/11/2026, sessione successiva alle 13:29 CET
"""Independent byte-only adapter, retaining exact historic portable source.
No path access, install or privileged execution.
"""
import io,json,tarfile
from abc_v165_stage_bundle_v1 import SCHEMA,need,sha,canonical,rows,put
from abc_v165_locked_snapshot_v1 import BUNDLE_BYTES,BUNDLE_SHA256

def inspect_bundle_bytes(b):
    """Parse exactly the immutable supplied bytes; never reopen a path."""
    need(type(b) is bytes and len(b)==BUNDLE_BYTES and sha(b)==BUNDLE_SHA256)
    app={}
    with tarfile.open(fileobj=io.BytesIO(b),mode="r:") as t:
        items=t.getmembers()
        need(len(items)==156 and items[0].name=="MANIFEST.json")
        need(all(m.type==tarfile.REGTYPE and m.mode==0o644 and m.uid==m.gid==m.mtime==0 and not m.pax_headers for m in items))
        raw=t.extractfile(items[0]).read()
        d=json.loads(raw);need(raw==canonical(d))
        expected=rows(d)
        need([m.name for m in items[1:]]==["app/"+n for n in expected])
        for m in items[1:]:
            r=expected[m.name[4:]]
            data=t.extractfile(m).read()
            need(m.size==r["bytes"] and len(data)==r["bytes"] and sha(data)==r["candidate_sha256"])
            app[m.name[4:]]=data
        # Reject appended bytes, noncanonical headers, alternate tar encodings.
        rebuilt=io.BytesIO()
        with tarfile.open(fileobj=rebuilt,mode="w",format=tarfile.USTAR_FORMAT) as out:
            for m in items:put(out,m.name,t.extractfile(m).read())
        need(rebuilt.getvalue()==b)
    return {"schema":SCHEMA,"bundle_sha256":sha(b),"bundle_bytes":len(b),
            "application_paths":155,"deployment_reference_only":28,
            "installable":False,"release_authorized":False},d,app
