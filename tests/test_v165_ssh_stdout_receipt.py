"""Offline validation of the future private one-shot audit transport contract."""
from __future__ import annotations

import ast
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
ORACLE = ROOT / "deploy" / "oracle"
sys.path.insert(0, str(ORACLE))
import v165_ssh_stdout_receipt as receipt

TEMPLATE = ORACLE / "templates" / "v165-private-ssh-audit-REVIEW-ONLY.yml"


def good():
    return {
        "schema": receipt.SCHEMA,
        "status": "V164_PINNED_SOURCE_CONTENT_MATCH_ONLY",
        "fixedReleaseSourceCommit": receipt.SOURCE_COMMIT,
        "expectedPinnedFiles": 15,
        "independentlyComparedFiles": 15,
        "fullInstalledShaFromUpdaterVerified": False,
        "liveV165VersionAttested": False,
        "realSqliteBackupOrRestoreVerified": False,
        "oracleAlwaysFreeVerified": False,
        "privateAccessAclVerified": False,
        "authorizedRelease": False,
        "productionFilesModifiedByProgram": False,
        "researchC5Enabled": False,
        "operationalDecision": receipt.NO_GO,
    }


def encoded(item):
    return json.dumps(item, sort_keys=True).encode()


class OneShotReceiptTests(unittest.TestCase):
    def test_valid_bounded_payload_only_reports_15_matched(self):
        self.assertEqual(receipt.parse_untrusted_stdout(encoded(good())),
                         receipt.CONFIRMATION)
        self.assertIn("V165_RELEASE_AUTHORIZED=NO", receipt.CONFIRMATION)
        self.assertNotIn("YES", receipt.CONFIRMATION)

    def test_reject_wrong_target_sha(self):
        bad = good()
        bad["fixedReleaseSourceCommit"] = "0" * 40
        with self.assertRaises(receipt.UnsafeReceipt):
            receipt.parse_untrusted_stdout(encoded(bad))

    def test_reject_bad_schema(self):
        bad=good()
        bad["schema"] = "other"
        with self.assertRaises(receipt.UnsafeReceipt):
            receipt.parse_untrusted_stdout(encoded(bad))

    def test_reject_wrong_status(self):
        bad=good()
        bad["status"] = "GO"
        with self.assertRaises(receipt.UnsafeReceipt):
            receipt.parse_untrusted_stdout(encoded(bad))

    def test_reject_all_claimed_production_green_gates(self):
        for flag in receipt.MUST_REMAIN_FALSE:
            for value in (True, 1, 0, "false", None):
                with self.subTest(flag=flag,value=value):
                    data=good()
                    data[flag] = value
                    with self.assertRaises(receipt.UnsafeReceipt):
                        receipt.parse_untrusted_stdout(encoded(data))

    def test_reject_wrong_count_and_bool_spoof(self):
        for key in ("expectedPinnedFiles","independentlyComparedFiles"):
            for value in (14, 16, True, 15.0, "15", -1):
                with self.subTest(key=key,value=value):
                    data=good()
                    data[key]=value
                    with self.assertRaises(receipt.UnsafeReceipt):
                        receipt.parse_untrusted_stdout(encoded(data))

    def test_reject_success_decision_instead_of_no_go(self):
        bad=good()
        bad["operationalDecision"] = "GO"
        with self.assertRaises(receipt.UnsafeReceipt):
            receipt.parse_untrusted_stdout(encoded(bad))

    def test_reject_any_unexpected_field_including_secrets(self):
        bad=good()
        bad["ssh_private_key"] = "NEVER"
        with self.assertRaises(receipt.UnsafeReceipt):
            receipt.parse_untrusted_stdout(encoded(bad))

    def test_reject_missing_field(self):
        bad=good()
        del bad["status"]
        with self.assertRaises(receipt.UnsafeReceipt):
            receipt.parse_untrusted_stdout(encoded(bad))

    def test_reject_duplicate_field(self):
        first=encoded(good()).decode()
        payload=first[:-1]+',"status":"V164_PINNED_SOURCE_CONTENT_MATCH_ONLY"}'
        with self.assertRaises(receipt.UnsafeReceipt):
            receipt.parse_untrusted_stdout(payload.encode())

    def test_reject_trailing_output(self):
        with self.assertRaises(receipt.UnsafeReceipt):
            receipt.parse_untrusted_stdout(encoded(good())+b"\nTOKEN=secret")

    def test_reject_oversize(self):
        with self.assertRaises(receipt.UnsafeReceipt):
            receipt.parse_untrusted_stdout(encoded(good())+b" "*3000)

    def test_reject_invalid_utf8(self):
        with self.assertRaises(receipt.UnsafeReceipt):
            receipt.parse_untrusted_stdout(b"\xff")

    def test_reject_non_json(self):
        with self.assertRaises(receipt.UnsafeReceipt):
            receipt.parse_untrusted_stdout(b"V164_GO=YES")

    def test_reject_non_dict_json(self):
        for payload in (b'[]',b'null',b'123',b'true'):
            with self.subTest(payload=payload):
                with self.assertRaises(receipt.UnsafeReceipt):
                    receipt.parse_untrusted_stdout(payload)

    def test_reject_empty_output(self):
        with self.assertRaises(receipt.UnsafeReceipt):
            receipt.parse_untrusted_stdout(b"")

    def test_reject_non_bytes(self):
        with self.assertRaises(receipt.UnsafeReceipt):
            receipt.parse_untrusted_stdout("bad")

    def test_cli_prints_only_sanitized_success(self):
        script=str(ORACLE/"v165_ssh_stdout_receipt.py")
        p=subprocess.run([sys.executable, script], input=encoded(good()),
                         capture_output=True,timeout=10)
        self.assertEqual(p.returncode,0)
        self.assertEqual(p.stdout.decode().strip(),receipt.CONFIRMATION)
        self.assertEqual(p.stderr,b"")

    def test_cli_bad_does_not_echo_private_content(self):
        script=str(ORACLE/"v165_ssh_stdout_receipt.py")
        secret=b'\x7b"private":"ssh-secret-here"\x7d'
        p=subprocess.run([sys.executable, script],input=secret,
                         capture_output=True,timeout=10)
        self.assertNotEqual(p.returncode,0)
        self.assertEqual(p.stdout.decode().strip(),receipt.REJECTION)
        self.assertNotIn(b"ssh-secret-here",p.stdout+p.stderr)

    def test_receiver_no_network_or_deploy_code(self):
        path=ORACLE/"v165_ssh_stdout_receipt.py"
        src=path.read_text()
        names={x.name.split(".")[0] for node in ast.walk(ast.parse(src))
               if isinstance(node,ast.Import) for x in node.names}
        self.assertEqual(names,{"json","sys"})
        self.assertNotIn("os.environ",src)
        self.assertNotIn("subprocess",src)
        self.assertNotIn("urllib",src)

    def test_transport_is_nonactive_template_not_real_workflow(self):
        self.assertEqual(TEMPLATE.parent.name,"templates")
        self.assertNotIn(".github/workflows",str(TEMPLATE))

    def test_transport_only_manual_main_and_private_enabled(self):
        t=TEMPLATE.read_text()
        self.assertIn("  workflow_dispatch:",t)
        self.assertNotIn("  schedule:",t)
        self.assertNotIn("  push:",t)
        self.assertNotIn("  pull_request:",t)
        for guard in ("github.event.repository.private == true",
                      "github.ref == 'refs/heads/main'",
                      "vars.REMURA_V165_SSH_AUDIT_ENABLED == '1'",
                      "environment: v165-audit-protected"):
            self.assertIn(guard,t)

    def test_transport_never_widens_existing_https_only_tag(self):
        t=TEMPLATE.read_text()
        self.assertIn("tags: tag:remura-ci-v165-audit",t)
        self.assertNotIn("tags: tag:remura-ci-read",t)

    def test_transport_pins_exact_code_source(self):
        t=TEMPLATE.read_text()
        self.assertIn("ref: 33aeb9a4805104d663489e3a5e28dd12db47f28a",t)
        self.assertIn("expected_code_blob=98b0a28190647e9d321690097aae30395bc9f900",t)
        self.assertIn("git hash-object",t)
        self.assertIn("persist-credentials: false",t)

    def test_transport_requires_pinned_ssh_known_hosts(self):
        t=TEMPLATE.read_text()
        self.assertIn("ssh-keygen -F",t)
        self.assertIn("-o StrictHostKeyChecking=yes",t)
        self.assertIn("-o UserKnownHostsFile=",t)
        self.assertNotIn("ssh-keyscan ",t)
        self.assertNotIn("StrictHostKeyChecking=no",t)
        self.assertNotIn("accept-new",t)

    def test_transport_rejects_root_privileged_account(self):
        t=TEMPLATE.read_text()
        self.assertIn('"$REMURA_V165_SSH_USER" == root',t)
        self.assertIn("-o PasswordAuthentication=no",t)
        self.assertIn("-o BatchMode=yes",t)
        self.assertIn("-o ForwardAgent=no",t)

    def test_no_script_copy_or_remote_deployment(self):
        t=TEMPLATE.read_text()
        self.assertIn("'python3 -I - --audit-live-readonly --operator-approved'",t)
        self.assertIn("< deploy/oracle/v165_v164_live_code_readonly.py",t)
        for forbidden in (" scp ", " rsync ", " sudo ", " systemctl ",
                          " chmod 777 ", " curl ", " apt-get ",
                          " ssh-keyscan ", ">> /opt/"):
            self.assertNotIn(forbidden,t)

    def test_runner_does_not_log_raw_ssh_output(self):
        t=TEMPLATE.read_text()
        self.assertIn("2>/dev/null",t)
        self.assertIn('printf \'%s\' "$report" |',t)
        self.assertIn("v165_ssh_stdout_receipt.py",t)
        self.assertNotIn('echo "$report"',t)
        self.assertNotIn("set -x",t)

    def test_documented_disclaimers_no_release(self):
        t=TEMPLATE.read_text()
        self.assertIn("NOT INSTALLED AS A GITHUB ACTION",t)
        self.assertIn("would NOT verify updater SHA",t)
        self.assertIn("MUST NOT be expanded",t)


if __name__ == "__main__":
    unittest.main()
