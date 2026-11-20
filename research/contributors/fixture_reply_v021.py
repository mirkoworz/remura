# REMURA Experience v0.21 LAB — 20/11/2026 CET
# Generate an actual v0.20 response using three temporary SQLite files.
import json
import tempfile
from pathlib import Path
from snapshot_v020 import SnapshotV020
from test_snapshot_store_v019 import data, OWNER, USER, YES, NOW

with tempfile.TemporaryDirectory() as root:
    f=SnapshotV020(Path(root)/'fixture'); f.initialize_snapshot()
    x=data(); x['prices'][0]['observed_at']='2026-11-20T15:45:00Z'
    assert f.publish_snapshot(0,x,OWNER,YES,lambda:NOW)=='PUBLISHED'
    fresh=f.deliver(USER,lambda:NOW); stale=f.deliver(USER,lambda:NOW+1)
    assert fresh and stale
    print(json.dumps({'now':NOW,'fresh':fresh,'stale':stale}))
