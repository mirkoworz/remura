# REMURA v0.8.152 LAB — 18/11/2026, sessione successiva alle 11:13 CET
import json,os,sqlite3,tempfile,unittest,shutil
from unittest.mock import patch
import abc_prices_recovery_v2 as recovery
from pathlib import Path
from abc_prices_recovery_v2 import snapshot,make_tar,verify_plain,inspect_closed
from abc_v165_preflight_portable_v1 import modules,SOURCES,MANIFEST
class Tests(unittest.TestCase):
    def test_portable_exact_sources_and_manifest(self):
        here=Path(__file__).resolve().parent
        for n,s in SOURCES:self.assertEqual((here/(n+".py")).read_text(),s)
        self.assertEqual((here/"abc-v165-pinned-application-manifest.json").read_text(),MANIFEST)
        p,m=modules()
        self.assertEqual(len(m),155)
        self.assertEqual(sum(r["operation"]=="add" for r in m),76)
        self.assertTrue(callable(p.oracle_report))
    def test_future_snapshot_and_schema_and_archive(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d).resolve();source=root/"live.db";copy=root/"copy.db";tar=root/"copy.tar.gz"
            a=sqlite3.connect(source)
            try:
                a.execute("PRAGMA journal_mode=WAL")
                a.executescript("CREATE TABLE prices(x);CREATE TABLE status(x);CREATE TABLE cot_reports(x);CREATE TABLE cot_first_seen(x);CREATE TABLE research_cvd_observations(x);INSERT INTO prices VALUES(1);")
                a.commit()
                summary=snapshot(source,copy)
                self.assertEqual(summary["cot_tables_present"],2)
                self.assertEqual(summary["research_tables_present"],1)
                self.assertEqual(inspect_closed(copy)["result"],summary)
                make_tar(copy,tar,6,summary)
                self.assertEqual(verify_plain(tar.read_bytes(),6)["status"],"DECRYPTION_AND_MEMBER_HASH_VERIFIED")
                with self.assertRaises(ValueError):verify_plain(tar.read_bytes(),7)
                self.assertEqual(a.execute("SELECT count(*) FROM prices").fetchone()[0],1)
            finally:a.close()
    def test_refuse_closed_with_sidecar(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d).resolve()/"x.db";p.write_bytes(b"x")
            Path(str(p)+"-wal").touch()
            with self.assertRaises(ValueError):inspect_closed(p)

    def test_gpg_owner_recovery_and_signed_receipt(self):
        self.assertIsNotNone(shutil.which("gpg"),"GPG required for end-to-end test")
        with tempfile.TemporaryDirectory() as d:
            root=Path(d).resolve()
            owner=root/"owner"; public=root/"public"; out=root/"out"
            for p in (owner,public,out):p.mkdir(mode=0o700)
            try:
                recovery.gpg(owner,"--pinentry-mode","loopback","--passphrase","","--quick-generate-key",
                             "REMURA disposable CI <fixture@example.invalid>","rsa2048","sign","1d",stdout=recovery.subprocess.PIPE)
                keys=recovery.gpg(owner,"--with-colons","--list-keys",stdout=recovery.subprocess.PIPE).stdout.decode()
                primary=next(x.split(":")[9] for x in keys.splitlines() if x.startswith("fpr:"))
                recovery.gpg(owner,"--pinentry-mode","loopback","--passphrase","","--quick-add-key",primary,"rsa2048","encr","1d",stdout=recovery.subprocess.PIPE)
                keys=recovery.gpg(owner,"--with-colons","--list-keys",stdout=recovery.subprocess.PIPE).stdout.decode()
                sub=[x.split(":")[9] for x in keys.splitlines() if x.startswith("fpr:")][1]
                pub=recovery.gpg(owner,"--export",primary,stdout=recovery.subprocess.PIPE).stdout
                recovery.gpg(public,"--import",input=pub,stdout=recovery.subprocess.PIPE)
                recovery.recipient_check(public,primary,sub)
                # Reuse the disposable key pair for domain-separated release authorization.
                import abc_v165_release_attestation_v1 as release
                payload=root/"release.json"
                payload.write_bytes(release.statement())
                signature=recovery.gpg(owner,"--pinentry-mode","loopback","--passphrase","","--local-user",primary+"!",
                                      "--detach-sign","--output","-",str(payload),
                                      stdout=recovery.subprocess.PIPE).stdout
                with patch.object(release.os,"geteuid",return_value=1000):
                    att=release.verify_attestation(public,primary,signature)
                    self.assertTrue(att["owner_signature_verified"])
                    self.assertFalse(att["install_authorized"])
                    with self.assertRaises(ValueError):release.verify_attestation(public,sub,signature)
                    with self.assertRaises(ValueError):release.verify_attestation(owner,primary,signature)
                    with patch.object(release,"BUNDLE","0"*64):
                        with self.assertRaises(recovery.subprocess.CalledProcessError):
                            release.verify_attestation(public,primary,signature)
                    with patch.object(release.stage,"inspect_bundle",return_value={"bundle_sha256":release.BUNDLE,"bundle_bytes":release.BUNDLE_BYTES}):
                        self.assertTrue(release.verify_bundle_attestation(root/"fixture.tar",public,primary,signature)["bundle_on_target_verified"])
                    with patch.object(release.stage,"inspect_bundle",return_value={"bundle_sha256":"0"*64,"bundle_bytes":release.BUNDLE_BYTES}):
                        with self.assertRaises(ValueError):release.verify_bundle_attestation(root/"fixture.tar",public,primary,signature)
                # Reuse existing disposable signing key, no real key or extra provisioning.
                import abc_v165_external_phase_receipt_lab_v1 as phase
                first=phase.statement(transaction="a"*64,plan="b"*64,sequence=1,
                    previous=phase.ZERO,phase="prepared",journal="c"*64,challenge="d"*64)
                def sign_phase(body):
                    p=root/"phase.json";p.write_bytes(recovery.canon(body))
                    return recovery.gpg(owner,"--pinentry-mode","loopback","--passphrase","",
                        "--local-user",primary+"!","--detach-sign","--output","-",str(p),
                        stdout=recovery.subprocess.PIPE).stdout
                sig1=sign_phase(first);a1=phase.anchor(first,sig1)
                second=phase.successor(first,sig1,latest_anchor=a1,phase="applying",
                                       journal="c"*64,challenge="e"*64)
                sig2=sign_phase(second);a2=phase.anchor(second,sig2)
                args=dict(keyring=public,signer=primary,latest_anchor=a2,transaction="a"*64,
                          plan="b"*64,sequence=2,phase="applying",journal="c"*64,
                          challenge="e"*64,synthetic=True)
                self.assertFalse(phase.verify(second,sig2,**args)["install_authorized"])
                with self.assertRaises(ValueError):phase.verify(first,sig1,**args)
                with self.assertRaises(ValueError):phase.verify(second,sig2,**dict(args,challenge="f"*64))
                with self.assertRaises(ValueError):phase.verify(second,sig2,**dict(args,keyring=owner))
                with self.assertRaises(ValueError):phase.successor(first,sig1,latest_anchor=a1,
                    phase="applied",journal="c"*64,challenge="e"*64)
                bad=dict(second,journal="f"*64)
                with self.assertRaises(recovery.subprocess.CalledProcessError):
                    phase.verify(bad,sig2,**dict(args,journal="f"*64,latest_anchor=phase.anchor(bad,sig2)))
                # Exercise durable compare-and-set across separate SQLite connections.
                import abc_v165_external_phase_store_lab_v1 as store
                register=root/"register";register.mkdir(mode=0o700)
                store.create(register,synthetic=True)
                with self.assertRaises(FileExistsError):store.create(register,synthetic=True)
                def append(body,sig,expected):
                    return store.append(register,body,sig,expected_latest=expected,
                                        keyring=public,signer=primary,synthetic=True)
                self.assertEqual(append(first,sig1,phase.ZERO),a1)
                self.assertEqual(append(second,sig2,a1),a2)
                with self.assertRaises(ValueError):append(second,sig2,a1)
                with self.assertRaises(ValueError):append(first,sig1,a2)
                with sqlite3.connect(register/"phase-register.sqlite3") as tamper:
                    self.assertEqual(tamper.execute("SELECT count(*) FROM receipts").fetchone()[0],2)
                    tamper.execute("DELETE FROM receipts WHERE seq=2")
                # An independently retained latest anchor detects a reverted register.
                with self.assertRaises(ValueError):append(second,sig2,a2)
                with self.assertRaises(ValueError):recovery.recipient_check(owner,primary,sub)
                db=root/"source.db"; copy=root/"copy.db"; tar=root/"package"; cipher=out/"fixture.gpg"
                a=sqlite3.connect(db)
                try:
                    a.executescript("CREATE TABLE prices(x);CREATE TABLE status(x);CREATE TABLE cot_reports(x);CREATE TABLE cot_first_seen(x);INSERT INTO prices VALUES(7);")
                    a.commit()
                finally:a.close()
                summary=snapshot(db,copy)
                make_tar(copy,tar,6,summary)
                recovery.seal(public,sub,tar,cipher)
                expected=recovery.hash_file(cipher)
                with patch.object(recovery.getpass,"getpass",return_value=""):
                    result=recovery.verify_owner(cipher,owner,expected,6,recover=True)
                    self.assertTrue(result["sqlite_restore_tested"])
                    self.assertTrue(recovery.sign_receipt(result,expected,owner,out,primary)["witness_signed"])
                    with self.assertRaises(ValueError):recovery.sign_receipt(result,expected,owner,out,primary)
                    with self.assertRaises(ValueError):recovery.verify_owner(cipher,owner,"0"*64,6,recover=True)
                receipt=out/"prices-000006.receipt.json"
                self.assertEqual(recovery.verify_receipt(receipt,public,expected,6,primary)["status"],"OWNER_RECEIPT_SIGNATURE_VERIFIED")
                env=json.loads(receipt.read_bytes());env["payload"]["owner_clock_utc"]="tampered"
                bad=out/"bad.json";bad.write_bytes(recovery.canon(env))
                with self.assertRaises(recovery.subprocess.CalledProcessError):recovery.verify_receipt(bad,public,expected,6,primary)
                with self.assertRaises(ValueError):recovery.verify_receipt(receipt,public,expected,7,primary)
                with self.assertRaises(ValueError):recovery.seal(public,sub,tar,cipher)
            finally:
                for p in (owner,public):
                    recovery.subprocess.run(["gpgconf","--homedir",str(p),"--kill","all"],check=False,stdout=recovery.subprocess.DEVNULL,stderr=recovery.subprocess.DEVNULL)

    def test_capture_gate_swap_and_metadata(self):
        h="Filename Type Size Used Priority\n"
        mem="MemAvailable: 640532 kB\nSwapTotal: 0 kB\n"
        args=(recovery.CAPTURE_BUDGET,recovery.MAX+2*recovery.MARGIN)
        recovery.capture_resource_gate(mem,h,*args)
        for m,s,reason in [
            (mem.replace("SwapTotal: 0","SwapTotal: 1048572"),h,"CAPTURE_SWAP_ACTIVE"),
            (mem,h+"/dev/example partition 1 0 -2\n","CAPTURE_SWAP_ACTIVE"),
            (mem.replace("SwapTotal: 0 kB\n",""),h,"CAPTURE_RESOURCE_METADATA"),
            (mem,"","CAPTURE_RESOURCE_METADATA"),
            (mem+"SwapTotal: 0 kB\n",h,"CAPTURE_RESOURCE_METADATA"),
        ]:
            with self.assertRaisesRegex(recovery.CaptureResourceError,reason):
                recovery.capture_resource_gate(m,s,*args)

    def test_capture_gate_full_cap_and_reserve(self):
        h="Filename Type Size Used Priority\n"
        limit=recovery.CAPTURE_BUDGET+recovery.RAM_RESERVE
        mem="MemAvailable: %d kB\nSwapTotal: 0 kB\n"%(limit//1024)
        a,b=recovery.CAPTURE_BUDGET,recovery.MAX+2*recovery.MARGIN
        recovery.capture_resource_gate(mem,h,a,b)
        for m,x,y in [(mem,a-1,b),(mem,a,b-1),(mem.replace(str(limit//1024),str(limit//1024-1)),a,b)]:
            with self.assertRaisesRegex(recovery.CaptureResourceError,"CAPTURE_RESOURCES_LOW"):
                recovery.capture_resource_gate(m,h,x,y)
