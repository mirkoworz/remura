# REMURA v0.8.137 LAB — 17/11/2026, sessione successiva alle 14:22 CET
"""Pinned repository-scope application manifest; not a deployable installer."""
import ast,hashlib,json,re
from abc_overlay_transaction_lab_v1 import need,valid_blob,sha,valid_path
from abc_dependency_inventory_lab_v1 import inspect
from abc_v165_overlay_manifest_lab_v1 import SERVER_PIN,UI
ASSET=re.compile(r"[A-Za-z0-9_-]+[.](?:html|js|css|webp|svg|webmanifest)\Z")
DEPLOY=re.compile(r"deploy/oracle/[A-Za-z0-9_.-]+\Z")
def assets(server):
    tree=ast.parse(server)
    matches=[n.value for n in tree.body if isinstance(n,ast.Assign) and
             any(isinstance(t,ast.Name) and t.id=="SAFE_ASSETS" for t in n.targets)]
    need(len(matches)==1)
    result=ast.literal_eval(matches[0])
    need(type(result) is set and all(type(p) is str and ASSET.fullmatch(p) for p in result))
    return result
def git_blob(b):return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def build(base,overlay,deploy,*,synthetic=False):
    need(synthetic is True and type(base) is dict and type(overlay) is dict and type(deploy) is dict)
    need(len(base)==79 and len(overlay)==90 and len(deploy)==28)
    need(all(valid_blob(b) for d in (base,overlay,deploy) for b in d.values()))
    need(all(valid_path(p) or ASSET.fullmatch(p) for d in (base,overlay) for p in d))
    need(all(DEPLOY.fullmatch(p) for p in deploy))
    need(not set(deploy)&(set(base)|set(overlay)))
    need(set(overlay)&set(base)==set(UI)|{"scripts/private_server.py","scripts/price_store.py","scripts/signals_monitor.py"})
    need(all(base[p]!=overlay[p] for p in set(base)&set(overlay)))
    full={**base,**overlay}
    server=full["scripts/private_server.py"]
    need(sha(server)==SERVER_PIN)
    ui={p for p in full if ASSET.fullmatch(p)}
    scripts={p:b for p,b in full.items() if valid_path(p)}
    need(len(ui)==54 and len(scripts)==101 and ui==assets(server))
    match=re.search(rb"const STATIC\s*=\s*(\[[^\n]+?\]);",full["sw.js"])
    need(match is not None)
    cache=json.loads(match.group(1))
    need(type(cache) is list and len(cache)==len(set(cache)) and "./" in cache)
    need(all(type(p) is str and p.startswith("./") for p in cache))
    need(set(p[2:] for p in cache if p!="./")==ui-{"sw.js"})
    need(full["nav.js"].count(b"DATA_ORA_REALE_SOLO_AL_RILASCIO")==1)
    graph=inspect(scripts,synthetic=True)
    startup=set(graph["startup_static"]);other=set(graph["other_service_reachable_static"])
    rows=[]
    for p,b in sorted(full.items()):
        kind="ui" if p in ui else "startup_static" if p in startup else "service_reachable_static" if p in other else "unclassified_retained"
        rows.append({"path":p,"category":kind,"operation":"add" if p not in base else "replace" if p in overlay else "retain",
                     "base_git_blob":git_blob(base[p]) if p in base else None,"candidate_sha256":sha(b),"bytes":len(b)})
    refs=[{"path":p,"git_blob":git_blob(b),"sha256":sha(b),"operation":"inventory_only"} for p,b in sorted(deploy.items())]
    data={"application":rows,"deployment_reference":refs}
    return {"schema":"remura.abc.v165.repository_manifest.lab.v1",**data,
            "manifest_sha256":sha(json.dumps(data,sort_keys=True,separators=(",",":")).encode()),
            "application_paths":len(rows),"changed_paths":len(overlay),
            "deployment_reference_paths":len(refs),"live_baseline_verified":False,
            "permissions_verified":False,"installed_dependencies_verified":False,
            "full_distribution_manifest_verified":False,"release_authorized":False}
