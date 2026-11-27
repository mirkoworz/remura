"""Tests for real read-only pinned v1.64 identity verifier; fixture files only."""
from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "deploy" / "oracle"
sys.path.insert(0, str(DIR))
import v165_v164_live_code_readonly as m


class IndependentV164IdentityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="remura-v164-local-file-fixture-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "scripts").mkdir()
        self.raw = {
            name: (b"REMURA TEST FILE " + name.encode("ascii") + b"\n")
            for name in m.FILES
        }
        self.raw["nav.js"] = (
            b"const version = 'v1.64'; const banner = 'REMURA "
            + m.STAMP_PREPARED + b"';\n"
        )
        self.expected = {k: m.git_blob(v) for k,v in self.raw.items()}
        for name, data in self.raw.items():
            p = self.root / name
            p.write_bytes(data)
        self.live_stamp = b"08/11/2026 18:00 (Italia)"
        (self.root / "nav.js").write_bytes(
            self.raw["nav.js"].replace(m.STAMP_PREPARED, self.live_stamp))

    def verify(self):
        fd = os.open(self.root, m._directory_flags())
        try:
            return m._verify_fd(fd, self.expected)
        finally:
            os.close(fd)

    def test_exact_fifteen_files_fixture_matched(self):
        self.assertEqual(self.verify(), 15)

    def test_pinned_manifest_real_sha_matches_reviewed_release(self):
        self.assertEqual(m.SOURCE_COMMIT, "883336a4e956a9e50c94dcfebf8d7ba78910fb65")
        self.assertEqual(len(m.FILES), 15)
        self.assertEqual(set(m.FILES),set(m.GIT_BLOBS))
        self.assertEqual(m.GIT_BLOBS["nav.js"],
                         "d35c9d06f9c64a10938f30ec7e7ae7b2f2c5fbec")
        self.assertEqual(m.GIT_BLOBS["splash-mascot.webp"],
                         "60433776bf6a94d2b342023446dc62a409f58962")

    def test_nav_source_prep_stamp_not_accepted_as_live(self):
        (self.root / "nav.js").write_bytes(self.raw["nav.js"])
        with self.assertRaisesRegex(m.LocalReadOnlyStop, "STOP_NAV_PREPARATION"):
            self.verify()

    def test_nav_real_stamp_different_day_is_ok(self):
        (self.root / "nav.js").write_bytes(
            self.raw["nav.js"].replace(
                m.STAMP_PREPARED, b"07/11/2026 23:59 (Italia)"))
        self.assertEqual(self.verify(), 15)

    def test_nav_unrelated_modification_rejected(self):
        p = self.root / "nav.js"
        p.write_bytes(p.read_bytes() + b"// injected\n")
        with self.assertRaisesRegex(m.LocalReadOnlyStop, "STOP_PINNED_FILE_MISMATCH"):
            self.verify()

    def test_nav_multiple_dates_rejected(self):
        p = self.root / "nav.js"
        p.write_bytes(p.read_bytes() + b"08/11/2026 17:00 (Italia)")
        with self.assertRaisesRegex(m.LocalReadOnlyStop, "STOP_NAV_STAMP_MISSING_OR_AMBIGUOUS"):
            self.verify()

    def test_nav_invalid_date_format_rejected(self):
        (self.root / "nav.js").write_bytes(
            self.raw["nav.js"].replace(m.STAMP_PREPARED, b"42/11/2026 18:00 (Italia)"))
        with self.assertRaisesRegex(m.LocalReadOnlyStop, "STOP_NAV_STAMP_MISSING_OR_AMBIGUOUS"):
            self.verify()

    def test_nav_wrong_placeholder_rejected(self):
        (self.root / "nav.js").write_bytes(b"no Italian timestamp")
        with self.assertRaisesRegex(m.LocalReadOnlyStop, "STOP_NAV_STAMP_MISSING_OR_AMBIGUOUS"):
            self.verify()

    def test_every_single_file_change_is_caught(self):
        for name in m.FILES:
            if name=="nav.js": continue
            with self.subTest(file=name):
                p=self.root/name
                original=p.read_bytes()
                try:
                    p.write_bytes(original+b"BAD")
                    with self.assertRaisesRegex(m.LocalReadOnlyStop,"STOP_PINNED_FILE_MISMATCH"):
                        self.verify()
                finally:
                    p.write_bytes(original)

    def test_missing_file_rejected(self):
        (self.root/"splash.css").unlink()
        with self.assertRaises(OSError):
            self.verify()

    def test_nonregular_directory_rejected(self):
        p=self.root/"splash.js"
        p.unlink()
        p.mkdir()
        with self.assertRaises((OSError,m.LocalReadOnlyStop)):
            self.verify()

    def test_symlink_file_rejected_even_matching(self):
        p=self.root/"splash.css"
        data=p.read_bytes()
        p.unlink()
        target=self.root/"outside"
        target.write_bytes(data)
        p.symlink_to(target)
        with self.assertRaises((OSError,m.LocalReadOnlyStop)):
            self.verify()

    def test_symlink_scripts_directory_rejected(self):
        (self.root/"scripts"/"private_server.py").unlink()
        (self.root/"scripts").rmdir()
        folder=self.root/"outsidefolder"
        folder.mkdir()
        (folder/"private_server.py").write_bytes(self.raw["scripts/private_server.py"])
        (self.root/"scripts").symlink_to(folder,target_is_directory=True)
        with self.assertRaises((OSError,m.LocalReadOnlyStop)):
            self.verify()

    def test_hardlinked_file_rejected(self):
        p=self.root/"splash.css"
        os.link(p,self.root/"extra-hardlink")
        with self.assertRaisesRegex(m.LocalReadOnlyStop,"STOP_FILE_NOT_REGULAR"):
            self.verify()

    def test_empty_file_rejected(self):
        (self.root/"splash.css").write_bytes(b"")
        with self.assertRaisesRegex(m.LocalReadOnlyStop,"STOP_FILE_NOT_REGULAR"):
            self.verify()

    def test_oversized_file_rejected(self):
        with (self.root/"splash.css").open("wb") as f:
            f.truncate(m.MAX_FILE+1)
        with self.assertRaisesRegex(m.LocalReadOnlyStop,"STOP_FILE_NOT_REGULAR"):
            self.verify()

    def test_read_no_file_content_transmitted(self):
        r=m._result(status="STOP_LOCAL_CODE_NOT_ATTESTED",count=0)
        text=json.dumps(r)
        for secret in ("privateKey","/opt/remura","accessToken","content",
                       "sqlite3","Tailscale","account"):
            self.assertNotIn(secret,text)
        self.assertEqual(r["operationalDecision"],m.NO_GO)

    def test_result_never_certifies_deploy_or_price_collection(self):
        r=m._result(status="V164_PINNED_SOURCE_CONTENT_MATCH_ONLY",count=15)
        for key in ("fullInstalledShaFromUpdaterVerified",
                    "liveV165VersionAttested","realSqliteBackupOrRestoreVerified",
                    "oracleAlwaysFreeVerified","privateAccessAclVerified",
                    "authorizedRelease","productionFilesModifiedByProgram",
                    "researchC5Enabled"):
            self.assertIs(r[key],False,key)

    def test_outside_manifest_not_counted(self):
        (self.root/"unrelated.txt").write_text("extra")
        self.assertEqual(self.verify(),15)
        self.assertEqual(len(m.FILES),15)

    def test_git_blob_matches_canonical_git_format(self):
        payload=b"hello\n"
        target=hashlib.sha1(b"blob 6\0hello\n").hexdigest()
        self.assertEqual(m.git_blob(payload),target)

    def test_git_blob_empty_refused(self):
        with self.assertRaisesRegex(m.LocalReadOnlyStop,"STOP_BOUNDED_BYTES_REQUIRED"):
            m.git_blob(b"")

    def test_git_blob_wrong_type_refused(self):
        with self.assertRaisesRegex(m.LocalReadOnlyStop,"STOP_BOUNDED_BYTES_REQUIRED"):
            m.git_blob("hi")

    def test_manifest_mutation_refused(self):
        bad=dict(self.expected)
        bad.pop("splash.js")
        fd=os.open(self.root,m._directory_flags())
        try:
            with self.assertRaisesRegex(m.LocalReadOnlyStop,"STOP_MANIFEST_INVALID"):
                m._verify_fd(fd,bad)
        finally:
            os.close(fd)

    def test_manifest_extra_secrets_refused(self):
        bad=dict(self.expected)
        bad["private/secret"]="a"*40
        fd=os.open(self.root,m._directory_flags())
        try:
            with self.assertRaisesRegex(m.LocalReadOnlyStop,"STOP_MANIFEST_INVALID"):
                m._verify_fd(fd,bad)
        finally:
            os.close(fd)

    def test_manifest_invalid_hash_refused(self):
        bad=dict(self.expected)
        bad["splash.css"]="NOT_A_HASH"
        fd=os.open(self.root,m._directory_flags())
        try:
            with self.assertRaisesRegex(m.LocalReadOnlyStop,"STOP_MANIFEST_INVALID"):
                m._verify_fd(fd,bad)
        finally:
            os.close(fd)

    def test_file_component_traversal_rejected(self):
        fd=os.open(self.root,m._directory_flags())
        try:
            for name in ("../x","a/b","", ".", "..", "a\\b", None):
                with self.subTest(name=name):
                    with self.assertRaisesRegex(m.LocalReadOnlyStop,"STOP_FILE_COMPONENT"):
                        m._bounded_file(fd,name)
        finally:
            os.close(fd)

    def test_no_services_network_database_or_live_cli_fallback(self):
        source=(DIR/"v165_v164_live_code_readonly.py").read_text("utf-8")
        imports={a.name.split(".")[0] for node in ast.walk(ast.parse(source))
                 if isinstance(node,ast.Import) for a in node.names}
        self.assertTrue(imports.isdisjoint({
            "subprocess","sqlite3","urllib","socket","requests",
            "http","shutil","tempfile","threading"
        }))
        for flag in ("--apply","--rollback","--deploy","--target",
                     "--root","--path","--host","--json","--write"):
            self.assertNotIn('add_argument("'+flag+'"',source)
        self.assertNotIn("systemctl",source)

    def test_cli_cannot_accidentally_probe_live_with_one_flag(self):
        cmd=[sys.executable,str(DIR/"v165_v164_live_code_readonly.py")]
        for extra in ([],["--audit-live-readonly"],["--operator-approved"],
                      ["--apply"]):
            p=subprocess.run(cmd+extra,cwd=ROOT,timeout=15,text=True,
                             capture_output=True)
            self.assertNotEqual(p.returncode,0,extra)

    def test_local_scan_uses_pinned_root_only(self):
        source=(DIR/"v165_v164_live_code_readonly.py").read_text("utf-8")
        self.assertIn('os.open("/", flags)',source)
        self.assertIn('("opt", "remura")',source)
        self.assertIn('os.O_NOFOLLOW',source)
        self.assertNotIn('os.environ',source)

    def test_cleanup_on_mid_scan_failure(self):
        fd=os.open(self.root,m._directory_flags())
        try:
            (self.root/"splash.css").unlink()
            with patch.object(m.os,"close",wraps=m.os.close) as close:
                with self.assertRaises(OSError):
                    m._verify_fd(fd,self.expected)
                self.assertGreaterEqual(close.call_count,1)
        finally:
            os.close(fd)


if __name__ == "__main__":
    unittest.main()
