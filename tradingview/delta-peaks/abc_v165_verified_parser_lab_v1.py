"""REMURA v0.8.168 LAB — 18/11/2026, sessione successiva alle 16:21 CET.
Load exact reviewed source snapshots in a disposable LAB process only.
No candidate import from disk, sys.path edits, live CLI or root authorization.
This is not a sandbox: trust Python, stdlib and this verifier independently.
"""
import builtins
from types import ModuleType
from abc_v165_bootstrap_source_gate_v1 import verify_sources, PINS

ORDER=("abc_v165_start_guard_v1","abc_v165_locked_snapshot_v1",
       "abc_v165_stage_bundle_v1","abc_v165_locked_bundle_parser_v1")
STDLIB=frozenset(("os","stat","sys","pathlib","fcntl","hashlib","contextlib",
                    "argparse","io","json","re","tarfile","tempfile"))

def verified_parser(anchor,parts,uid,*,synthetic=False):
    if synthetic is not True:
        raise ValueError("LAB_ONLY")
    raw=verify_sources(anchor,parts,uid)
    if set(raw)!=set(PINS):
        raise ValueError("SOURCE_SET")
    modules={}
    original=builtins.__import__
    def local_import(name,globals=None,locals=None,fromlist=(),level=0):
        if level==0 and name in modules and fromlist:
            return modules[name]
        if level==0 and name in STDLIB:
            return original(name,globals,locals,fromlist,level)
        raise ImportError("UNREVIEWED_DIRECT_IMPORT")
    for name in ORDER:
        module=ModuleType(name)
        module.__dict__["__builtins__"]=dict(vars(builtins),__import__=local_import)
        exec(compile(raw[name+".py"],"<verified:"+name+">","exec",
                     dont_inherit=True),module.__dict__)
        modules[name]=module
    # Do not expose the stage builder, CLI or candidate startup guard.
    return modules[ORDER[-1]].inspect_bundle_bytes
