"""V31.2 LAB fail-closed timer entry. Not installed."""
import os,sys
from v312_collector_tick import BASE,tick,old
def main():
    os.umask(0o077)
    old.check_private(BASE,True)
    try:
        print("V312 COLLECTOR",tick(),flush=True)
    except Exception as e:
        stop=BASE/"v312-collector-STOP"
        if not os.path.lexists(stop):
            with stop.open("x") as f:
                f.write("MANUAL_REVIEW_REQUIRED\n");f.flush();os.fsync(f.fileno())
        print("V312 STOP",type(e).__name__,flush=True)
        return 2
    return 0
if __name__=="__main__":sys.exit(main())
