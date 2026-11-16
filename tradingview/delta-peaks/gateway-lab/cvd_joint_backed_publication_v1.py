# REMURA v0.8.102 LAB — 16/11/2026 14:59 CET
"""Synthetic backup-before-finalization transaction. No external authority.
Two-copy limit; stops before reservation when full. No deletion or rotation.
"""
import os,stat,secrets
from contextlib import contextmanager
from cvd_joint_encrypted_v1 import EncryptedJoint,open_encrypted_joint,NAME
from cvd_joint_backup_v1 import inventory,read_exact,MAX_COPIES,PREFIX
from cvd_joint_publication_v1 import need
from cvd_runtime_private_state_v1 import _private,digest
from cvd_runtime_singleflight_v1 import single_flight

class BackedJoint(EncryptedJoint):
    copy_limit=MAX_COPIES
    def inventory(self):return inventory(self.dest,limit=self.copy_limit)
    def __init__(self,source,dest,dest_guard):
        super().__init__(source.fd,source.guard,source.c,source.g,source._key)
        self.dest=dest;self.dest_guard=dest_guard
    def name(self,seq):return f"remura-d-backup-synthetic-{self.g}-{seq:03d}.json"
    def both(self):
        self.check();self.dest_guard()
    def status(self,p):
        out=super().status(p)
        self.both()
        need(self.name(p.sequence) in self.inventory())
        need(read_exact(self.dest,self.name(p.sequence))==read_exact(self.fd,NAME))
        self.authority(p,"STABLE")
        return {**out,"matching_local_backup":True,"independent_failure_domain_verified":False}
    def bootstrap(self,core,*,expected,cutoff,windows,cycles):
        self.authority(expected,"GENESIS");self.both()
        need(self.inventory()==[])
        return super().bootstrap(core,expected=expected,cutoff=cutoff,windows=windows,cycles=cycles)
    def cycle(self,core,*,expected,cutoff,windows):
        self.status(expected);self.both()
        names=self.inventory()
        need(len(names)<self.copy_limit and self.name(expected.sequence+1) not in names)
        return super().cycle(core,expected=expected,cutoff=cutoff,windows=windows)
    def publish(self,pending,s):
        self.authority(pending,"PENDING");self.both()
        names=self.inventory();name=self.name(pending.sequence)
        need(name not in names and len(names)<self.copy_limit)
        self.write(s)
        check,l=self.read();need(digest(check)==digest(s))
        raw=read_exact(self.fd,NAME)
        # Authenticated decode of these exact ciphertext bytes before copying.
        # The source was just fully validated under the same cooperative lock.
        from cvd_runtime_private_state_v1 import encoded
        need(self.decode_file(raw)==encoded({"state":check,"sha256":digest(check)}))
        self.authority(pending,"PENDING");self.both()
        need(self.inventory()==names)
        tmp=PREFIX+secrets.token_hex(16)
        f=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=self.dest)
        with os.fdopen(f,"wb") as stream:
            stream.write(raw);stream.flush();os.fsync(stream.fileno())
        self.dest_guard();self.guard();self.authority(pending,"PENDING")
        os.link(tmp,name,src_dir_fd=self.dest,dst_dir_fd=self.dest,follow_symlinks=False)
        os.fsync(self.dest);os.unlink(tmp,dir_fd=self.dest);os.fsync(self.dest)
        self.both();need(self.inventory()==sorted(names+[name]))
        need(read_exact(self.dest,name)==raw and read_exact(self.fd,NAME)==raw)
        # Only now acknowledge the new stable state. Failed copy leaves
        # PENDING and no status can be published. Never auto-finalize.
        self.authority(pending,"PENDING")
        stable=self.c.finalize(pending,self.describe(check,l))
        return stable,self.status(stable)

@contextmanager
def open_backed_joint(source,destination,custody,*,generation,key,synthetic=False):
    need(synthetic is True)
    with open_encrypted_joint(source,custody,generation=generation,key=key,synthetic=True) as s:
        dest=os.open(destination,os.O_RDONLY|os.O_NOFOLLOW|os.O_DIRECTORY)
        try:
            st=os.fstat(dest);_private(st,stat.S_ISDIR);identity=(st.st_dev,st.st_ino)
            src=os.fstat(s.fd);need(identity!=(src.st_dev,src.st_ino))
            with single_flight(destination) as held:
                def guard():
                    held();cur=os.stat(destination,follow_symlinks=False);_private(cur,stat.S_ISDIR)
                    need((cur.st_dev,cur.st_ino)==identity)
                guard()
                yield BackedJoint(s,dest,guard)
        finally:os.close(dest)
