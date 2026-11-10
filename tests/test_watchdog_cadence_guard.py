"""Broker quota / collector schedule safety tests; offline, fail closed."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from watchdog_cadence_guard import inspect_cadence


class WatchdogCadenceGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / "scripts/private_server.py").read_text("utf-8")

    def check(self, altered):
        return inspect_cadence(altered)

    def test_real_pr99_preserves_two_broker_call_sites_and_quarter_wait(self):
        result = self.check(self.source)
        self.assertEqual(result["state"], "STATIC_REVIEW_REQUIRED")
        self.assertEqual(result["violations"], ())
        self.assertFalse(result["release_authorized"])

    def test_additional_primary_broker_call_is_blocked(self):
        before = "            primary=collect_once(db_path,group,days=days)"
        self.assertIn(before, self.source)
        candidate = self.source.replace(before, before + "\n" + before)
        self.assertIn("BROKER_CALL_SITE_DRIFT", self.check(candidate)["violations"])

    def test_additional_backup_broker_call_is_blocked(self):
        before = 'fallback=collect_once(db_path,subset,days=horizon,source="backup")'
        self.assertIn(before, self.source)
        candidate = self.source.replace(before, before + "\n                        " + before)
        self.assertIn("BROKER_CALL_SITE_DRIFT", self.check(candidate)["violations"])

    def test_quarter_wait_must_stay_bounded_to_original_scheduler(self):
        before = "stop.wait(seconds_to_next_quarter())"
        self.assertIn(before, self.source)
        candidate = self.source.replace(before, "stop.wait(5)")
        self.assertIn("QUARTER_WAIT_DRIFT", self.check(candidate)["violations"])

    def test_additional_timer_call_is_blocked(self):
        before = "        stop.wait(seconds_to_next_quarter())"
        candidate = self.source.replace(before, "        time.sleep(1)\n" + before)
        self.assertIn("EXTRA_TIMER_IN_COLLECTOR", self.check(candidate)["violations"])

    def test_progress_completion_marker_cannot_disappear(self):
        before = "progress.mark_completed()"
        self.assertIn(before, self.source)
        candidate = self.source.replace(before, "progress.do_nothing()")
        self.assertIn("PROGRESS_WITNESS_DRIFT", self.check(candidate)["violations"])

    def test_priority_source_switch_cannot_be_lost(self):
        before = '"REMURA_PRIORITY_COLLECTOR_ENABLED"'
        self.assertIn(before, self.source)
        candidate = self.source.replace(before, '"FAKE_PRIORITY_ENABLED"')
        self.assertIn("PRIORITY_OPTIN_OR_BATCH_PLAN_DRIFT", self.check(candidate)["violations"])

    def test_health_get_must_not_call_broker(self):
        before = "        def do_GET(self):\n"
        self.assertIn(before, self.source)
        candidate = self.source.replace(before, before + "            collect_once('fake', [], days=1)\n")
        self.assertIn("BROKER_OR_WORKER_IN_HTTP", self.check(candidate)["violations"])

    def test_new_collector_thread_call_site_is_blocked(self):
        before = "thread=threading.Thread(target=collector_loop,args=(db_path,stop),"
        self.assertIn(before, self.source)
        candidate = self.source.replace(before, before.replace("thread=", "other_thread=") +
                                        "\n        " + before)
        self.assertIn("COLLECTOR_THREAD_OR_PROGRESS_START_DRIFT", self.check(candidate)["violations"])

    def test_invalid_source_fails_closed(self):
        self.assertEqual(self.check("def broken(:")["state"], "INVALID_SYNTAX")
        self.assertEqual(inspect_cadence(None)["state"], "INVALID_INPUT")

    def test_no_execute_network_or_live_operations_in_guard(self):
        content = (ROOT / "scripts/watchdog_cadence_guard.py").read_text("utf-8")
        for forbidden in ("subprocess", "requests", "urlopen", "socket",
                          "systemctl", "/opt/remura", "import os", "exec(",
                          "time.sleep", "if __name__"):
            self.assertNotIn(forbidden, content)


if __name__ == "__main__":
    unittest.main()
