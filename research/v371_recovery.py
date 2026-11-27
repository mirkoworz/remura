"""REMURA V37.1, 2026-11-27 CET. Offline recovery planner, no writes.
Calendar intervals are supplied only after source-specific verification.
No fabricated bars, no horizon shifts, no prospective admission.
"""
import json, sqlite3, sys, time, unittest
from pathlib import Path
from contextlib import closing
from collections import Counter
from bisect import bisect_left, bisect_right
M5=300000
HOUR=3600000
HOURS=(1,4,24)
COSTS={0,1,2}
GRACE=48*HOUR
BASE=Path.home()/'.remura-v296'

def coverage(entry,hours,now,closes,calendar=()):
    if type(entry) is not int or entry<=0 or entry%M5 or hours not in HOURS:
        raise ValueError('scope')
    end=entry+hours*HOUR
    if end>now:return 'PENDING',0
    missing=[t for t in range(entry+M5,end+1,M5) if t not in closes]
    if not missing:return 'READY',0
    def state(t):
        matches={status for a,b,status in calendar if a<=t-M5 and t<=b}
        return next(iter(matches)) if len(matches)==1 else 'UNKNOWN'
    states={state(t) for t in missing}
    if states=={'CLOSED'}:status='DOCUMENTED_CLOSURE_GAP'
    elif states=={'OPEN'}:status='OPEN_SESSION_GAP'
    elif 'UNKNOWN' in states:status='UNVERIFIED_SESSION_GAP'
    else:status='MIXED_SESSION_GAP'
    return status,len(missing)

def jobs(db,multi):
    obs='v318_observations' if multi else 'observations'
    out='v318_outcomes' if multi else 'outcomes'
    entry='o.entry_ms' if multi else "CAST(json_extract(o.packet,'$.entry_ms') AS INTEGER)"
    terminal='0' if multi else 'EXISTS(SELECT 1 FROM terminal_missing t WHERE t.id=o.id AND t.hours=h.hours)'
    sql=f'''WITH h(hours) AS (VALUES(1),(4),(24)), c(cost) AS (VALUES(0),(1),(2))
      SELECT o.id,{entry},h.hours,c.cost,{terminal} FROM {obs} o CROSS JOIN h CROSS JOIN c
      LEFT JOIN {out} x ON x.id=o.id AND x.hours=h.hours AND x.cost=c.cost
      WHERE x.id IS NULL ORDER BY 2,3,4'''
    for row in db.execute(sql):yield row

def plan(rows,closes,now,calendar=(),limit=32):
    if type(limit) is not int or not 2<=limit<=32:raise ValueError('limit')
    groups={}
    for ident,entry,h,c,terminal in rows:
        if c not in COSTS or terminal not in (0,1):raise ValueError('job')
        key=(ident,entry,h)
        costs,old=groups.setdefault(key,(set(),terminal))
        if old!=terminal or c in costs:raise ValueError('duplicate')
        costs.add(c)
    counts={h:Counter() for h in HOURS};recent=[];older=[]
    for (ident,entry,h),(costs,terminal) in groups.items():
        status,n=coverage(entry,h,now,closes,calendar)
        end=entry+h*HOUR
        counts[h][status]+=1
        if end<=now-GRACE:counts[h]['OVER_48H']+=1
        if terminal:counts[h]['PREVIOUS_TERMINAL_MARKER']+=1
        if status=='READY':
            item=(ident,entry,h,tuple(sorted(costs)),bool(terminal))
            (older if end<=now-GRACE else recent).append(item)
    order=lambda x:(x[1]+x[2]*HOUR,x[1],x[0])
    recent.sort(key=order);older.sort(key=order)
    # Reserve a quarter of the batch for old ready jobs; unused capacity shared.
    reserve=max(1,limit//4)
    selected=older[:reserve]+recent[:limit-reserve]
    if len(selected)<limit:
        selected+=older[reserve:reserve+limit-len(selected)]
    if len(selected)<limit:
        selected+=recent[limit-reserve:limit-reserve+limit-len(selected)]
    return {'counts':{str(h):dict(c) for h,c in counts.items()},
            'ready_total':len(recent)+len(older),'selected':selected,
            'prospective_admitted':False}

def report():
    now=int(time.time()*1000)
    def ro(p):
        db=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True,timeout=3)
        db.execute('PRAGMA query_only=ON');return db
    with closing(ro(BASE/'v312/science-tv.sqlite3')) as s, closing(ro(BASE/'v318/multifactor.sqlite3')) as m:
        s.execute('BEGIN');m.execute('BEGIN')
        closes={t for (t,) in s.execute('SELECT close_ms FROM events WHERE close_ms<=? AND received_ms<=? AND seen_ms<=?',(now,now,now))}
        if any(type(t) is not int or t%M5 for t in closes):raise ValueError('source_grid')
        result={}
        for name,db,multi in [('science',s,False),('multifactor',m,True)]:
            p=plan(jobs(db,multi),closes,now)
            selected=p.pop('selected')
            p['selected_horizons']=len(selected)
            p['selected_cost_rows']=sum(len(x[3]) for x in selected)
            p['selected_previously_terminal']=sum(x[4] for x in selected)
            result[name]=p
        return {'version':'V37.1','asof_ms':now,'calendar':'UNVERIFIED','read_only':True,**result}

class Tests(unittest.TestCase):
    def test_gap_and_calendar(self):
        e=24*HOUR;now=e+HOUR;bars=set(range(e+M5,now+1,M5));bars.remove(e+M5)
        self.assertEqual(coverage(e,1,now,bars),('UNVERIFIED_SESSION_GAP',1))
        self.assertEqual(coverage(e,1,now,bars,[(e,e+M5,'CLOSED')]),('DOCUMENTED_CLOSURE_GAP',1))
        self.assertEqual(coverage(e,1,now,bars,[(e,e+M5,'OPEN')]),('OPEN_SESSION_GAP',1))
        self.assertEqual(coverage(e,1,now,bars,[(e,e+M5,'OPEN'),(e,e+M5,'CLOSED')]),('UNVERIFIED_SESSION_GAP',1))
        self.assertEqual(coverage(e,1,now-1,bars),('PENDING',0))
    def test_old_gap_does_not_block(self):
        old=HOUR;new=100*HOUR;now=new+HOUR
        rows=[('gap',old,1,0,1),('new',new,1,1,0),('old',old+HOUR,1,2,1)]
        bars=set(range(new+M5,now+1,M5))|set(range(old+HOUR+M5,old+2*HOUR+1,M5))
        p=plan(rows,bars,now,limit=2)
        self.assertEqual([x[0] for x in p['selected']],['old','new'])
        self.assertEqual(p['counts']['1']['OVER_48H'],2)
    def test_partial_costs_and_no_shift(self):
        e=HOUR;now=e+HOUR;bars=set(range(e+M5,now+1,M5))
        p=plan([('x',e,1,2,0),('x',e,1,0,0)],bars,now)
        self.assertEqual(p['selected'][0][3],(0,2))
        bars.remove(now);bars.add(now+M5)
        self.assertEqual(plan([('x',e,1,0,0)],bars,now+M5)['ready_total'],0)
    def test_real_schema_queries(self):
        with closing(sqlite3.connect(':memory:')) as db:
            db.executescript('''CREATE TABLE observations(id,packet);CREATE TABLE outcomes(id,hours,cost);CREATE TABLE terminal_missing(id,hours);CREATE TABLE v318_observations(id,entry_ms);CREATE TABLE v318_outcomes(id,hours,cost);''')
            db.execute('INSERT INTO observations VALUES(?,?)',('x',json.dumps({'entry_ms':HOUR})))
            db.execute('INSERT INTO terminal_missing VALUES(?,?)',('x',1))
            db.execute('INSERT INTO outcomes VALUES(?,?,?)',('x',1,0))
            db.execute('INSERT INTO v318_observations VALUES(?,?)',('y',HOUR))
            self.assertEqual(list(jobs(db,False))[:2],[('x',HOUR,1,1,1),('x',HOUR,1,2,1)])
            self.assertEqual(len(list(jobs(db,True))),9)

if __name__=='__main__':
    if sys.argv[1:]==['--selftest']:unittest.main(argv=[sys.argv[0]])
    elif sys.argv[1:]==['--report']:print(json.dumps(report(),sort_keys=True))
    else:raise SystemExit('--selftest | --report')
