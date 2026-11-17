# REMURA v0.8.136 LAB — 17/11/2026, sessione 14:22 CET
"""Observe actual import-time dependencies in a fresh stdlib-only subprocess.
Diagnostic audit hooks are guardrails for reviewed source, not a security sandbox.
No main(), broker, DB, installer, deployment or claim of full runtime closure.
"""
import json,os,subprocess,sys,tempfile
from pathlib import Path
from abc_dependency_inventory_lab_v1 import inspect
from abc_overlay_transaction_lab_v1 import need

ROOTS=("private_server","ctrader_feed","cot_monitor","update_myfxbook","update_ig","update_capital","price_feed")
CHILD=r"""
import importlib,importlib.util,json,os,sys
from pathlib import Path
root=Path(sys.argv[1]).resolve()
name=sys.argv[2]
sys.path.insert(0,str(root/"scripts"))
def guard(event,args):
    if (event.startswith(("socket.","subprocess.","sqlite3.connect","ctypes.","os.exec","os.spawn","os.fork"))
        or event in ("os.system","os.remove","os.rename","os.mkdir","os.rmdir","os.chmod","os.chown","os.link","os.symlink","os.truncate","os.putenv","os.unsetenv","os.chdir","threading.Thread.start")):
        raise RuntimeError("LAB_SIDE_EFFECT_BLOCKED")
    if event=="open":
        flags=args[2]
        if isinstance(flags,int) and flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):
            raise RuntimeError("LAB_WRITE_BLOCKED")
sys.addaudithook(guard)
importlib.import_module(name)
local=[]
for mod in tuple(sys.modules.values()):
    path=getattr(mod,"__file__",None)
    if path:
        p=Path(path).resolve()
        if p.parent==root/"scripts" and p.suffix==".py":
            local.append("scripts/"+p.name)
print(json.dumps({"root":name,"observed":sorted(set(local)),
                  "sdk_discoverable":importlib.util.find_spec("ctrader_open_api") is not None}))
"""
def observe(files,*,synthetic=False,roots=ROOTS):
    need(synthetic is True)
    static=inspect(files,roots=roots,synthetic=True)
    rows=[]
    with tempfile.TemporaryDirectory(prefix="remura-import-lab-") as tmp:
        root=Path(tmp)
        (root/"scripts").mkdir()
        (root/"home").mkdir()
        for path,body in files.items():
            (root/path).write_bytes(body)
        env={"HOME":str(root/"home"),"LANG":"C.UTF-8"}
        for name in roots:
            result=subprocess.run([sys.executable,"-I","-S","-B","-c",CHILD,str(root),name],
                                  cwd=root,env=env,capture_output=True,text=True,timeout=15)
            need(result.returncode==0 and not result.stderr and len(result.stdout)<=32768)
            row=json.loads(result.stdout)
            need(row["root"]==name and row["sdk_discoverable"] is False)
            need(set(row["observed"])<=set(files) and "scripts/"+name+".py" in row["observed"])
            rows.append(row)
    seen=set().union(*(set(row["observed"]) for row in rows))
    reachable=set(static["startup_static"])|set(static["other_service_reachable_static"])
    return {"schema":"remura.abc.import_observation.lab.v1","entrypoints":rows,
            "observed_import_paths":sorted(seen),"observed_outside_static":sorted(seen-reachable),
            "static_only_not_observed":sorted(reachable-seen),
            "unclassified_retained":sorted(set(files)-seen-reachable),
            "source_inventory_pin":static["all_files_pin"],
            "sdk_installed_in_live_verified":False,"service_functions_executed":False,
            "dynamic_closure_verified":False,"safe_to_remove_unobserved":False,
            "release_authorized":False}
