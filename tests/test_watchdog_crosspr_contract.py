"""Synthetic-only fail-closed contract for any future integrated PR candidate.

The current PR #99 intentionally fails the 3-way candidate gate; that is safe.
"""
import hashlib
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from watchdog_crosspr_contract import inspect_candidate


CANDIDATE = """
from collector_watchdog import CycleProgress, snapshot as collector_watchdog_snapshot
from storage_cache_v165 import StorageMetadataCache

def collect_once(*, research_ingest_first_seen=False):
    return ingest(research_parent_read_at="test")

def retail_once(*, research_retail_first_seen=False,
                research_retail_numeric_features=False):
    return retail_research.capture_pair()

def observe_periodic_squalincome():
    return ("REMURA_SHARK_COMPACT_RESEARCH_ENABLED",
            "REMURA_SHARK_COMPACT_RESEARCH_ACK")

def squalincome_loop():
    return observe_periodic_squalincome()

def collector_loop(*, progress=None):
    progress.mark_completed()

def http_handler(db_path, collector_thread=None, collector_progress=None):
    if "REMURA_STORAGE_DIAG_ENABLED":
        data["storageInventory"] = _STORAGE_CACHE.peek()
    return {"collectorWatchdog": collector_watchdog_snapshot(
        thread=collector_thread, progress=collector_progress)}

def main():
    if "REMURA_STORAGE_DIAG_ENABLED":
        _STORAGE_CACHE.start("db", "stop")
    progress = CycleProgress()
    collector_loop(progress=progress)
    return http_handler("db", collector_thread="thread", collector_progress=progress)
"""


def run(source):
    return inspect_candidate(source, hashlib.sha256(source.encode("utf-8")).hexdigest())


class CrossPrContractTests(unittest.TestCase):
    def test_purely_synthetic_combination_is_review_only(self):
        result = run(CANDIDATE)
        self.assertEqual(result["state"], "STRUCTURAL_REVIEW_REQUIRED")
        self.assertEqual(result["missing"], ())
        self.assertIs(result["release_authorized"], False)

    def test_current_watchdog_branch_is_not_falsely_marked_integrated(self):
        source = (ROOT / "scripts/private_server.py").read_text("utf-8")
        result = run(source)
        self.assertEqual(result["state"], "BLOCKED_MISSING_CONTRACTS")
        self.assertIn("B_INGEST_OPTIN", result["missing"])
        self.assertIn("V165_STORAGE_START", result["missing"])
        self.assertNotIn("WATCHDOG_IMPORT", result["missing"])
        self.assertNotIn("WATCHDOG_CYCLE_PROGRESS", result["missing"])
        self.assertIs(result["release_authorized"], False)

    def test_b_ingest_opt_in_must_default_false(self):
        result = run(CANDIDATE.replace("research_ingest_first_seen=False",
                                       "research_ingest_first_seen=True"))
        self.assertIn("B_INGEST_OPTIN", result["missing"])

    def test_b_price_ingest_parent_read_link_must_survive(self):
        result = run(CANDIDATE.replace("research_parent_read_at=", "timestamp="))
        self.assertIn("B_INGEST_OPTIN", result["missing"])

    def test_b_retail_flags_cannot_default_true(self):
        result = run(CANDIDATE.replace("research_retail_numeric_features=False",
                                       "research_retail_numeric_features=True"))
        self.assertIn("B_RETAIL_OPTIN", result["missing"])

    def test_b_observer_wiring_cannot_be_silently_dropped(self):
        result = run(CANDIDATE.replace("return observe_periodic_squalincome()",
                                       "return None"))
        self.assertIn("B_PERIODIC_RESEARCH_GUARD", result["missing"])

    def test_v165_cache_import_must_survive(self):
        result = run(CANDIDATE.replace("from storage_cache_v165 import StorageMetadataCache",
                                       "x = 1"))
        self.assertIn("V165_RESOURCES_CACHE", result["missing"])

    def test_v165_resources_guard_required(self):
        result = run(CANDIDATE.replace('"REMURA_STORAGE_DIAG_ENABLED":\n        data',
                                       '"DISABLED":\n        data'))
        self.assertIn("V165_RESOURCES_CACHE", result["missing"])

    def test_v165_cache_start_required(self):
        result = run(CANDIDATE.replace('_STORAGE_CACHE.start("db", "stop")',
                                       'pass'))
        self.assertIn("V165_STORAGE_START", result["missing"])

    def test_watchdog_import_required(self):
        result = run(CANDIDATE.replace(
            "from collector_watchdog import CycleProgress, snapshot as collector_watchdog_snapshot", "x = 1"))
        self.assertIn("WATCHDOG_IMPORT", result["missing"])

    def test_watchdog_health_field_required(self):
        result = run(CANDIDATE.replace('"collectorWatchdog":', '"collectorNotThere":'))
        self.assertIn("WATCHDOG_HEALTH_FIELD", result["missing"])

    def test_watchdog_thread_binding_required(self):
        result = run(CANDIDATE.replace('collector_thread="thread"', 'different="thread"'))
        self.assertIn("WATCHDOG_THREAD_WIRING", result["missing"])

    def test_watchdog_progress_import_is_required(self):
        result = run(CANDIDATE.replace(
            "from collector_watchdog import CycleProgress, snapshot as collector_watchdog_snapshot",
            "from collector_watchdog import snapshot as collector_watchdog_snapshot"))
        self.assertIn("WATCHDOG_CYCLE_PROGRESS", result["missing"])

    def test_watchdog_completed_cycle_must_be_recorded(self):
        result = run(CANDIDATE.replace("progress.mark_completed()", "pass"))
        self.assertIn("WATCHDOG_CYCLE_PROGRESS", result["missing"])

    def test_watchdog_progress_must_reach_health_response(self):
        result = run(CANDIDATE.replace("progress=collector_progress)",
                                       "not_progress=collector_progress)"))
        self.assertIn("WATCHDOG_CYCLE_PROGRESS", result["missing"])

    def test_watchdog_progress_must_be_passed_by_main(self):
        result = run(CANDIDATE.replace("collector_progress=progress)",
                                       "different=progress)"))
        self.assertIn("WATCHDOG_CYCLE_PROGRESS", result["missing"])

    def test_untrusted_or_wrong_pin_is_rejected(self):
        self.assertEqual(inspect_candidate(CANDIDATE, "0"*64)["state"], "UNPINNED_CANDIDATE")
        self.assertEqual(inspect_candidate(CANDIDATE, "Z"*64)["state"], "INVALID_INPUT")

    def test_bad_source_is_rejected(self):
        self.assertEqual(run("def x(:")["state"], "INVALID_SYNTAX")
        self.assertEqual(inspect_candidate(None, "0"*64)["state"], "INVALID_INPUT")

    def test_no_network_or_deploy_entrypoints_in_gate(self):
        module = (ROOT / "scripts/watchdog_crosspr_contract.py").read_text("utf-8")
        for marker in ("subprocess", "requests", "urlopen", "socket", "systemctl",
                       "SSH_", "os.system", "time.sleep", "/opt/remura"):
            self.assertNotIn(marker, module)


if __name__ == "__main__":
    unittest.main()
