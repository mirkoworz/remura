# REMURA Contributors v0.55 LAB — synthetic POSIX helper, no external operations.
import sys
from pathlib import Path
# Isolated Python does not put the script directory on sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fixture_durable_claim_lab import claim

if __name__ == "__main__":
    try:
        if len(sys.argv) != 2:
            raise RuntimeError("claim_denied")
        claim(sys.argv[1])
        print("SYNTHETIC_CLAIM_CONSUMED", flush=True)
    except Exception:
        raise SystemExit(2) from None
