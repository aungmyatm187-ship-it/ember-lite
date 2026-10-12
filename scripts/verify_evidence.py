#!/usr/bin/env python3
"""
Offline evidence verifier.
==========================
Checks what is actually committed to the repo, with no network access:

1. Every evidence/*.json bundle that has a sibling .sig file must verify
   against its recorded Ed25519 public key.
2. If the local evidence-chain DB exists, verify_chain() must report a valid
   hash chain (tamper detection).

Exit code 0 = all checks passed. Non-zero = at least one check failed, so CI
turns red when a signed bundle is altered or the chain is broken.
"""

import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

EVIDENCE_DIR = REPO / "evidence"


def verify_signed_bundles() -> list[str]:
    """Return a list of failure messages for signed evidence bundles."""
    failures = []
    bundles = sorted(EVIDENCE_DIR.glob("*.json"))
    if not bundles:
        return ["no evidence bundles found in evidence/"]

    from perception.bridge_signatures import verify

    checked = 0
    for bundle in bundles:
        sig_path = bundle.with_suffix(bundle.suffix + ".sig")
        if not sig_path.exists():
            continue
        try:
            payload = json.loads(bundle.read_text())
            sig = json.loads(sig_path.read_text())
            ok = verify(payload, sig["signature"], sig["public_key"])
        except Exception as exc:
            failures.append(f"{bundle.name}: unreadable ({type(exc).__name__}: {exc})")
            continue
        checked += 1
        if not ok:
            failures.append(f"{bundle.name}: signature INVALID")

    if checked == 0:
        failures.append("no signed bundles (*.json + *.sig) found to verify")
    return failures


def verify_chain_db() -> list[str]:
    """Verify the local chain DB if it exists. Absence is not a failure."""
    from perception import evidence_chain as ec

    if not os.path.exists(ec.DB_PATH):
        return []

    result = ec.verify_chain()
    if result["valid"]:
        print(
            f"  chain: valid, {result['blocks']} blocks, "
            f"{result['verified']} signed+verified, tip={result['tip']}"
        )
        return []
    return [
        f"chain BROKEN at block {result['broken_at']}: {result.get('broken_reason')}"
    ]


def main() -> int:
    failures = []
    failures += verify_signed_bundles()
    failures += verify_chain_db()

    if failures:
        print("EVIDENCE VERIFICATION FAILED", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1

    print("EVIDENCE VERIFICATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
