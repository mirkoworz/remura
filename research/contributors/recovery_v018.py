# REMURA Experience v0.18 LAB — 20/11/2026 CET
# Explicit local recovery; never a production authorization or rollback authority.
import json
import journal_v015 as jmod
import witness_v016 as wmod
from integration_v017 import Fixture, JKEY, WKEY, body, digest


class Recovery(Fixture):
    def read(self, authorize):
        try:
            return super().read(authorize)
        except Exception:
            return None

    def publish(self, expected, stamp, value, authorize, interrupt=None):
        try:
            return super().publish(expected, stamp, value, authorize, interrupt)
        except Exception:
            return 'BLOCKED'

    def _candidate(self, a, j, prior, wanted):
        n = prior[0]
        rows = a.execute('SELECT revision,generation,as_of,digest,payload FROM fixture_revision ORDER BY revision LIMIT 33').fetchall()
        heads = a.execute('SELECT id,revision,generation,digest FROM fixture_head LIMIT 2').fetchall()
        links = j.execute('SELECT record,tag FROM chain ORDER BY seq LIMIT 33').fetchall()
        if len(rows) != n+1 or len(links) not in (n,n+1):
            raise ValueError('unexpected revision count')
        previous = ''
        for i, (rev, gen, stamp, sha, payload) in enumerate(rows, 1):
            parsed = json.loads(payload)
            if (type(parsed) is not dict or rev != i or gen != 'fixture-v014' or stamp < previous
                    or payload != body(i, stamp, parsed.get('value')) or digest(payload) != sha):
                raise ValueError('archive invalid')
            if i <= len(links) and json.loads(links[i-1][0])['snapshot_digest'] != sha:
                raise ValueError('journal digest mismatch')
            previous = stamp
        if n and (links[n-1][1] != prior[1] or rows[n-1][3] != prior[2]):
            raise ValueError('prior mismatch')
        if rows[-1][3] != wanted or heads != [(1,n+1,'fixture-v014',wanted)]:
            raise ValueError('candidate mismatch')
        return jmod.scan(j,JKEY)

    def recover(self, prior, wanted, authorize, approve, interrupt=False):
        # prior and wanted must come from independently retained approved intent.
        # Caller supplies trusted synthetic callbacks; no request/client adapter.
        try:
            if not wmod.valid(prior) or prior[0] >= 32 or not jmod.hex64(wanted) or wanted == wmod.ZERO:
                return 'BLOCKED'
            if type(interrupt) is not bool or authorize() != 'OWNER':
                return 'DENIED'
            with self._open() as (a,j,w):
                pin = wmod.read(w,WKEY)
                if pin != prior and (pin[0] != prior[0]+1 or pin[2] != wanted):
                    return 'BLOCKED'
                head = self._candidate(a,j,prior,wanted)
                if pin != prior:
                    self._verified(a,j,w)
                    return 'ALREADY_COMMITTED' if authorize() == 'OWNER' else 'DENIED'
                if approve(prior,wanted) is not True or authorize() != 'OWNER':
                    return 'DENIED'
                if head == prior[:2]:
                    head = jmod.append(j,JKEY,prior[:2],wanted,True)
                    if head is None:
                        return 'BLOCKED'
                if interrupt:
                    return 'INTERRUPTED'
                if head[0] != prior[0]+1 or self._candidate(a,j,prior,wanted) != head or authorize() != 'OWNER':
                    return 'BLOCKED'
                if not wmod.advance(w,WKEY,prior,(*head,wanted),True):
                    return 'BLOCKED'
                self._verified(a,j,w)
                return 'RECOVERED'
        except Exception:
            return 'BLOCKED'
