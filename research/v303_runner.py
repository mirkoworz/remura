"""REMURA V30.3 — 26/11/2026 Europe/Rome.
Finite 24-hour owner-authorized run. No installation or activation on import.
"""
import os,time,sys,subprocess,json
from pathlib import Path
from v302_backfill import BASE,old,clock
MAX_TICKS=288
PERIOD=300

def next_action(p,now,done):
    if type(done) is not int or not 0<=done<=MAX_TICKS:
        raise ValueError("counter")
    if (type(p.get("start_ms")) is not int or type(p.get("end_ms")) is not int
        or not 0<p["end_ms"]-p["start_ms"]<=86400000
        or p.get("enabled") is not True or p.get("free_confirmed") is not True
        or now<p["start_ms"]):
        raise ValueError("permit")
    return done<MAX_TICKS and now+100000<p["end_ms"]

def run():
    os.umask(0o077)
    old.check_private(BASE,True)
    permit=BASE/"v302-live-permit.json"
    p=old.read_private(permit)
    marker=BASE/"v303-run-attempt.lock"
    stop=BASE/"v302-live-STOP"
    with marker.open("x") as f:
        f.write("ONE_SHOT\n");f.flush();os.fsync(f.fileno())
    done=0
    try:
        while next_action(p,clock(),done) and not stop.exists():
            if old.read_private(permit)!=p:raise ValueError("permit_changed")
            started=time.monotonic()
            result=subprocess.run([sys.executable,"-B",str(BASE/"v301"/"v303_live_tick.py")],timeout=90)
            if result.returncode!=0:raise ValueError("tick_failed")
            done+=1
            print("V303 CICLI",done,flush=True)
            if done<MAX_TICKS:
                time.sleep(max(0,min(PERIOD-(time.monotonic()-started),(p["end_ms"]-clock()-100000)/1000)))
        print("V303 FINE",done,flush=True)
    finally:
        # Completion or failure: do not allow further automatic network.
        if not os.path.lexists(stop):
            with stop.open("x") as f:f.write("V303_CLOSED\n")
if __name__=="__main__":
    try:run()
    except Exception as e:
        print("V303 STOP",type(e).__name__,flush=True);sys.exit(2)
