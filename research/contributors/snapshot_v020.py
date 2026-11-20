# REMURA Experience v0.20 LAB — 20/11/2026 18:59 CET
# Offline fixture only. No real identity, independent authority or network delivery.
import json
import journal_v015 as journal
import witness_v016 as witness
from snapshot_store_v019 import SnapshotStore, JKEY, WKEY, actor, project, parse, sha, fresh, stamp_ms

MAX_WINDOW_MS = 5000


def window(start, end, stamp):
    return type(start) is int and type(end) is int and 0 <= end-start <= MAX_WINDOW_MS and fresh(stamp,end)


class SnapshotV020(SnapshotStore):
    def deliver(self, auth, clock):
        try:
            user = actor(auth,'CONTRIBUTOR')
            with self._open() as (a,j,w):
                pin,raw,stamp = self._verified(a,j,w)
                if raw is None or actor(auth,'CONTRIBUTOR') != user:
                    return None
                start = clock()
                reply = project(raw,start)
                if actor(auth,'CONTRIBUTOR') != user or self._verified(a,j,w)[0] != pin:
                    return None
                end = clock()
                if not window(start,end,stamp):
                    return None
                view = json.loads(reply['body'])
                if view['revision'] != pin[0] or view['as_of'] != stamp:
                    return None
                view['schema'] = 'REMURA_SHARED_VIEW_FIXTURE_V2'
                for row in view['prices']:
                    if end-stamp_ms(row['observed_at']) > 900000:
                        row['freshness'] = 'STALE'
                        row['price'] = None
                reply['body'] = json.dumps(view,separators=(',',':'),ensure_ascii=True,allow_nan=False)
                return reply if len(reply['body'].encode('ascii')) <= 16384 else None
        except Exception:
            return None

    def _pending(self,a,j,prior,wanted):
        n = prior[0]
        head = journal.scan(j,JKEY)
        rows = a.execute('SELECT revision,generation,as_of,digest,payload FROM fixture_revision ORDER BY revision LIMIT 33').fetchall()
        links = j.execute('SELECT record,tag FROM chain ORDER BY seq LIMIT 33').fetchall()
        heads = a.execute('SELECT id,revision,generation,digest FROM fixture_head LIMIT 2').fetchall()
        if len(rows)!=n+1 or head[0] not in (n,n+1) or len(links)!=head[0]:
            raise ValueError('count')
        previous=''
        for i,(rev,gen,stamp,d,raw) in enumerate(rows,1):
            if rev!=i or gen!='fixture-v014' or stamp<previous or sha(raw)!=d:
                raise ValueError('archive')
            parse(raw,i,stamp)
            if i<=len(links) and json.loads(links[i-1][0])['snapshot_digest']!=d:
                raise ValueError('link')
            previous=stamp
        if n and (links[n-1][1]!=prior[1] or rows[n-1][3]!=prior[2]):
            raise ValueError('prior')
        if rows[-1][3]!=wanted or heads!=[(1,n+1,'fixture-v014',wanted)]:
            raise ValueError('candidate')
        return head,rows[-1][4],previous

    def recover_snapshot(self, prior, wanted, auth, approve, clock, interrupt=False):
        # Prior and digest must originate from a trusted retained intent (synthetic here).
        try:
            owner=actor(auth,'OWNER')
            if not witness.valid(prior) or prior[0]>=32 or not journal.hex64(wanted) or wanted==witness.ZERO or type(interrupt) is not bool:
                return 'BLOCKED'
            with self._open() as (a,j,w):
                pin=witness.read(w,WKEY)
                if pin!=prior and (pin[0]!=prior[0]+1 or pin[2]!=wanted):
                    return 'BLOCKED'
                head,raw,stamp=self._pending(a,j,prior,wanted)
                if pin!=prior:
                    self._verified(a,j,w)
                    return 'ALREADY_COMMITTED' if actor(auth,'OWNER')==owner else 'BLOCKED'
                start=clock(); project(raw,start)
                if approve(prior,wanted) is not True or actor(auth,'OWNER')!=owner or not window(start,clock(),stamp):
                    return 'BLOCKED'
                if head==prior[:2]:
                    head=journal.append(j,JKEY,prior[:2],wanted,True)
                    if head is None:
                        return 'BLOCKED'
                if interrupt:
                    return 'INTERRUPTED'
                if self._pending(a,j,prior,wanted)[0]!=head or head[0]!=prior[0]+1 or actor(auth,'OWNER')!=owner or not window(start,clock(),stamp):
                    return 'BLOCKED'
                if not witness.advance(w,WKEY,prior,(*head,wanted),True):
                    return 'BLOCKED'
                return 'RECOVERED' if self._verified(a,j,w)[0]==(*head,wanted) else 'BLOCKED'
        except Exception:
            return 'BLOCKED'
