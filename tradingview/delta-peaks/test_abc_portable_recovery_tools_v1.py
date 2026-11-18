# REMURA v0.8.151 LAB — 18/11/2026, sessione delle 11:07 CET
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
