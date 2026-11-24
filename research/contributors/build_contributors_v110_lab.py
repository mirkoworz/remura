"""Build the standalone Worker and the scoped staging release archive offline."""

import argparse
import hashlib
from pathlib import Path
import subprocess
import tempfile
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


SOURCE = Path(__file__).resolve().parent
ENTRY = SOURCE / "staging_contributors_v110_lab.mjs"
MANUAL = SOURCE / "REMURA-CONTRIBUTORS-V110-LAB.md"
SLOTS = SOURCE / "staging-slots-v110.sql"
LEVELS = SOURCE / "staging-levels-v110.sql"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--esbuild", default="esbuild", help="path to an installed esbuild executable")
    parser.add_argument("--output", required=True, type=Path, help="new ZIP file")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="remura-v110-") as temporary:
        worker = Path(temporary) / "worker-v110.mjs"
        subprocess.run(
            [
                args.esbuild,
                str(ENTRY),
                "--bundle",
                "--format=esm",
                "--platform=browser",
                "--target=es2022",
                f"--outfile={worker}",
            ],
            cwd=SOURCE,
            check=True,
        )
        levels = LEVELS.read_bytes()
        files = {
            "README.md": MANUAL.read_bytes(),
            "worker-v110.mjs": worker.read_bytes(),
            "migration-from-v105.sql": SLOTS.read_bytes() + b"\n" + levels,
            "migration-from-v109.sql": levels,
        }
    checksums = [f"{hashlib.sha256(data).hexdigest()}  {name}\n" for name, data in files.items()]
    files["SHA256SUMS"] = "".join(checksums).encode("ascii")
    with ZipFile(args.output, "x", compression=ZIP_DEFLATED) as archive:
        for name, data in files.items():
            member = ZipInfo(name, date_time=(2026, 11, 24, 23, 15, 0))
            archive.writestr(member, data, compress_type=ZIP_DEFLATED, compresslevel=9)
    print(hashlib.sha256(args.output.read_bytes()).hexdigest(), args.output)


if __name__ == "__main__":
    main()
