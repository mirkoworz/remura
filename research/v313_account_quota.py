"""V31.3 LAB account quota adapter. No provider call on import or selftest.
Analytics are adaptive estimates, not exact billing. Plan attestation remains explicit.
The caller must separately authorize the bounded read-only provider requests.
"""
import unittest
from datetime import datetime,timezone
HOUR=3600000
DAY=24*HOUR
def day(ms):
    return datetime.fromtimestamp(ms/1000,timezone.utc).date().isoformat()
def build_sample(*,now,analytics_ms,usage,storage_ms,storage,plan):
    if any(type(x) is not int or x<=0 for x in (now,analytics_ms,storage_ms)):raise ValueError("clock")
    if not 0<=now-analytics_ms<=HOUR or day(now)!=day(analytics_ms):raise ValueError("analytics_stale")
    if not 0<=now-storage_ms<=DAY or day(now)!=day(storage_ms):raise ValueError("storage_stale")
    if set(plan)!={"plan","confirmed_ms","expires_ms"} or plan["plan"]!="FREE" or any(type(plan[k]) is not int for k in ("confirmed_ms","expires_ms")) or not 0<plan["confirmed_ms"]<=now<plan["expires_ms"] or not 0<plan["expires_ms"]-plan["confirmed_ms"]<=7*DAY:
        raise ValueError("plan_unconfirmed")
    if not isinstance(usage,(tuple,list)) or len(usage)!=2:raise ValueError("usage_unknown")
    if not isinstance(storage,dict) or storage.get("status")!="OK":raise ValueError("storage_unknown_or_warning")
    count,total,largest=storage["count"],storage["bytes"],storage["largest"]
    reads,writes=usage
    if any(type(x) is not int or x<0 for x in (count,total,largest,reads,writes)) or not 1<=count<=10 or largest>total or largest>=400000000 or total>=4000000000:
        raise ValueError("inventory")
    # "complete" means both read-only responses are available, not that estimates equal billing.
    return dict(scope="ACCOUNT_D1",plan="FREE",complete=True,checked_ms=min(analytics_ms,plan["expires_ms"]-HOUR),rows_read=reads,rows_written=writes,storage_bytes=total,databases=count)
def collect_sample(*,clock,plan,analytics_reader,storage_reader,storage_cache=None,authorized=False):
    """Dependency injection; use audited read-only readers, never a write-capable client.
    A storage cache may be reused within UTC day; no retry on a failed reader.
    No network entrypoint or credential configuration is installed by this module.
    """
    if authorized is not True:raise PermissionError("separate_read_approval_required")
    start=clock()
    if not isinstance(plan,dict) or plan.get("plan")!="FREE" or type(plan.get("confirmed_ms")) is not int or type(plan.get("expires_ms")) is not int or not 0<plan["confirmed_ms"]<=start<plan["expires_ms"] or not 0<plan["expires_ms"]-plan["confirmed_ms"]<=7*DAY:raise ValueError("plan_unconfirmed")
    if storage_cache is not None:
        stamp,storage=storage_cache
        if type(stamp) is not int or not 0<=start-stamp<=DAY or day(stamp)!=day(start):storage_cache=None
    if storage_cache is None:
        stamp=clock();storage=storage_reader()
    checked=clock();usage=analytics_reader(day(checked));now=clock()
    if day(start)!=day(now):raise ValueError("day_changed")
    return build_sample(now=now,analytics_ms=checked,usage=usage,storage_ms=stamp,storage=storage,plan=plan),(stamp,storage)
class Tests(unittest.TestCase):
    def setUp(self):
        self.t=1800000000000
        self.plan=dict(plan="FREE",confirmed_ms=self.t-1000,expires_ms=self.t+DAY)
        self.storage=dict(count=5,bytes=1000,largest=500,status="OK")
    def test_sample(self):
        a=build_sample(now=self.t,analytics_ms=self.t,usage=(100,20),storage_ms=self.t,storage=self.storage,plan=self.plan)
        self.assertEqual(a["rows_read"],100)
        with self.assertRaises(ValueError):build_sample(now=self.t,analytics_ms=self.t,usage=None,storage_ms=self.t,storage=self.storage,plan=self.plan)
    def test_denied_no_reader(self):
        def forbidden(*a):raise AssertionError("called")
        with self.assertRaises(PermissionError):collect_sample(clock=lambda:self.t,plan=self.plan,analytics_reader=forbidden,storage_reader=forbidden)
    def test_cached_storage(self):
        def forbidden():raise AssertionError("called")
        sample,_=collect_sample(clock=lambda:self.t,plan=self.plan,analytics_reader=lambda d:(100,20),storage_reader=forbidden,storage_cache=(self.t,self.storage),authorized=True)
        self.assertEqual(sample["databases"],5)
if __name__=="__main__":unittest.main()
