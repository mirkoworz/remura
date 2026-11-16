# REMURA v0.8.103 LAB — 16/11/2026 15:02 CET
"""Explicit bounded synthetic rotation. No real deletion, scheduler or remote storage."""
import os
from contextlib import contextmanager
from cvd_joint_backed_publication_v1 import BackedJoint,open_backed_joint
from cvd_joint_backup_v1 import read_exact
from cvd_joint_publication_v1 import need
from cvd_joint_encrypted_v1 import NAME

class RotatingJoint(BackedJoint):
    copy_limit=3
    def status(self,p):
        result=super().status(p)
        names=self.inventory()
        latest=[self.name(i) for i in range(max(1,p.sequence-1),p.sequence+1)]
        if p.sequence>=3:
            need(names in (latest,[self.name(p.sequence-2)]+latest))
        else:need(names==latest)
        return {**result,"backup_count":len(names),"rotation_required":len(names)==3}
    def cycle(self,core,*,expected,cutoff,windows):
        out=self.status(expected)
        need(not out["rotation_required"])
        return super().cycle(core,expected=expected,cutoff=cutoff,windows=windows)
    def prune(self,expected,*,allow_synthetic_prune=False):
        need(allow_synthetic_prune is True)
        result=self.status(expected)
        need(result["rotation_required"] and expected.sequence>=3)
        names=[self.name(i) for i in range(expected.sequence-2,expected.sequence+1)]
        need(self.inventory()==names)
        # Never select a path from user input. Preserve the newest exact copy
        # and previous named copy; the previous is not newly authenticated here.
        current=read_exact(self.dest,names[-1])
        previous=read_exact(self.dest,names[-2])
        oldest=read_exact(self.dest,names[0])
        self.both();self.authority(expected,"STABLE")
        need(self.inventory()==names)
        need(read_exact(self.fd,NAME)==current and read_exact(self.dest,names[-1])==current)
        need(read_exact(self.dest,names[-2])==previous and read_exact(self.dest,names[0])==oldest)
        try:
            os.unlink(names[0],dir_fd=self.dest);os.fsync(self.dest)
        except BaseException:
            self.failed=True
            raise
        need(self.inventory()==names[1:])
        need(read_exact(self.dest,names[-2])==previous and read_exact(self.dest,names[-1])==current)
        return self.status(expected)

@contextmanager
def open_rotating_joint(source,destination,custody,*,generation,key,synthetic=False):
    need(synthetic is True)
    with open_backed_joint(source,destination,custody,generation=generation,key=key,synthetic=True) as j:
        yield RotatingJoint(j,j.dest,j.dest_guard)
