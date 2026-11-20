# REMURA v0.8.135 LAB — 17/11/2026 13:17 CET
"""Conservative static Python dependency graph, not a production install list."""
import ast,re,sys,hashlib,json
from collections import deque
from abc_overlay_transaction_lab_v1 import need,valid_path,valid_blob
ROOTS=("private_server","ctrader_feed","update_myfxbook","update_ig","update_capital")
NAME=re.compile(r"[A-Za-z_][A-Za-z_0-9]*\Z")
def inspect(files,*,roots=ROOTS,synthetic=False):
    need(synthetic is True and type(files) is dict and 1<=len(files)<=150)
    need(all(valid_path(p) and valid_blob(b) for p,b in files.items()))
    need(sum(map(len,files.values()))<=16*1024*1024)
    modules={p[8:-3]:ast.parse(b,filename=p) for p,b in files.items()}
    need(all(NAME.fullmatch(n) for n in modules))
    need(type(roots) is tuple and 1<=len(roots)<=8 and len(set(roots))==len(roots) and all(r in modules for r in roots))
    def edges(module,*,eager=False):
        local=set();external=set();review=set()
        def named(name,explicit=False):
            if name in modules:local.add(name)
            elif explicit:raise ValueError("MISSING_SCRIPTS_DEPENDENCY")
            elif name not in sys.stdlib_module_names and name!="__future__":external.add(name)
        def walk(node):
            if eager and isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.Lambda)):
                # Defaults, decorators and annotations can execute at import,
                # so visit those expressions, but not callable bodies.
                for field,value in ast.iter_fields(node):
                    if field!="body":
                        for child in ([value] if isinstance(value,ast.AST) else value if isinstance(value,list) else []):
                            if isinstance(child,ast.AST):walk(child)
                return
            if isinstance(node,ast.Import):
                for alias in node.names:
                    parts=alias.name.split(".")
                    if parts[0]=="scripts":
                        if len(parts)>1:named(parts[1],True)
                        else:review.add("SCRIPTS_NAMESPACE_IMPORT")
                    else:named(parts[0])
            elif isinstance(node,ast.ImportFrom):
                parts=(node.module or "").split(".")
                if node.level or parts[0]=="scripts":
                    if node.level>1:review.add("RELATIVE_IMPORT_REVIEW")
                    if node.module and parts[0]!="scripts":named(parts[0],True)
                    elif len(parts)>1:named(parts[1],True)
                    else:
                        for alias in node.names:
                            if alias.name=="*":review.add("STAR_NAMESPACE_IMPORT")
                            else:named(alias.name,True)
                else:named(parts[0])
            elif isinstance(node,ast.Constant) and isinstance(node.value,str):
                match=re.fullmatch(r"(?:scripts/)?([A-Za-z_][A-Za-z_0-9]*)\.py",node.value)
                if match:
                    if match[1] in modules:local.add(match[1])
                    else:review.add("UNRESOLVED_PYTHON_FILE_LITERAL")
            elif isinstance(node,ast.Call):
                f=node.func
                name=f.id if isinstance(f,ast.Name) else f.attr if isinstance(f,ast.Attribute) else ""
                if name in ("__import__","import_module","find_spec","spec_from_file_location","exec","eval","run_path","run_module"):
                    review.add("DYNAMIC_"+name.upper())
                    if node.args and isinstance(node.args[0],ast.Constant) and isinstance(node.args[0].value,str) and name in ("__import__","import_module","find_spec","run_module"):
                        parts=node.args[0].value.split(".")
                        if parts[0]=="scripts" and len(parts)>1:named(parts[1],True)
                        elif NAME.fullmatch(parts[0]):named(parts[0])
            for child in ast.iter_child_nodes(node):walk(child)
        walk(modules[module])
        return local,external,review
    def closure(start,eager):
        todo=deque(start);seen=set();ext=set();review=set()
        while todo:
            n=todo.popleft()
            if n in seen:continue
            seen.add(n)
            a,b,c=edges(n,eager=eager)
            todo.extend(sorted(a-seen));ext.update(b)
            review.update((n,k) for k in c)
        return seen,ext,review
    eager,_,_=closure((roots[0],),True)
    reachable,external,review=closure(roots,False)
    need(eager<=reachable)
    def paths(ns):return sorted("scripts/"+n+".py" for n in ns)
    return {"schema":"remura.abc.static_dependency_inventory.lab.v1",
            "startup_static":paths(eager),"other_service_reachable_static":paths(reachable-eager),
            "not_reached_statically":paths(set(modules)-reachable),"external_import_names":sorted(external),
            "dynamic_review_sites":[list(x) for x in sorted(review)],
            "all_files_pin":hashlib.sha256(json.dumps([(p,hashlib.sha256(b).hexdigest()) for p,b in sorted(files.items())],separators=(",",":")).encode()).hexdigest(),
            "dynamic_closure_verified":False,"live_environment_verified":False,"safe_to_remove_unreached":False,"release_authorized":False}
