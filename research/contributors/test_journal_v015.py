# REMURA Experience v0.15 LAB — synthetic local execution only
import hashlib
import os
import shutil
import tempfile
from pathlib import Path
from journal_v015 import ZERO, open_journal, append, verify, scan


def run():
    count = 0
    def ok(v):
        nonlocal count
        assert v, f'check {count+1}'
        count += 1
    key = b'fixture-only-key-not-production!'  # exactly 32 bytes; publicly known
    assert len(key) == 32
    initial = (0, ZERO)
    digest = lambda n: hashlib.sha256(f'fixture-{n}'.encode()).hexdigest()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'journal.sqlite'
        j = open_journal(path, create=True)
        ok((path.stat().st_mode & 0o777) == 0o600)
        ok(verify(j,key,initial))
        ok(not verify(j,key,None))
        ok(append(j,key,initial,digest(1),False) is None)
        pin1 = append(j,key,initial,digest(1),True)
        ok(pin1 is not None and pin1[0] == 1)
        ok(verify(j,key,pin1) and not verify(j,key,initial))
        j.close()
        shutil.copy2(path, Path(tmp)/'old.sqlite')
        j = open_journal(path)
        ok(verify(j,key,pin1))
        ok(not verify(j,b'x'*32,pin1))
        ok(append(j,key,initial,digest(2),True) is None)
        ok(append(j,key,pin1,'bad',True) is None)
        pin2 = append(j,key,pin1,digest(2),True)
        ok(pin2 is not None and pin2[0] == 2)
        old = open_journal(Path(tmp)/'old.sqlite')
        ok(not verify(old,key,pin2))
        ok(append(old,key,pin2,digest(3),True) is None)
        old.close()
        ok(not verify(j,key,pin1))  # interrupted external pin advancement
        ok(verify(j,key,pin2))
        j.close()
        for mode in ('record','tag','truncate','gap'):
            p=Path(tmp)/(mode+'.sqlite'); shutil.copy2(path,p)
            q=open_journal(p)
            if mode=='record': q.execute("UPDATE chain SET record=replace(record,?,?) WHERE seq=1",(digest(1),digest(3)))
            elif mode=='tag': q.execute('UPDATE chain SET tag=? WHERE seq=1',(ZERO,))
            elif mode=='truncate': q.execute('DELETE FROM chain WHERE seq=2')
            else: q.execute('DELETE FROM chain WHERE seq=1')
            ok(not verify(q,key,pin2));q.close()
        j=open_journal(path)
        pin=pin2
        for i in range(3,33):
            pin=append(j,key,pin,digest(i),True)
            assert pin is not None
        ok(pin[0]==32 and verify(j,key,pin))
        ok(append(j,key,pin,digest(33),True) is None)
        j.close()
        try: open_journal(path,create=True)
        except FileExistsError: ok(True)
        else: ok(False)
        try: open_journal(Path(tmp)/'missing.sqlite')
        except ValueError: ok(True)
        else: ok(False)
    print(f'REMURA_JOURNAL_FIXTURE_PASS={count}')

if __name__ == '__main__':
    run()
