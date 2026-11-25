"""Offline package validation; no production files, services, or network access."""
import ast, hashlib, json
from pathlib import Path
from owner_static_resolver import UI_PATHS
root=Path(__file__).resolve().parent
m=json.loads((root/"owner-release-manifest.json").read_text())
assert m["channel"]=="owner-protected-only" and m["activationAuthorized"] is False
assert m["originalServerBlob"]=="0853194762f3f0340451a69c9ed8b4e0261db42d"
expected={x["path"]:x for x in m["files"]}
assert len(expected)==len(m["files"])==79
assert set(expected)==UI_PATHS
actual={p.relative_to(root/"ui").as_posix() for p in (root/"ui").rglob("*") if p.is_file()}
assert actual==set(expected)
for path,f in expected.items():
    p=root/"ui"/path
    assert not p.is_symlink() and p.resolve().is_relative_to(root/"ui")
    body=p.read_bytes()
    assert len(body)==f["bytes"],path
    assert hashlib.sha1(b"blob "+str(len(body)).encode()+b"\0"+body).hexdigest()==f["gitBlob"],path
    if p.suffix in (".json",".webmanifest"):
        json.loads(body)
assert sum(p.endswith(".html") for p in expected)==10
assert "capital-cloud-config.js" not in expected
assert "preview-network-guard.js" not in expected
for path in ("server/private_server.py","owner_static_resolver.py","test_owner_static_resolver.py"):
    ast.parse((root/path).read_text(),filename=path)
print("OK: 79/79 FILE UI, 10 PAGINE, 3 SCRIPT PYTHON COMPILABILI (AST)")
print("OK: CONFIG RUNTIME E SERVIZI PRIVATI ESCLUSI DAL PACCHETTO UI")
