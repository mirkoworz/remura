# REMURA Contributors v0.79 LAB — NEW exact source drift tests only.
from __future__ import annotations
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import json
import tempfile
import unittest

import staging_source_lock_v079_lab as lock


class LockedBlobCases(unittest.TestCase):
    pass


def blob_case(name):
    def case(self):
        self.assertTrue(lock.verify_blob(name,lock.LOCKED_BLOBS[name]))
    return case


for index, name in enumerate(lock.LOCKED_BLOBS):
    setattr(LockedBlobCases, f"test_{index+1:02d}_fixed_blob",blob_case(name))


class SourceContractCases(unittest.TestCase):
    def test_15_expected_14_paths_are_fixed(self):
        self.assertEqual(len(lock.LOCKED_BLOBS),14)

    def test_16_full_pinned_contract_matches(self):
        self.assertEqual(lock.verify_contract()["status"],"LAB_SOURCE_LOCK_MATCH")

    def test_17_contract_never_authorizes_deploy(self):
        self.assertIs(lock.verify_contract()["automatic_deploy_allowed"],False)

    def test_18_contract_does_not_attest_real_cloudflare(self):
        self.assertIs(lock.verify_contract()["production_runtime_attested"],False)

    def test_19_git_blob_hash_matches_known_public_vector(self):
        # Git blob SHA-1 for the three bytes 'abc'
        self.assertEqual(lock.git_blob_sha(b"abc"),"f2ba8f84ab5c1bce84a7b441cb1959cfc7093b7f")

    def test_20_git_blob_hash_changes_on_single_byte(self):
        self.assertNotEqual(lock.git_blob_sha(b"abc"),lock.git_blob_sha(b"abC"))

    def test_21_blob_must_be_binary(self):
        with self.assertRaises(lock.SourceLockError):
            lock.git_blob_sha("abc")

    def test_22_path_traversal_is_denied(self):
        with self.assertRaises(lock.SourceLockError):
            lock.checked_path("research/contributors/../private-secret.mjs")

    def test_23_absolute_paths_are_denied(self):
        with self.assertRaises(lock.SourceLockError):
            lock.checked_path("/etc/passwd")

    def test_24_backslash_escape_is_denied(self):
        with self.assertRaises(lock.SourceLockError):
            lock.checked_path("research\\contributors\\secret.mjs")

    def test_25_unexpected_file_extensions_are_denied(self):
        with self.assertRaises(lock.SourceLockError):
            lock.checked_path("research/contributors/.env")

    def test_26_other_repo_paths_are_denied(self):
        with self.assertRaises(lock.SourceLockError):
            lock.checked_path("private/contributors/a.mjs")

    def test_27_invalid_sha_hex_is_denied(self):
        path=next(iter(lock.LOCKED_BLOBS))
        with self.assertRaises(lock.SourceLockError):
            lock.verify_blob(path,"f"*39)

    def test_28_hash_drift_is_denied(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            p=root/"research/contributors/access_binding_candidate.mjs"
            p.parent.mkdir(parents=True)
            p.write_bytes(b"tampered")
            with self.assertRaises(lock.SourceLockError):
                lock.verify_blob("research/contributors/access_binding_candidate.mjs",
                                 lock.LOCKED_BLOBS["research/contributors/access_binding_candidate.mjs"],root=root)

    def test_29_missing_file_denied(self):
        with tempfile.TemporaryDirectory() as temp:
            name=next(iter(lock.LOCKED_BLOBS))
            with self.assertRaises(lock.SourceLockError):
                lock.verify_blob(name,lock.LOCKED_BLOBS[name],root=Path(temp))

    def test_30_symlink_cannot_substitute_source(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            path=root/"research/contributors/access_binding_candidate.mjs"
            path.parent.mkdir(parents=True)
            target=root/"fake.mjs"
            target.write_text("abc")
            path.symlink_to(target)
            with self.assertRaises(lock.SourceLockError):
                lock.verify_blob("research/contributors/access_binding_candidate.mjs",
                                 lock.LOCKED_BLOBS["research/contributors/access_binding_candidate.mjs"],root=root)

    def test_31_empty_source_denied(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            path=root/"research/contributors/access_binding_candidate.mjs"
            path.parent.mkdir(parents=True)
            path.write_bytes(b"")
            with self.assertRaises(lock.SourceLockError):
                lock.verify_blob("research/contributors/access_binding_candidate.mjs",
                                 lock.git_blob_sha(b""),root=root)

    def test_32_source_over_200kb_denied(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            path=root/"research/contributors/access_binding_candidate.mjs"
            path.parent.mkdir(parents=True)
            content=b"a"*200001
            path.write_bytes(content)
            with self.assertRaises(lock.SourceLockError):
                lock.verify_blob("research/contributors/access_binding_candidate.mjs",
                                 lock.git_blob_sha(content),root=root)

    def test_33_cli_check_only(self):
        with redirect_stdout(StringIO()) as output:
            self.assertEqual(lock.main(["--check"]),0)
        document=json.loads(output.getvalue())
        self.assertEqual(document["locked_sources"],14)

    def test_34_cli_deploy_argument_denied(self):
        with redirect_stdout(StringIO()) as output:
            self.assertEqual(lock.main(["--deploy"]),2)
        self.assertIn("NO_GO",output.getvalue())

    def test_35_no_api_network_or_credential_access(self):
        source=(Path(__file__).parent/"staging_source_lock_v079_lab.py").read_text()
        self.assertNotIn("urllib.request",source)
        self.assertNotIn("requests.",source)
        self.assertNotIn("cloudflare.com/client",source)
        self.assertNotIn("os.environ",source)

    def test_36_pinned_composition_has_no_worker_fetch_entry(self):
        text=(Path(__file__).parent/"private_levels_composition_v078_lab.mjs").read_text()
        self.assertNotIn("export default",text)
        self.assertIn("privateWorkerCandidateV078",text)


if __name__=="__main__":
    unittest.main()
