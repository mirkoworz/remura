# REMURA v0.8.101 LAB — 16/11/2026 14:57 CET
"""Bounded synthetic encrypted backup copy, no rotation or external service.
Two distinct private directories and cooperating locks, not independent devices.
No deletion, overwrite, real keys or automatic backup scheduling.
"""
import hashlib,json,os,stat,secrets,re
from cvd_joint_encrypted_v1 import open_encrypted_joint,NAME,MAX_CIPHER
from cvd_joint_publication_v1 import validate,MAX_FILE,need
from cvd_runtime_private_state_v1 import encoded,digest,_no_duplicates,_private
from cvd_runtime_singleflight_v1 import single_flight,NAME as LOCK
MAX_COPIES=2
PREFIX=".remura-d-backup-synthetic-"
PATTERN=re.compile(r"remura-d-backup-synthetic-[0-9a-f]{32}-[0-9]{3}\.json")

def read_exact(fd,name):
    f=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd)
    try:
        st=os.fstat(f);_private(st,stat.S_ISREG)
        need(st.st_nlink==1 and 1<=st.st_size<=MAX_CIPHER)
        with os.fdopen(os.dup(f),"rb") as stream:raw=stream.read(MAX_CIPHER+1)
        need(len(raw)==st.st_size)
        return raw
    finally:os.close(f)

def inventory(fd):
    names=os.listdir(fd)
    need(LOCK in names and len(names)<=MAX_COPIES+1)
    copies=[]
    for name in names:
        if name==LOCK:continue
        need(PATTERN.fullmatch(name) is not None)
        st=os.stat(name,dir_fd=fd,follow_symlinks=False);_private(st,stat.S_ISREG)
        need(st.st_nlink==1 and 1<=st.st_size<=MAX_CIPHER)
        copies.append(name)
    return sorted(copies)

def backup(source,destination,custody,*,generation,key,expected,synthetic=False):
    need(synthetic is True)
    with open_encrypted_joint(source,custody,generation=generation,key=key,synthetic=True) as s:
        s.authority(expected,"STABLE");s.check()
        dest=os.open(destination,os.O_RDONLY|os.O_NOFOLLOW|os.O_DIRECTORY)
        try:
            st=os.fstat(dest);_private(st,stat.S_ISDIR)
            src=os.fstat(s.fd);identity=(st.st_dev,st.st_ino)
            need(identity!=(src.st_dev,src.st_ino))
            with single_flight(destination) as held:
                def guard():
                    s.check();held();s.authority(expected,"STABLE")
                    cur=os.stat(destination,follow_symlinks=False);_private(cur,stat.S_ISDIR)
                    need((cur.st_dev,cur.st_ino)==identity)
                guard()
                names=inventory(dest)
                name=f"remura-d-backup-synthetic-{generation}-{expected.sequence:03d}.json"
                need(PATTERN.fullmatch(name) is not None and 1<=expected.sequence<=96)
                need(name not in names and len(names)<MAX_COPIES)
                raw=read_exact(s.fd,NAME)
                plain=s.decode_file(raw);need(0<len(plain)<=MAX_FILE)
                w=json.loads(plain,object_pairs_hook=_no_duplicates)
                need(type(w) is dict and set(w)=={"state","sha256"} and encoded(w)==plain)
                state=w["state"];need(w["sha256"]==digest(state)==expected.state_digest)
                l=validate(state,generation)
                desc=s.describe(state,l)
                need(desc["claim_ms"]==expected.cutoff_ms and l.summary()["cycles_recorded"]==expected.sequence)
                guard();need(inventory(dest)==names)
                tmp=PREFIX+secrets.token_hex(16)
                f=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=dest)
                with os.fdopen(f,"wb") as stream:
                    stream.write(raw);stream.flush();os.fsync(stream.fileno())
                guard()
                os.link(tmp,name,src_dir_fd=dest,dst_dir_fd=dest,follow_symlinks=False)
                os.fsync(dest)
                os.unlink(tmp,dir_fd=dest);os.fsync(dest)
                guard();need(inventory(dest)==sorted(names+[name]))
                need(read_exact(dest,name)==raw and read_exact(s.fd,NAME)==raw)
                return {"status":"EXACT_SYNTHETIC_BACKUP_CREATED","name":name,
                        "sequence":expected.sequence,"ciphertext_bytes":len(raw),
                        "ciphertext_sha256":hashlib.sha256(raw).hexdigest(),
                        "copies":len(names)+1,"copy_limit":MAX_COPIES,
                        "steady_logical_bound_bytes":MAX_COPIES*MAX_CIPHER,
                        "independent_failure_domain_verified":False,
                        "custody_advanced":False,"scientific_admission":False,"live_authorized":False}
        finally:os.close(dest)
