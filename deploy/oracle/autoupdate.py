#!/usr/bin/env python3
"""REMURA v1.7: CI-gated code-only updater. Credentials/database never synced."""
import argparse,datetime,fcntl,io,json,os,re,shutil,stat,subprocess,sys,tempfile,time,urllib.request,zipfile
from pathlib import Path,PurePosixPath
APP=Path("/opt/remura")
STATE=APP/"private"/"autoupdate-state.json"
WORK=Path("/var/lib/remura-autoupdate")
API="https://api.github.com/repos/mirkoworz/remura"
SHA=re.compile(r"^[a-f0-9]{40}$")
FIELDS=("enabled","state","installedSha","targetSha","failedSha","skippedSha","manualSha","lastCheck","lastSuccess","message")
EXCLUDES=(".git/",".venv/","private/","local/","data/prices/",".env",".env.*","*.pem","*.key","*.apikey","__pycache__/")
WORKFLOWS=("insights-checks.yml","price-checks.yml")
MANUAL_ONLY=("deploy/oracle/","scripts/",".github/workflows/")
def non_code_only(paths):
 return bool(paths) and all(p.startswith("data/") or p.endswith(".md") for p in paths)
def requires_manual(paths):
 return any(p.startswith(MANUAL_ONLY) for p in paths)
def changed_paths(old,new,fetch=None):
 if fetch is None:fetch=json_api
 if not SHA.fullmatch(old) or not SHA.fullmatch(new):raise ValueError("SHA invalid")
 result=fetch(API+"/compare/"+old+"..."+new)
 files=result.get("files")
 if result.get("status")!="ahead" or not isinstance(files,list) or len(files)>=300 or not files:
  raise ValueError("History not safely comparable")
 return [f["filename"] for f in files if isinstance(f.get("filename"),str)]
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
def load_state(path=STATE):
 try:
  v=json.loads(path.read_text("utf-8"))
  return {k:v[k] for k in FIELDS if k in v} if isinstance(v,dict) else {}
 except (OSError,ValueError):return {}
def save_state(v,path=STATE):
 path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
 fd,p=tempfile.mkstemp(prefix=".update-",dir=path.parent)
 try:
  with os.fdopen(fd,"w",encoding="utf-8") as f:json.dump({k:v[k] for k in FIELDS if k in v},f)
  os.chmod(p,0o644)
  os.replace(p,path)
 finally:
  if os.path.exists(p):os.unlink(p)
def json_api(url):
 req=urllib.request.Request(url,headers={"User-Agent":"REMURA-v1.7","Accept":"application/vnd.github+json"})
 with urllib.request.urlopen(req,timeout=20) as res:return json.load(res)
def remote_sha(fetch=json_api):
 s=fetch(API+"/commits/main").get("sha")
 if not isinstance(s,str) or not SHA.fullmatch(s):raise RuntimeError("GitHub SHA non valido")
 return s
def ci_passed(sha,fetch=json_api):
 if not SHA.fullmatch(sha):return False
 for workflow in WORKFLOWS:
  url=API+"/actions/workflows/"+workflow+"/runs?event=push&head_sha="+sha+"&per_page=20"
  runs=fetch(url).get("workflow_runs",[])
  selected=[r for r in runs if r.get("head_sha")==sha and r.get("event")=="push" and r.get("head_branch")=="main"]
  if not selected or any(r.get("status")!="completed" or r.get("conclusion")!="success" for r in selected):return False
 return True
def archive(sha):
 req=urllib.request.Request(API+"/zipball/"+sha,headers={"User-Agent":"REMURA-v1.7"})
 with urllib.request.urlopen(req,timeout=60) as res:body=res.read(150_000_001)
 if len(body)>150_000_000:raise ValueError("Archivio troppo grande")
 return body
def safe_extract(body,dest):
 with zipfile.ZipFile(io.BytesIO(body)) as z:
  items=z.infolist()
  if len(items)>6000 or sum(i.file_size for i in items)>350_000_000:raise ValueError("Archivio troppo grande")
  roots=set()
  for i in items:
   parts=PurePosixPath(i.filename).parts
   if not parts or i.filename.startswith("/") or ".." in parts:raise ValueError("Percorso non valido")
   roots.add(parts[0])
   kind=(i.external_attr>>16)&0o170000
   if kind not in (0,stat.S_IFREG,stat.S_IFDIR):raise ValueError("Symlink non ammesso")
   if len(parts)<2:continue
   rel=Path(*parts[1:])
   if rel.parts[0] in ("private","local",".git") or rel.name.startswith(".env"):raise ValueError("File privato nell'archivio")
   target=dest/rel
   if i.is_dir():target.mkdir(parents=True,exist_ok=True)
   else:
    if i.file_size>20_000_000:raise ValueError("File anomalo")
    target.parent.mkdir(parents=True,exist_ok=True)
    with z.open(i) as src,target.open("wb") as out:shutil.copyfileobj(src,out)
  if len(roots)!=1:raise ValueError("Radice archivio non valida")
 for name in ("scripts/private_server.py","nav.js","deploy/oracle/autoupdate.py","deploy/oracle/remura.service"):
  if not (dest/name).is_file():raise ValueError("Archivio incompleto")
def cmd(*args):
 subprocess.run(args,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=130)
def sync(src,dst,exclude_manual=False):
 args=["rsync","-a","--chown=remura:remura"]
 for x in EXCLUDES:args.append("--exclude="+x)
 # Automatic releases must never copy sensitive/manual-only directories.
 # Backups/rollback use the default False to preserve every existing file.
 if exclude_manual:
  for x in MANUAL_ONLY:args.append("--exclude="+x)
 # No --delete: never erase locally generated files.
 cmd(*args,str(src)+"/",str(dst)+"/")
def healthy():
 try:
  with urllib.request.urlopen("http://127.0.0.1:8765/private-api/health",timeout=4) as r:
   return r.status==200 and json.load(r).get("name")=="REMURA Private"
 except (OSError,ValueError,TimeoutError):return False
def wait_health():
 for _ in range(25):
  if healthy():return True
  time.sleep(1)
 return False
def install(sha):
 if not healthy():raise RuntimeError("Server non sano, aggiornamento annullato")
 WORK.mkdir(mode=0o700,parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory(prefix="candidate-",dir=WORK) as temp:
  candidate=Path(temp)
  safe_extract(archive(sha),candidate)
  cmd(sys.executable,"-m","py_compile",str(candidate/"scripts/private_server.py"),str(candidate/"deploy/oracle/autoupdate.py"))
  cmd("bash","-n",str(candidate/"deploy/oracle/install.sh"))
  backup=Path(tempfile.mkdtemp(prefix="backup-",dir=WORK))
  try:
   sync(APP,backup)
   created=[p.relative_to(candidate) for p in candidate.rglob("*") if p.is_file() and not (APP/p.relative_to(candidate)).exists()]
   stopped=False
   try:
    cmd("systemctl","stop","remura-private.service");stopped=True
    sync(candidate,APP,exclude_manual=True)
    cmd("systemctl","start","remura-private.service")
    if not wait_health():raise RuntimeError("Nuovo server non sano")
    prior=WORK/"previous-code"
    if prior.exists():shutil.rmtree(prior)
    backup.rename(prior)
   except Exception:
    if stopped:
     try:
      sync(backup,APP)
      for relative in created:
       p=APP/relative
       if p.is_file() or p.is_symlink():p.unlink()
      cmd("systemctl","restart","remura-private.service")
      if not wait_health():raise RuntimeError("Health check dopo rollback fallito")
     except Exception as err:raise RuntimeError("ROLLBACK NON RIUSCITO") from err
    raise
  finally:
   if backup.exists():shutil.rmtree(backup,ignore_errors=True)
def check_once():
 if os.geteuid()!=0:raise RuntimeError("Serve root")
 WORK.mkdir(mode=0o700,parents=True,exist_ok=True)
 with (WORK/"lock").open("w") as lock:
  try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:return 0
  state=load_state()
  if not state.get("enabled"):return 0
  state["lastCheck"]=now();applying=False
  try:
   sha=remote_sha();state["targetSha"]=sha
   if sha==state.get("installedSha"):state.update(state="up_to_date",message="Codice già aggiornato")
   elif sha==state.get("failedSha"):state.update(state="blocked",message="Questo commit è stato bloccato dopo un errore")
   elif sha==state.get("skippedSha"):state.update(state="data_only",message="Solo archivi dati o documentazione: nessun riavvio")
   elif sha==state.get("manualSha"):state.update(state="manual_required",message="Modifica delicata: aggiornamento da Termius richiesto")
   else:
    files=changed_paths(state.get("installedSha",""),sha)
    if non_code_only(files):
     state.update(state="data_only",skippedSha=sha,message="Solo dati o documentazione: codice invariato")
    elif requires_manual(files):
     state.update(state="manual_required",manualSha=sha,message="Scripts/server/installer: serve aggiornamento manuale")
    elif not ci_passed(sha) or remote_sha()!=sha:
     state.update(state="waiting_ci",message="Attendo entrambi i test verdi per il commit main")
    else:
     applying=True;install(sha)
     state.update(state="updated",installedSha=sha,failedSha="",skippedSha="",manualSha="",lastSuccess=now(),message="Aggiornamento verificato e installato")
  except Exception as e:
   if applying:state["failedSha"]=state.get("targetSha","")
   state.update(state="error",message="Verifica o aggiornamento fallito; controlla log VPS")
   print("REMURA UPDATE ERROR:",type(e).__name__,str(e),file=sys.stderr)
   save_state(state);return 1
  save_state(state);return 0
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--init-sha",default="")
 opts=p.parse_args()
 if opts.init_sha:
  if os.geteuid()!=0 or not SHA.fullmatch(opts.init_sha):p.error("Serve root e SHA completo")
  save_state({"enabled":True,"state":"configured","installedSha":opts.init_sha,"targetSha":opts.init_sha,
              "failedSha":"","skippedSha":"","manualSha":"","lastCheck":"","lastSuccess":now(),"message":"Configurato, attendo prima verifica"})
 else:sys.exit(check_once())
