# REMURA Experience v0.16 LAB — 20/11/2026, 17:50 CET
import hashlib
import sqlite3
import tempfile
import unittest
from pathlib import Path
from witness_v016 import EMPTY, advance, checked_payload, open_witness, read

KEY = b'w' * 32 # synthetic only
A, B = b'fixture-one', b'fixture-two'
P1 = (1, 'a'*64, hashlib.sha256(A).hexdigest())
P2 = (2, 'b'*64, hashlib.sha256(B).hexdigest())


class WitnessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'witness.sqlite'
        self.db = open_witness(self.path, KEY, create=True)

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def publish(self):
        self.assertTrue(advance(self.db, KEY, EMPTY, P1, True))

    def serve(self, pin=P1, body=A, allowed=True):
        return checked_payload(self.db, KEY, pin[:2], pin[0], body, allowed)

    def test_empty(self):
        self.assertEqual(read(self.db, KEY), EMPTY)
        self.assertIsNone(self.serve())

    def test_reopen(self):
        self.publish()
        self.db.close()
        self.db = open_witness(self.path, KEY)
        self.assertEqual(read(self.db, KEY), P1)
        self.assertEqual(self.serve(), A)

    def test_both_primary_copies_rolled_back(self):
        self.publish()
        self.assertTrue(advance(self.db, KEY, P1, P2, True))
        self.assertIsNone(self.serve())
        self.assertEqual(self.serve(P2, B), B)

    def test_interrupted_publication(self):
        self.publish()
        self.assertIsNone(self.serve(P2, B))
        self.assertEqual(read(self.db, KEY), P1)

    def test_archive_digest(self):
        self.publish()
        self.assertIsNone(self.serve(body=B))

    def test_journal_tag(self):
        self.publish()
        self.assertIsNone(self.serve((1, 'c'*64, P1[2])))

    def test_archive_revision(self):
        self.publish()
        self.assertIsNone(checked_payload(self.db, KEY, P1[:2], 2, A, True))

    def test_access_denied(self):
        self.publish()
        self.assertIsNone(self.serve(allowed=False))
        self.assertIsNone(self.serve(allowed=1))

    def test_cas_stale(self):
        self.publish()
        other = open_witness(self.path, KEY)
        try:
            self.assertFalse(advance(other, KEY, EMPTY, P1, True))
        finally:
            other.close()

    def test_skip_revision(self):
        self.assertFalse(advance(self.db, KEY, EMPTY, P2, True))

    def test_no_approval(self):
        self.assertFalse(advance(self.db, KEY, EMPTY, P1, False))
        self.assertFalse(advance(self.db, KEY, EMPTY, P1, 1))

    def test_wrong_key(self):
        self.publish()
        self.assertIsNone(checked_payload(self.db, b'x'*32, P1[:2], 1, A, True))

    def test_tampered_witness(self):
        self.publish()
        self.db.execute('UPDATE witness SET rev=2')
        self.assertIsNone(self.serve())
        self.assertFalse(advance(self.db, KEY, P1, P2, True))

    def test_deleted_witness_record(self):
        self.db.execute('DELETE FROM witness')
        self.assertIsNone(self.serve())

    def test_missing_file_no_reinitialization(self):
        missing = Path(self.tmp.name) / 'missing.sqlite'
        with self.assertRaises(ValueError):
            open_witness(missing, KEY)
        self.assertFalse(missing.exists())

    def test_closed_authority(self):
        self.db.close()
        self.assertIsNone(self.serve())

    def test_full_witness_rollback_is_unresolved(self):
        self.publish()
        old = sqlite3.connect(':memory:')
        try:
            self.db.backup(old)
            self.assertTrue(advance(self.db, KEY, P1, P2, True))
            # If the witness itself is restored, authentication alone cannot detect it.
            self.assertEqual(checked_payload(old, KEY, P1[:2], 1, A, True), A)
        finally:
            old.close()


if __name__ == '__main__':
    unittest.main()
