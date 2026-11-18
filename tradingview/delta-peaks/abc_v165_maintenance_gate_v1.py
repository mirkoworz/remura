# REMURA v0.8.145 LAB — 18/11/2026, sessione successiva alle 09:44 CET
"""Reviewed updater candidate and durable inhibit protocol.
Never installs a file or changes systemd. No automatic inhibit removal.
"""
import hashlib,os,re
BASE="53ca8ec381e30d019f1cc8570e33e0150e6c233e"
MARKER="maintenance-v165.inhibit"
# Self-contained functions embedded into the exact existing updater candidate;
# no new runtime dependency or import from a research directory.
GUARD = '''
MAINTENANCE_MARKER="maintenance-v165.inhibit"
def maintenance_lock(work):
 s=work.lstat()
 if not stat.S_ISDIR(s.st_mode) or s.st_uid!=os.getuid() or s.st_mode&0o077:
  raise RuntimeError("MAINTENANCE_WORK_UNSAFE")
 fd=os.open(work/"lock",os.O_RDWR|os.O_NOFOLLOW|os.O_NONBLOCK)
 try:
  s=os.fstat(fd); p=(work/"lock").lstat()
  if not stat.S_ISREG(s.st_mode) or s.st_uid!=os.getuid() or s.st_mode&0o077 or s.st_nlink!=1 or (s.st_dev,s.st_ino)!=(p.st_dev,p.st_ino):
   raise RuntimeError("MAINTENANCE_LOCK_UNSAFE")
  return os.fdopen(fd,"r+b")
 except BaseException:
  os.close(fd);raise
def maintenance_pending(work):
 try:(work/MAINTENANCE_MARKER).lstat()
 except FileNotFoundError:return False
 return True
def initialize_state(sha):
 if os.geteuid()!=0 or not SHA.fullmatch(sha):raise RuntimeError("MAINTENANCE_INIT_INVALID")
 with maintenance_lock(WORK) as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  if maintenance_pending(WORK):raise RuntimeError("MAINTENANCE_INHIBITED")
  save_state({"enabled":True,"state":"configured","installedSha":sha,"targetSha":sha,
              "failedSha":"","skippedSha":"","manualSha":"","lastCheck":"","lastSuccess":now(),"message":"Configurato, attendo prima verifica"})
'''
def replace_once(s,a,b):
    if s.count(a)!=1:raise ValueError("UPDATER_PATCH_CONTEXT")
    return s.replace(a,b,1)
def build_candidate(raw):
    if type(raw) is not bytes or hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()!=BASE:
        raise ValueError("UPDATER_BASE_PIN")
    s=raw.decode("utf-8")
    s=replace_once(s,"def check_once():",GUARD+"\ndef check_once():")
    s=replace_once(s,' with (WORK/"lock").open("w") as lock:'," with maintenance_lock(WORK) as lock:")
    s=replace_once(s,'  except BlockingIOError:return 0\n  state=load_state()',
                   '  except BlockingIOError:return 0\n  if maintenance_pending(WORK):\n   print("REMURA UPDATE: MAINTENANCE_INHIBITED")\n   return 0\n  state=load_state()')
    start='  save_state({"enabled":True,"state":"configured","installedSha":opts.init_sha,"targetSha":opts.init_sha,\n              "failedSha":"","skippedSha":"","manualSha":"","lastCheck":"","lastSuccess":now(),"message":"Configurato, attendo prima verifica"})'
    s=replace_once(s,start,"  initialize_state(opts.init_sha)")
    compile(s,"autoupdate_candidate.py","exec")
    return s.encode("utf-8")

def create_inhibit_lab(work,transaction,*,synthetic=False):
    """Exercise actual persistent marker creation only in disposable test roots.
    Requires caller to hold the same cooperative lock; no release/clear API.
    """
    import fcntl,json,stat,tempfile
    from pathlib import Path
    work=Path(work)
    if not (synthetic is True and work.is_absolute() and work==work.resolve()
            and work.parent==Path(tempfile.gettempdir()).resolve()
            and re.fullmatch(r"remura-inhibit-lab-[A-Za-z0-9_]+",work.name)
            and re.fullmatch(r"[a-f0-9]{64}",transaction)):
        raise ValueError("INHIBIT_LAB_ONLY")
    ns={"os":os,"stat":stat,"fcntl":fcntl,"MAINTENANCE_MARKER":MARKER}
    exec(compile(GUARD,"maintenance_guard","exec"),ns)
    with ns["maintenance_lock"](work) as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        fd=os.open(work/MARKER,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,"wb") as f:
            f.write(json.dumps({"schema":"remura.v165.inhibit.v1","transaction":transaction},sort_keys=True).encode())
            f.flush();os.fsync(f.fileno())
        d=os.open(work,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try:os.fsync(d)
        finally:os.close(d)
