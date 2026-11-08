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
        self.assertIn("ref: 77eb7ec4dfd98176c8146651489a382126647048",t)
        self.assertIn("expected_code_blob=98b0a28190647e9d321690097aae30395bc9f900",t)
        self.assertIn("git hash-object",t)
        self.assertIn("persist-credentials: false",t)

    def test_external_actions_are_immutable_upstream_verified_sha(self):
        t=TEMPLATE.read_text()
        self.assertIn("uses: actions/checkout@93cb6efe18208431cddfb8368fd83d5badbf9bfd # v5.0.1", t)
        self.assertIn("uses: tailscale/github-action@064b10558093f38325e838ddea35486bdc6b1d5c # v4.4.0", t)
        self.assertNotIn("uses: actions/checkout@v5", t)
        self.assertNotIn("uses: tailscale/github-action@v4", t)

    def test_external_actions_all_use_full_40_hex_shas(self):
        import re
        t=TEMPLATE.read_text()
        refs=re.findall(r"^\s+uses:\s+([^\s#]+)", t, re.MULTILINE)
        self.assertEqual(len(refs),2)
        for ref in refs:
            with self.subTest(ref=ref):
                self.assertRegex(ref, r"^[a-z0-9_-]+/[a-z0-9_-]+@[0-9a-f]{40}$")
        self.assertNotIn("@main",t)
        self.assertNotIn("@latest",t)

    def test_tailscale_client_version_explicit_and_no_cache_reuse(self):
        t=TEMPLATE.read_text()
        self.assertIn("          version: 1.104.4",t)
        self.assertIn("          use-cache: 'false'",t)
        self.assertNotIn("version: latest",t)
        self.assertNotIn("version: unstable",t)

    def test_template_runner_os_is_fixed_supported_family(self):
        t=TEMPLATE.read_text()
        self.assertIn("    runs-on: ubuntu-24.04",t)
        self.assertNotIn("    runs-on: ubuntu-latest",t)

    def test_tailscale_archive_digest_from_reviewed_variable_only(self):
        t=TEMPLATE.read_text()
        variable=chr(36)+"{{ vars.REMURA_V165_TS_TARBALL_SHA256 }}"
        self.assertIn("sha256sum: "+variable,t)
        self.assertIn("TS_V165_ARCHIVE_SHA256: "+variable,t)
        self.assertIn("REMURA_AUDIT=TAILSCALE_ARCHIVE_PIN_NOT_ATTESTED",t)
        self.assertLess(t.index("TAILSCALE_ARCHIVE_PIN_NOT_ATTESTED"),
                        t.index("Connect dedicated ephemeral audit identity"))

    @staticmethod
    def _archive_preflight(digest, os_name="Linux", arch="X64"):
        import os
        import textwrap
        t=TEMPLATE.read_text()
        start=t.split("      - name: Require independently reviewed pinned Tailscale archive checksum",1)[1]
        gate=start.split("      - name: Connect dedicated ephemeral audit identity",1)[0]
        script=textwrap.dedent(gate.split("        run: |\n",1)[1]).strip()
        env=dict(os.environ)
        env.update({"TS_V165_ARCHIVE_SHA256":digest,
                    "RUNNER_OS":os_name,"RUNNER_ARCH":arch})
        return subprocess.run(["bash","-c",script],env=env,
                              capture_output=True,timeout=5)

    def test_archive_preflight_rejects_missing_zeros_bad_lengths_and_injection(self):
        candidates=("", "0"*64, "a"*63, "f"*65, "A"*64,
                    "x"*64, "a"*31+"$(echo secret)", "a"*32+"\n"+"b"*32)
        for digest in candidates:
            with self.subTest(length=len(digest)):
                p=self._archive_preflight(digest)
                self.assertNotEqual(p.returncode,0)
                self.assertIn(b"TAILSCALE_ARCHIVE_PIN_NOT_ATTESTED",p.stdout)
                self.assertNotIn(b"secret",p.stdout+p.stderr)

    def test_archive_preflight_rejects_wrong_runner_platform(self):
        digest="ab"*32
        for os_name,arch in (("Windows","X64"),("macOS","X64"),
                             ("Linux","ARM64"),("Linux","")):
            with self.subTest(os=os_name,arch=arch):
                p=self._archive_preflight(digest,os_name,arch)
                self.assertNotEqual(p.returncode,0)

    def test_archive_preflight_accepts_synthetic_shape_not_authenticity(self):
        # A syntactically valid test digest is NOT the real archive checksum.
        p=self._archive_preflight("ab"*32)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(p.stdout,b"")
        self.assertEqual(p.stderr,b"")

    def test_transport_requires_pinned_ssh_known_hosts(self):
        t=TEMPLATE.read_text()
        self.assertIn("ssh-keygen -F",t)
        self.assertIn("-o StrictHostKeyChecking=yes",t)
        self.assertIn("-o UserKnownHostsFile=",t)
        self.assertNotIn("ssh-keyscan ",t)
        self.assertNotIn("StrictHostKeyChecking=no",t)
        self.assertNotIn("StrictHostKeyChecking=accept-new",t)

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
        self.assertIn('head -c 2049 > "$outfile"',t)
        self.assertIn('v165_ssh_stdout_receipt.py < "$outfile"',t)
        self.assertIn('outfile="$(mktemp ',t)
        self.assertIn('rm -f "$keyfile" "$khfile" "$outfile"',t)
        self.assertNotIn('report=""',t)
        self.assertNotIn('echo "$report"',t)
        self.assertNotIn("set -x",t)

    def test_runner_output_ceiling_tied_to_strict_receiver(self):
        t=TEMPLATE.read_text()
        self.assertIn(f"head -c {receipt.MAX_STDOUT_BYTES + 1}",t)
        self.assertIn("set -o pipefail; timeout 40s ssh",t)

    def test_oidc_permission_is_scoped_to_gated_job(self):
        t=TEMPLATE.read_text()
        self.assertIn("permissions:\n  contents: read\n\nconcurrency:",t)
        self.assertIn("jobs:\n  audit:\n",t)
        self.assertIn("    permissions:\n      contents: read\n      id-token: write",t)
        self.assertEqual(t.count("id-token: write"),1)

    def test_transport_pins_receiver_separately_before_credentials(self):
        t=TEMPLATE.read_text()
        self.assertIn("expected_receiver_blob=96a3fd628baff65e677d4594bb8e6c65205bc596",t)
        self.assertIn("git hash-object deploy/oracle/v165_ssh_stdout_receipt.py",t)
        self.assertLess(t.index("PINNED_RECEIVER_DRIFT"),t.index("Connect dedicated ephemeral audit identity"))

    def test_ssh_does_not_use_inherited_client_proxies_or_control_sockets(self):
        t=TEMPLATE.read_text()
        for guard in ("ssh -F /dev/null", "-o ProxyCommand=none",
                      "-o ProxyJump=none", "-o ControlMaster=no",
                      "-o ControlPath=none"):
            self.assertIn(guard,t)

    def test_documented_disclaimers_no_release(self):
        t=TEMPLATE.read_text()
        self.assertIn("NOT INSTALLED AS A GITHUB ACTION",t)
        self.assertIn("would NOT verify updater SHA",t)
        self.assertIn("MUST NOT be expanded",t)


if __name__ == "__main__":
    unittest.main()
