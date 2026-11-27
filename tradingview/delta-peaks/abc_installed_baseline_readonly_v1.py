#!/usr/bin/env python3
# REMURA v0.8.140 LAB — 17/11/2026, sessione serale CET
"""Bounded read-only installed baseline census. No broker/network/database reads.
Private file metadata only; never emit private paths, contents, credentials.
Run manually only after CI and owner review. Never updates or restarts service.
"""
import argparse,datetime,hashlib,json,os,re,shutil,stat,sys
from pathlib import Path
BASE="30de2987fe28ee73044448817e66ac60391e3357"
INSTALLED_REPORTED="c964bcb85b85106f6fdf9260e7e571bb74111499"
PINS={
    "asset.html": "2036c63dc8ff2930636f6dc9d4259fa2353c8b11",
    "capital-cloud-config.js": "f05cb26784807d8e5b44ee4ae46a9cea3d6c81a5",
    "capital-cloud.js": "0a7cd3e5c91fb416057eb0bab6e8d1d60f891fd1",
    "case-audit-core.js": "29d9c9213586a328562b1a09ddf27e029e20d658",
    "case-audit-ui.js": "58e27ae7df4bdbd0c40236c1e4200b73e6403732",
    "catalogo.html": "2847a1ecb36ee92aa36e14444db5770f846f4978",
    "cot-indices-core.js": "b692c61de1ca7ef2d93009c36634b5641a68c201",
    "cot-week-watch-core.js": "97efc8c06d6d83528e50d0b8b384d2aa11289275",
    "cot-week-watch-ui.js": "bc1a3afdb58373ababcdd431b9ea4190a0a9cd4e",
    "deploy/oracle/autoupdate.py": "53ca8ec381e30d019f1cc8570e33e0150e6c233e",
    "deploy/oracle/backup_v156.py": "dc01f2b4767a5427b1d65b96f7a883870b82f608",
    "deploy/oracle/enable-autoupdate.sh": "2c6abe5f487060b575ea0d94f22ae91dadaf2485",
    "deploy/oracle/install.sh": "388e51729e9b60b6177a2fff21ff38293002a61e",
    "deploy/oracle/priority_v157.py": "f20e8c2ca1ac95e1100cbd73a7dc84fac42388a3",
    "deploy/oracle/reconcile_v156.py": "f695df39bf5a3c731437e287676b132980c4882f",
    "deploy/oracle/reconcile_v157.py": "aaf472ccc40f1af1cac5b35101f81eb884df75c8",
    "deploy/oracle/reconcile_v158.py": "1528102810a988d5df7d0d92fdfd3c2fcaadd5a6",
    "deploy/oracle/reconcile_v159.py": "18da8a029e81a68185999f72d507460be7e21151",
    "deploy/oracle/reconcile_v160.py": "43bc122516b0cf6a8a1097bd8edc2ad4c571abfa",
    "deploy/oracle/reconcile_v161.py": "679e5a0934a0c956aab4e6810b59ceef511f0ff0",
    "deploy/oracle/reconcile_v162.py": "99ae6c460ef12ab9764cb15732a7469627662ee0",
    "deploy/oracle/reconcile_v163.py": "c53ac714e9d73b9292419748978e70f060549095",
    "deploy/oracle/reconcile_v164.py": "4454480bf7f02cafa66c6c2dd730854c886b39ab",
    "deploy/oracle/release_myfxbook_151.py": "086ed4a4f87d3832fcc121322ef3df073798a148",
    "deploy/oracle/release_v152.py": "e61752c443ed9b972ac3af63c63b71708ff0beb9",
    "deploy/oracle/release_v156.py": "8997906ee3d246b5c5d3f13a700b546c112dc525",
    "deploy/oracle/release_v157.py": "66b1b47dffdba04218af79250c883b7adc5fc6fc",
    "deploy/oracle/release_v158.py": "73fe055bc215fdf27dcd8062bc01671c898b1dc4",
    "deploy/oracle/release_v159.py": "b14ee7b1efab67913c276d9728216df9750c289a",
    "deploy/oracle/release_v160.py": "fa7387056cd468c7f88564232d1aeb72b883b414",
    "deploy/oracle/release_v161.py": "49834cc0f73300b836dbc915cf49fba0d6157298",
    "deploy/oracle/release_v162.py": "c3bb2ada57097891d83e033fbc3d833cc69c8e65",
    "deploy/oracle/release_v163.py": "19d538c167550e5c3c9326d7cfc3ab5582347e9a",
    "deploy/oracle/release_v164.py": "5cad0abdff8a30f9e7dc583c872c213807863dc4",
    "deploy/oracle/remura-autoupdate.service": "abdbe86a16ab0a806620629b2ede64af14d8bc7d",
    "deploy/oracle/remura-autoupdate.timer": "dca0376a3651de9b947b9f2903a685f9e6db2827",
    "deploy/oracle/remura.service": "56bbca6a35c8fc5c0b748ebad97e89cfcc61e0c9",
    "dual24-core.js": "b9110a4a23091e3204b5e7863d7b05bb1d1ea24b",
    "dual24-ui.js": "553a8a2668499bb4a85df04ca165b77be2a18d56",
    "feed-health-core.js": "9137b41a701ba7604d7c3bed95dd2ec891f00d79",
    "fonti.html": "17b6ebedf83531e070f150d29ad508c1812c0cee",
    "forex.html": "e4f7c9fea8924dd3a1fffed18363e30dd539f8ca",
    "icon.svg": "52ed228ce69f3da5f8bbb54cc0de5cdd1cac2b6f",
    "impostazioni.html": "d772e2e8313148384fc2495faf189f8b1fa9d800",
    "impostazioni.js": "de1cb44a714f36cb0734f48d1fc6a4305a44761d",
    "index.html": "b41ebbf9f768bfa4a57d625620eb9b3f53b3e445",
    "insights-core.js": "9e3dcb235bba772aa8eeab7427c525bdc108b18e",
    "insights.css": "338f8c06910d5088f5d9a1181fe06dcd98f7ddf6",
    "insights.js": "b0000e03eca9f7499918d4830ced7fcc4a02c583",
    "manifest.webmanifest": "6d1034b749a34747cba1e8485277ce3583598f88",
    "market-audit-core.js": "c85d70ed6e019ec42b79f4d56bf1ad46470d12ac",
    "market-audit-ui.js": "95b8b0bdb75ebbc29730ed871e0673a8b803c5c8",
    "mercati.html": "10d20744ed69531d4d51bdda194c01b5fcd116f3",
    "nav.css": "95679269c114c81908ff81c01e124086a4a742ea",
    "nav.js": "d35c9d06f9c64a10938f30ec7e7ae7b2f2c5fbec",
    "price-core.js": "8c6c24cd4c60a3ce219209c39209c8111a0b9a29",
    "price-status-core.js": "bfa5f40687734961d1d37988c59f14938a847bed",
    "price.css": "6e9104b60acaa1f4d7cf31577dad9223b14177e7",
    "price.js": "33efbc371a30244221f1724671283390e4f94ce6",
    "resource-health.css": "8962d1dfab25a66c7f8aac9be7414229b38acd9c",
    "resource-health.js": "7f088282f33edf275e47d2fe674a70ab2f1a4a92",
    "retail.css": "03d92c20d08c25e363b516587d8b4cb0fc5e0e3e",
    "retail.js": "679992eb06c16022f4034cc13b0a784af858f462",
    "scripts/batch_timing.py": "68ef3244b3b4c055121b11be506b436f0551e6ac",
    "scripts/case_audit.py": "1434853216ddc186052e52b29a589191b13a2e74",
    "scripts/configure_ctrader_backup.py": "be08571285021f1acfdb45601f5b6cf27c7f8765",
    "scripts/cot_monitor.py": "f7f7ffec35671ebeb429e4a16713e8d27ad1764d",
    "scripts/cot_week_watch.py": "c998b8efd72bb5e6056068f58a9e3ce20a982504",
    "scripts/ctrader_feed.py": "a23a678b5fbb6fa5de43fabb57fad6a28fa52021",
    "scripts/ctrader_tokens.py": "8d732e8fdc5877d1ac63c0ed8d69ce82c2263c7f",
    "scripts/dual24_validation.py": "30bf4b793579dead0c5a04b12caa3458baf8553e",
    "scripts/h1_batch_comparison.py": "13a58bea9414a8d81b0cb1095fa9e44eab307ecc",
    "scripts/h1_paired_store.py": "8447ae397c4e82dc8d1c5e59a96e8dd347997463",
    "scripts/market_validation.py": "c947e80069c12383e8e3a5fee06bfe5867a5a31c",
    "scripts/myfxbook_safe_sync.py": "6b0a3056d0b6fab5fe0850d6cf60a8dca911e823",
    "scripts/myfxbook_store.py": "e7a0977a02c7ec86f2d03d174a37e208491bd9f4",
    "scripts/price_feed.py": "00a05fbf9098386ea596814048bdf67a4235186f",
    "scripts/price_store.py": "96375ed6319fc917a8bfd76cdc538fa1d911d23a",
    "scripts/private_server.py": "0853194762f3f0340451a69c9ed8b4e0261db42d",
    "scripts/resource_monitor.py": "7f6927cd3a7be4685fd6de4b4c8d6349f2661472",
    "scripts/session_gaps.py": "7a511c01c2fd35bf8b85f55297dcb5c62a66b373",
    "scripts/signals_monitor.py": "0c4769e81ff2d1e0c9065dccc2bb9bd67e322ddd",
    "scripts/squalincome_timing.py": "0034280c51fd05ac382d1f1a6d25da1d52939499",
    "scripts/statistical_validation.py": "931b4265a33c21269c99f4a1ff1b0ee949249fd9",
    "scripts/update_capital.py": "f17d42c286b55f08f5b9762a17bf7d55ad875a7d",
    "scripts/update_ig.py": "6e8d9a15809365103a4f917ecd957a2a772d8fac",
    "scripts/update_myfxbook.py": "63b7838f394253579f8a3ee67be7556c71c75367",
    "scripts/weekly_quality.py": "c8a0ea1acf6f1cc5d47d6992be4a44e47cf7fa2f",
    "sentiment-core.js": "14dc0b453ca658b3399af5a483076bc7517307ea",
    "sentiment-trend-core.js": "96fcac4a47555b43ebaf8509be18eba9b1125a6c",
    "sentiment-trend.css": "3737ae5b1fe37fe211b214178e2e045d037a8368",
    "sentiment-trend.js": "a8b0a4adf5680197072ce7cbbde7672249eec0a0",
    "sources.css": "fe4cc6227feb29c9608ff8232f4642f24672f322",
    "sources.js": "cdc8ace3174baf790a91cb385ef2deefa5b14178",
    "splash-mascot.webp": "60433776bf6a94d2b342023446dc62a409f58962",
    "splash.css": "54a847194847c88c0eca12824f860574e4909aaa",
    "splash.js": "9484df12d5ff9e3b538f5fc513d013d7c641b470",
    "squalincome-diagnostics.js": "4c78bf1dae17a19fb2fc87748b910c3e1ae3a2c2",
    "squalincome-freshness-core.js": "6f77d1ef0012e3fe9a80780e3fbb1290a6ff8e3d",
    "statistica-squali-core.js": "8a4f77a02b93520d2a7be86c91acb92f1f70d124",
    "statistica-squali.html": "4cd8ca9420f95deaa916fa5853d9fae697f0ad0a",
    "statistica-squali.js": "3b69ed485dc89f261164bb881f3b8ba179ee7cef",
    "stato-prezzi.html": "193211906f303db1b8ef9e6c1af4e30e01b6ce4c",
    "stato-prezzi.js": "f262b3a9cc8a6a802bac6bd025bd13c942df87c5",
    "sw.js": "6e447938533ff91183959d1902853634e6a83257",
    "weekly-quality-core.js": "3d0df46951eb8e34a1bfae6156fa99a0a020f17f",
    "weekly-quality-ui.js": "7ba08ce87eadf4c7977598935685d01b633edcd6"
}
STAMP=b"05/11/2026 18:03 (Italia, preparazione)"
LIVE_STAMP=re.compile(rb"\d{2}/\d{2}/20\d{2} \d{2}:\d{2} \(Italia\)")
MAX_CODE=2*1024*1024
MAX_NODES=12000
MAX_DEPTH=8
def blob(data):
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
def code_status(root,p,expected):
    parts=Path(p).parts
    fds=[]
    try:
        fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW);fds.append(fd)
        for part in parts[:-1]:
            fd=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd);fds.append(fd)
        st=os.stat(parts[-1],dir_fd=fd,follow_symlinks=False)
        if not stat.S_ISREG(st.st_mode) or not 0<st.st_size<=MAX_CODE:return "unsafe"
        item=os.open(parts[-1],os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd);fds.append(item)
        a=os.fstat(item)
        if not stat.S_ISREG(a.st_mode) or (a.st_dev,a.st_ino)!=(st.st_dev,st.st_ino):return "unsafe"
        with os.fdopen(os.dup(item),"rb") as h:data=h.read(MAX_CODE+1)
        b=os.fstat(item)
        if len(data)!=a.st_size or (a.st_size,a.st_mtime_ns,a.st_ctime_ns)!=(b.st_size,b.st_mtime_ns,b.st_ctime_ns):return "unstable"
        if blob(data)==expected:return "exact"
        if p=="nav.js":
            found=LIVE_STAMP.findall(data)
            if len(found)==1:
                try:datetime.datetime.strptime(found[0].decode(),"%d/%m/%Y %H:%M (Italia)")
                except ValueError:return "different"
                if blob(data.replace(found[0],STAMP,1))==expected:return "stamp_only"
        return "different"
    except FileNotFoundError:return "missing"
    except OSError:return "unsafe_or_unreadable"
    finally:
        for fd in reversed(fds):os.close(fd)
def private_metadata(root):
    totals={k:{"files":0,"bytes":0} for k in ("sqlite","sqlite_sidecar","json","backup_tree","credentials_or_config","other")}
    nodes=0;links=0;nonregular=0;errors=0;truncated=False
    private=root/"private"
    if not private.is_dir() or private.is_symlink():return {"state":"unavailable"}
    def err(_):
        nonlocal errors
        errors+=1
    for folder,dirs,files,fd in os.fwalk(private,follow_symlinks=False,onerror=err):
        rel=Path(folder).relative_to(private)
        if len(rel.parts)>=MAX_DEPTH and dirs:
            truncated=True;dirs.clear()
        nodes+=len(dirs)+len(files)
        if nodes>MAX_NODES:truncated=True;break
        for name in list(dirs)+files:
            try:s=os.stat(name,dir_fd=fd,follow_symlinks=False)
            except OSError:errors+=1;continue
            if stat.S_ISLNK(s.st_mode):links+=1;continue
            if stat.S_ISDIR(s.st_mode):continue
            if not stat.S_ISREG(s.st_mode):nonregular+=1;continue
            lower=name.lower()
            if rel.parts and rel.parts[0]=="predeploy-backups":kind="backup_tree"
            elif lower.endswith(("-wal","-shm","-journal")):kind="sqlite_sidecar"
            elif lower.endswith((".sqlite",".sqlite3",".db")):kind="sqlite"
            elif any(x in lower for x in ("token","secret","credential","remura.env","apikey","password")) or lower.endswith((".pem",".key")):kind="credentials_or_config"
            elif lower.endswith(".json"):kind="json"
            else:kind="other"
            totals[kind]["files"]+=1;totals[kind]["bytes"]+=s.st_size
    return {"state":"partial" if truncated or errors or links or nonregular else "metadata_only",
            "categories":totals,"nodes":nodes,"symlinks":links,"nonregular":nonregular,
            "errors":errors,"truncated":truncated,"consistent_snapshot":False}
def census(root):
    rows={p:code_status(root,p,h) for p,h in PINS.items()}
    groups={k:0 for k in ("exact","stamp_only","different","missing","unsafe","unstable","unsafe_or_unreadable")}
    for status in rows.values():groups[status]+=1
    anomalous={p:s for p,s in rows.items() if s not in ("exact","stamp_only")}
    disk=shutil.disk_usage(root)
    return {"schema":"remura.v165.installed.baseline.readonly.v1","repository_base":BASE,
            "previously_reported_installed":INSTALLED_REPORTED,"observed_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "expected_paths":len(PINS),"results":groups,"anomalous_public_paths":anomalous,
            "private_metadata":private_metadata(root),"disk_free_bytes":disk.free,
            "gpg_in_path":shutil.which("gpg") is not None,"age_in_path":shutil.which("age") is not None,
            "venv_python_present":(root/".venv/bin/python").is_file(),
            "installed_sdk_verified":False,"unexpected_code_census_verified":False,
            "actual_service_configuration_verified":False,"backup_verified":False,"release_authorized":False}
def main():
    p=argparse.ArgumentParser();p.add_argument("--read-only",action="store_true")
    if not p.parse_args().read_only:p.error("Explicit --read-only required")
    root=Path("/opt/remura")
    if not root.is_dir() or root.is_symlink():p.error("Expected regular /opt/remura directory")
    print(json.dumps(census(root),sort_keys=True))
if __name__=="__main__":main()
