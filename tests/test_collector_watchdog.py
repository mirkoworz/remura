"""Pure, offline watchdog tests. No database, server, broker or cloud actions."""
import datetime as dt
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from collector_watchdog import CYCLE_GAP_MINUTES, CycleProgress, RECENT_MINUTES, SCHEMA, snapshot

UTC = dt.timezone.utc
NOW = dt.datetime(2026, 11, 9, 9, 15, tzinfo=UTC)


class WatchdogOfflineTests(unittest.TestCase):
    def snap(self, *, enabled=True, thread=None, stamp=None, now=NOW, progress=None):
        return snapshot(enabled=enabled, thread=thread,
                        last_success=stamp, now=now, progress=progress)

    def test_schema_is_explicit_and_never_enables_restart(self):
        out = self.snap(enabled=False)
        self.assertEqual(out["schema"], SCHEMA)
        self.assertEqual(out["action"], "observe_only")
        self.assertIs(out["autoRestart"], False)

    def test_disabled_is_not_a_failure(self):
        thread = Mock()
        out = self.snap(enabled=False, thread=thread)
        self.assertEqual(out["threadState"], "disabled")
        self.assertEqual(out["latestBatch"], "unknown")
        thread.is_alive.assert_not_called()

    def test_no_reference_is_unknown_not_dead(self):
        self.assertEqual(self.snap()["threadState"], "unknown")

    def test_alive_recent_batch_is_not_broker_proof(self):
        thread = Mock(is_alive=lambda: True)
        out = self.snap(thread=thread, stamp="2026-11-09T09:00:00Z")
        self.assertEqual(out["threadState"], "running")
        self.assertEqual(out["latestBatch"], "recent")
        self.assertEqual(out["batchAgeMinutes"], 15)

    def test_stopped_worker_detected_even_with_recent_db_success(self):
        out = self.snap(thread=Mock(is_alive=lambda: False),
                        stamp="2026-11-09T09:13:00+00:00")
        self.assertEqual(out["threadState"], "stopped")
        self.assertEqual(out["latestBatch"], "recent")

    def test_old_batch_does_not_prove_worker_stopped(self):
        out = self.snap(thread=Mock(is_alive=lambda: True),
                        stamp="2026-11-06T15:00:00+00:00")
        self.assertEqual(out["threadState"], "running")
        self.assertEqual(out["latestBatch"], "old_or_market_closed")

    def test_boundary_45_minutes(self):
        stamp = (NOW - dt.timedelta(minutes=RECENT_MINUTES)).isoformat()
        out = self.snap(thread=Mock(is_alive=lambda: True), stamp=stamp)
        self.assertEqual(out["latestBatch"], "recent")
        stamp = (NOW - dt.timedelta(minutes=RECENT_MINUTES, seconds=1)).isoformat()
        out = self.snap(thread=Mock(is_alive=lambda: True), stamp=stamp)
        self.assertEqual(out["latestBatch"], "recent")  # integer minute only
        stamp = (NOW - dt.timedelta(minutes=RECENT_MINUTES + 1)).isoformat()
        out = self.snap(thread=Mock(is_alive=lambda: True), stamp=stamp)
        self.assertEqual(out["latestBatch"], "old_or_market_closed")

    def test_missing_invalid_and_naive_times_are_unknown(self):
        worker = Mock(is_alive=lambda: True)
        for stamp in (None, "", "not-a-date", "2026-11-09T09:00:00",
                      "x" * 500, "2026-99-01T00:00:00Z"):
            with self.subTest(stamp=str(stamp)[:25]):
                out = self.snap(thread=worker, stamp=stamp)
                self.assertEqual(out["latestBatch"], "unknown")
                self.assertIsNone(out["batchAgeMinutes"])

    def test_future_timestamp_never_claims_freshness(self):
        out = self.snap(thread=Mock(is_alive=lambda: True),
                        stamp="2026-11-09T09:16:00Z")
        self.assertEqual(out["latestBatch"], "unknown")

    def test_worker_liveness_error_does_not_break_health(self):
        thread = Mock()
        thread.is_alive.side_effect = RuntimeError("sensitive internal diagnostic")
        self.assertEqual(self.snap(thread=thread)["threadState"], "unknown")

    def test_nonboolean_worker_liveness_is_not_trusted(self):
        self.assertEqual(self.snap(thread=Mock(is_alive=lambda: "true"))["threadState"], "unknown")

    def test_unexpected_config_is_disabled(self):
        for enabled in (None, False, "1", 1):
            self.assertEqual(self.snap(enabled=enabled)["threadState"], "disabled")

    def test_offset_time_is_normalized_to_utc(self):
        out = self.snap(thread=Mock(is_alive=lambda: True),
                        stamp="2026-11-09T10:00:00+01:00")
        self.assertEqual(out["batchAgeMinutes"], 15)

    def test_no_credentials_or_private_values_in_result(self):
        out = self.snap(thread=Mock(is_alive=lambda: True),
                        stamp="sensitive-token-should-not-be-printed")
        self.assertEqual(set(out), {"schema", "threadState", "latestBatch", "batchAgeMinutes", "progressState", "progressAgeMinutes", "autoRestart", "action"})
        self.assertNotIn("sensitive-token", str(out))

    def test_naive_reference_time_rejected(self):
        with self.assertRaises(ValueError):
            self.snap(thread=Mock(is_alive=lambda: True), now=dt.datetime(2026, 11, 9))


class FakeClock:
    def __init__(self, seconds=1000):
        self.seconds = seconds

    def __call__(self):
        return self.seconds


class ProgressWatchdogOfflineTests(unittest.TestCase):
    def snapshot(self, progress, *, enabled=True, alive=True):
        return snapshot(enabled=enabled, thread=Mock(is_alive=lambda: alive),
                        last_success=None, now=NOW, progress=progress)

    def test_incomplete_first_cycle_uses_start_time_not_stale_prices(self):
        clock = FakeClock()
        progress = CycleProgress(clock=clock)
        out = self.snapshot(progress)
        self.assertEqual(out["progressState"], "awaiting_first_cycle")
        self.assertEqual(out["progressAgeMinutes"], 0)
        self.assertEqual(out["latestBatch"], "unknown")
        clock.seconds += (CYCLE_GAP_MINUTES + 1) * 60
        self.assertEqual(self.snapshot(progress)["progressState"], "first_cycle_overdue")

    def test_completed_cycle_uses_monotonic_progress_even_without_saved_prices(self):
        clock = FakeClock()
        progress = CycleProgress(clock=clock)
        clock.seconds += 10 * 60
        progress.mark_completed()
        clock.seconds += 3 * 60
        out = self.snapshot(progress)
        self.assertEqual(out["progressState"], "recent_cycle")
        self.assertEqual(out["progressAgeMinutes"], 3)
        self.assertEqual(out["latestBatch"], "unknown")

    def test_alive_thread_without_completed_cycle_in_over_one_hour_is_advisory(self):
        clock = FakeClock()
        progress = CycleProgress(clock=clock)
        progress.mark_completed()
        clock.seconds += (CYCLE_GAP_MINUTES + 1) * 60
        out = self.snapshot(progress)
        self.assertEqual(out["threadState"], "running")
        self.assertEqual(out["progressState"], "no_recent_cycle")
        self.assertFalse(out["autoRestart"])
        self.assertEqual(out["action"], "observe_only")

    def test_stopped_thread_takes_precedence_over_old_cycle_age(self):
        clock = FakeClock()
        progress = CycleProgress(clock=clock)
        progress.mark_completed()
        clock.seconds += 100 * 60
        out = self.snapshot(progress, alive=False)
        self.assertEqual(out["progressState"], "stopped")
        self.assertIsNone(out["progressAgeMinutes"])

    def test_disabled_worker_does_not_read_progress(self):
        clock = Mock()
        progress = CycleProgress(clock=lambda: 2)
        progress._clock = clock
        out = self.snapshot(progress, enabled=False)
        self.assertEqual(out["progressState"], "disabled")
        clock.assert_not_called()

    def test_unknown_progress_omits_unverified_claim(self):
        out = self.snapshot(progress=None)
        self.assertEqual(out["progressState"], "unknown")
        self.assertIsNone(out["progressAgeMinutes"])

    def test_bad_or_rolling_backward_monotonic_clock_fails_closed(self):
        clock = FakeClock()
        progress = CycleProgress(clock=clock)
        clock.seconds -= 3
        self.assertEqual(self.snapshot(progress)["progressState"], "unknown")
        clock.seconds = float("nan")
        self.assertEqual(self.snapshot(progress)["progressState"], "unknown")

    def test_monitoring_failure_never_aborts_a_real_batch(self):
        clock = FakeClock()
        progress = CycleProgress(clock=clock)
        def broken():
            raise RuntimeError("internal-monitor-error")
        progress._clock = broken
        progress.mark_completed()
        self.assertEqual(self.snapshot(progress)["progressState"], "unknown")

    def test_mark_only_after_completed_cycle(self):
        clock = FakeClock()
        progress = CycleProgress(clock=clock)
        self.assertEqual(progress.age_minutes(), (0, False))
        progress.mark_completed()
        self.assertEqual(progress.age_minutes(), (0, True))


if __name__ == "__main__":
    unittest.main()
