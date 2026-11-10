"""Offline HTTP integration checks for the private collector watchdog.

Requires full REMURA checkout; never connects to broker, Oracle or remote VPS.
"""
import datetime as dt
import json
from http.server import ThreadingHTTPServer
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch
from urllib.request import urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import private_server as server
import price_store
from collector_watchdog import CycleProgress

UTC = dt.timezone.utc


class WatchdogHTTPTests(unittest.TestCase):
    def test_health_surfaces_stopped_worker_without_restart_or_broker(self):
        now = dt.datetime(2026, 11, 9, 9, 0, tzinfo=UTC)
        with tempfile.TemporaryDirectory() as folder:
            dbpath = Path(folder) / "private" / "prices.sqlite"
            db = price_store.connect(dbpath)
            try:
                price_store.set_status(db, collector="running",
                                       last_success=(now - dt.timedelta(minutes=10)).isoformat())
            finally:
                db.close()
            worker = Mock(is_alive=lambda: False)
            with patch.dict(server.os.environ, {"REMURA_COLLECTOR_ENABLED": "1"}), \
                 patch.object(server, "utcnow", return_value=now), \
                 patch.object(server, "collect_once", side_effect=AssertionError("broker must not be called")):
                site = ThreadingHTTPServer(("127.0.0.1", 0), server.http_handler(dbpath, collector_thread=worker))
                runner = threading.Thread(target=site.serve_forever, daemon=True)
                runner.start()
                try:
                    base = f"http://127.0.0.1:{site.server_address[1]}"
                    with urlopen(base + "/private-api/health", timeout=5) as response:
                        data = json.load(response)
                    self.assertEqual(data["collector"], "running")
                    self.assertEqual(data["collectorWatchdog"]["threadState"], "stopped")
                    self.assertEqual(data["collectorWatchdog"]["latestBatch"], "recent")
                    self.assertFalse(data["collectorWatchdog"]["autoRestart"])
                    self.assertEqual(data["collectorWatchdog"]["action"], "observe_only")
                finally:
                    site.shutdown()
                    site.server_close()
                    runner.join(timeout=5)

    def test_disabled_collector_is_not_false_alarm(self):
        now = dt.datetime(2026, 11, 9, 9, 0, tzinfo=UTC)
        with tempfile.TemporaryDirectory() as folder:
            dbpath = Path(folder) / "private" / "prices.sqlite"
            db = price_store.connect(dbpath)
            db.close()
            with patch.dict(server.os.environ, {"REMURA_COLLECTOR_ENABLED": "0"}), \
                 patch.object(server, "utcnow", return_value=now):
                site = ThreadingHTTPServer(("127.0.0.1", 0), server.http_handler(dbpath))
                runner = threading.Thread(target=site.serve_forever, daemon=True)
                runner.start()
                try:
                    with urlopen(f"http://127.0.0.1:{site.server_address[1]}/private-api/health", timeout=5) as response:
                        data = json.load(response)
                    self.assertEqual(data["collectorWatchdog"]["threadState"], "disabled")
                    self.assertEqual(data["collectorWatchdog"]["latestBatch"], "unknown")
                finally:
                    site.shutdown()
                    site.server_close()
                    runner.join(timeout=5)


class CycleProgressHTTPTests(unittest.TestCase):
    def test_health_reports_thread_alive_but_no_recent_completed_cycle(self):
        clock = [1000]
        progress = CycleProgress(clock=lambda: clock[0])
        progress.mark_completed()
        clock[0] += 65 * 60
        now = dt.datetime(2026, 11, 10, 9, 0, tzinfo=UTC)
        with tempfile.TemporaryDirectory() as folder:
            dbpath = Path(folder) / "private" / "prices.sqlite"
            db = price_store.connect(dbpath)
            db.close()
            worker = Mock(is_alive=lambda: True)
            with patch.dict(server.os.environ, {"REMURA_COLLECTOR_ENABLED": "1"}), \\
                 patch.object(server, "utcnow", return_value=now), \\
                 patch.object(server, "collect_once", side_effect=AssertionError("no broker on GET")):
                site = ThreadingHTTPServer(("127.0.0.1", 0),
                    server.http_handler(dbpath, collector_thread=worker,
                                        collector_progress=progress))
                thread = threading.Thread(target=site.serve_forever, daemon=True)
                thread.start()
                try:
                    with urlopen(f"http://127.0.0.1:{site.server_address[1]}/private-api/health",
                                 timeout=5) as response:
                        data = json.load(response)
                    self.assertEqual(data["collectorWatchdog"]["threadState"], "running")
                    self.assertEqual(data["collectorWatchdog"]["progressState"], "no_recent_cycle")
                    self.assertEqual(data["collectorWatchdog"]["progressAgeMinutes"], 65)
                    self.assertEqual(data["collectorWatchdog"]["action"], "observe_only")
                finally:
                    site.shutdown()
                    site.server_close()
                    thread.join(timeout=5)

    def test_real_collector_loop_marks_completion_without_broker_requests(self):
        clock = [1000]
        progress = CycleProgress(clock=lambda: clock[0])
        class OneShotStop:
            def __init__(self):
                self.done = False
            def is_set(self):
                return self.done
            def wait(self, seconds):
                self.done = True
        stop = OneShotStop()
        with tempfile.TemporaryDirectory() as folder:
            dbpath = Path(folder) / "prices.sqlite"
            db = price_store.connect(dbpath)
            db.close()
            with patch.dict(server.os.environ, {
                    "REMURA_SYMBOLS": "EURUSD",
                    "REMURA_BATCH_TIMING_ENABLED": "0",
                    "REMURA_PRIORITY_COLLECTOR_ENABLED": "0"}), \\
                 patch.object(server, "collect_once", return_value={"saved": {}, "errors": {}}) as broker, \\
                 patch.object(server, "seconds_to_next_quarter", return_value=1):
                server.collector_loop(dbpath, stop, progress=progress)
            self.assertTrue(stop.done)
            self.assertEqual(broker.call_count, 1)
            self.assertEqual(progress.age_minutes(), (0, True))


if __name__ == "__main__":
    unittest.main()
