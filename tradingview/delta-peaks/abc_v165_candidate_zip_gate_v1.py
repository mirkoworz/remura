# REMURA v0.8.166 LAB — 18/11/2026, sessione successiva alle 15:52 CET
"""Bounded public candidate ZIP to immutable TAR handoff.
No extraction to supplied paths, signatures inferred, writes, network or CLI.
"""
import hashlib,io,stat,zipfile

ZIP_SIZE=495798
ZIP_SHA="9865ebf4cfc419ad073720b40ae11dfa0757e02d5c863ba53fdcc9ce08c0f5c0"
TAR_SIZE=1771520
TAR_SHA="6804531c819ec16af972755b042394ac5c9acee23b7c03f70a09ab765369cfcc"
NAMES={"remura-v165-candidate.tar","candidate-attestation.json","READ-ME.txt"}

def need(ok):
    if not ok:raise ValueError("CANDIDATE_ZIP_GATE")

def digest(data):return hashlib.sha256(data).hexdigest()

def _decode(data):
    # Only invoked after exact outer pin in production-facing function.
    need(type(data) is bytes and 0<len(data)<=1024*1024)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        infos=z.infolist()
        need(len(infos)==3 and {i.filename for i in infos}==NAMES)
        for i in infos:
            mode=(i.external_attr>>16)&0o170000
            need(not i.is_dir() and mode in (0,stat.S_IFREG)
                 and i.compress_type in (zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED)
                 and not i.flag_bits&1)
            need(0<i.file_size<=(TAR_SIZE if i.filename.endswith(".tar") else 16384))
        with z.open("remura-v165-candidate.tar") as f:
            tar=f.read(TAR_SIZE+1)
        need(len(tar)==TAR_SIZE and digest(tar)==TAR_SHA)
        return tar

def verified_tar(zip_bytes):
    """Validate delivery pin and return same immutable inner bytes only.
    No GPG verification, installation or authorization is implied.
    """
    need(type(zip_bytes) is bytes and len(zip_bytes)==ZIP_SIZE and digest(zip_bytes)==ZIP_SHA)
    return _decode(zip_bytes)
