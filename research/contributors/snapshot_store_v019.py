# REMURA Experience v0.19 LAB — 20/11/2026 CET
# New local fixture only. No migration of existing stores or real keys.
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from integration_v017 import Fixture
import journal_v015 as journal
import witness_v016 as witness

JKEY, WKEY = b'3'*32, b'4'*32
ADAPTER = Path(__file__).with_name('snapshot_adapter_v019.mjs')
FIELDS = {'schema','revision','as_of','prices','forex_rows'}


def encode(x):
    return json.dumps(x, sort_keys=True, separators=(',',':'), ensure_ascii=True, allow_nan=False)


def sha(raw):
    return hashlib.sha256(raw.encode('ascii')).hexdigest()


def stamp_ms(stamp):
    if type(stamp) is not str or len(stamp) != 20:
        raise ValueError('timestamp')
    t = datetime.strptime(stamp,'%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
    if t.strftime('%Y-%m-%dT%H:%M:%SZ') != stamp:
        raise ValueError('timestamp')
    return int(t.timestamp())*1000


def fresh(stamp, now):
    return type(now) is int and 0 <= now-stamp_ms(stamp) <= 900000


def parse(raw, revision, stamp):
    if type(raw) is not str or not 1 <= len(raw.encode('ascii')) <= 8192:
        raise ValueError('size')
    x=json.loads(raw)
    if (type(x) is not dict or set(x)!=FIELDS or x['schema']!='REMURA_SHARED_FIXTURE_V1'
            or type(x['revision']) is not int or x['revision']!=revision or x['as_of']!=stamp or encode(x)!=raw):
        raise ValueError('payload')
    stamp_ms(stamp)
    return x


def project(raw, now):
    if type(now) is not int or not 0 <= now <= 9007199254740991:
        raise ValueError('clock')
    result=subprocess.run(['node',str(ADAPTER),str(now)],input=raw.encode('ascii'),capture_output=True,timeout=5,check=True)
    if len(result.stdout)>20000:
        raise ValueError('response cap')
    reply=json.loads(result.stdout)
    if reply.get('status')!=200 or reply.get('headers',{}).get('Cache-Control')!='no-store, max-age=0':
        raise ValueError('projection denied')
    return reply


def actor(auth,role):
    a=auth()
    if (type(a) is not dict or set(a)!={'role','subject','generation'} or a['role']!=role
            or a['generation']!='fixture-v019' or type(a['subject']) is not str or not 1<=len(a['subject'])<=64):
        raise ValueError('authorization')
    return dict(a)


class SnapshotStore(Fixture):
    # Dedicated new directory, separate synthetic key domain. Reuse v0.14 schema only.
    def initialize(self):
        raise ValueError('use explicit initialize_snapshot')

    def initialize_snapshot(self):
        # Base initializer uses its own witness key; create a fresh witness directly instead.
        import os
        from contextlib import closing
        from integration_v017 import SCHEMA
        self.root.mkdir(mode=0o700,exist_ok=False)
        for path in (self.lock,self.archive):
            os.close(os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600))
        with closing(self._archive()) as db:
            db.executescript(SCHEMA)
        with closing(journal.open_journal(self.chain,create=True)),closing(witness.open_witness(self.anchor,WKEY,create=True)):
            pass

    def _open(self):
        # Base _open opens witness without validating its key until read; use new domain key below.
        return super()._open()

    def _verified(self,a,j,w):
        pin=witness.read(w,WKEY)
        if journal.scan(j,JKEY)!=pin[:2]:
            raise ValueError('journal')
        rows=a.execute('SELECT revision,generation,as_of,digest,payload FROM fixture_revision ORDER BY revision LIMIT 33').fetchall()
        links=j.execute('SELECT record FROM chain ORDER BY seq LIMIT 33').fetchall()
        heads=a.execute('SELECT id,revision,generation,digest FROM fixture_head LIMIT 2').fetchall()
        if len(rows)!=pin[0] or len(links)!=pin[0]:
            raise ValueError('count')
        prior=''
        for i,(rev,gen,stamp,d,raw) in enumerate(rows,1):
            if rev!=i or gen!='fixture-v014' or stamp<prior or sha(raw)!=d or json.loads(links[i-1][0])['snapshot_digest']!=d:
                raise ValueError('archive')
            parse(raw,i,stamp)
            prior=stamp
        if not rows:
            if heads or pin!=witness.EMPTY:
                raise ValueError('empty')
            return pin,None,''
        if heads!=[(1,pin[0],'fixture-v014',pin[2])] or rows[-1][3]!=pin[2]:
            raise ValueError('head')
        return pin,rows[-1][4],prior

    def publish(self,*args,**kwargs):
        return 'BLOCKED'  # scalar interface is not supported

    def read(self,*args,**kwargs):
        return None  # only projected delivery; never return raw snapshot externally

    def publish_snapshot(self, expected, data, auth, approve, clock, interrupt=None):
        try:
            owner=actor(auth,'OWNER')
            if type(expected) is not int or not 0<=expected<32 or type(data) is not dict or set(data)!={'as_of','prices','forex_rows'} or interrupt not in (None,'archive','journal'):
                return 'BLOCKED'
            raw=encode({'schema':'REMURA_SHARED_FIXTURE_V1','revision':expected+1,**data})
            x=parse(raw,expected+1,data['as_of']); d=sha(raw)
            now=clock(); project(raw,now)
            with self._open() as (a,j,w):
                pin,_,prior=self._verified(a,j,w)
                if pin[0]!=expected or x['as_of']<prior or actor(auth,'OWNER')!=owner or approve(pin,d) is not True or actor(auth,'OWNER')!=owner:
                    return 'BLOCKED'
                end=clock()
                if not fresh(x['as_of'],end) or end<now:
                    return 'BLOCKED'
                a.execute('BEGIN IMMEDIATE')
                a.execute('INSERT INTO fixture_revision VALUES(?,?,?,?,?)',(expected+1,'fixture-v014',x['as_of'],d,raw))
                if expected==0:
                    a.execute('INSERT INTO fixture_head VALUES(1,?,?,?)',(1,'fixture-v014',d))
                else:
                    a.execute('UPDATE fixture_head SET revision=?,digest=? WHERE id=1',(expected+1,d))
                a.commit()
                if interrupt=='archive':
                    return 'INTERRUPTED'
                head=journal.append(j,JKEY,pin[:2],d,True)
                if head is None or interrupt=='journal':
                    return 'INTERRUPTED'
                if actor(auth,'OWNER')!=owner or not fresh(x['as_of'],clock()) or journal.scan(j,JKEY)!=head or not witness.advance(w,WKEY,pin,(*head,d),True):
                    return 'BLOCKED'
                return 'PUBLISHED' if self._verified(a,j,w)[0]==(*head,d) else 'BLOCKED'
        except Exception:
            return 'BLOCKED'

    def deliver(self,auth,clock):
        try:
            user=actor(auth,'CONTRIBUTOR')
            with self._open() as (a,j,w):
                pin,raw,stamp=self._verified(a,j,w)
                if raw is None or actor(auth,'CONTRIBUTOR')!=user:
                    return None
                now=clock(); reply=project(raw,now)
                # Final check occurs inside local cooperative lock, not a network send guarantee.
                end=clock()
                if not fresh(stamp,end) or end!=now or actor(auth,'CONTRIBUTOR')!=user or self._verified(a,j,w)[0]!=pin:
                    return None
                return reply
        except Exception:
            return None
