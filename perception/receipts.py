"""
Signed response receipts (Phase C)
===================================
An Ed25519 receipt over an arbitrary response payload, so a client can verify
that a response really came from this engine and was not altered in transit.

Design:
    receipt = {
        schema_version, created_at,
        payload,               # the exact response body
        payload_hash,          # sha256 of the canonical payload
        signature, public_key, # Ed25519 over the canonical payload
        receipt_hash,          # sha256 over the receipt minus receipt_hash
    }

The payload is embedded so a verifier needs nothing but the receipt itself. A
receipt fails if the payload, the signature, or the receipt hash is altered.

Signing is done by perception.bridge_signatures (Ed25519); no network, no keys
beyond the engine's own keypair.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

SCHEMA_VERSION = "1.0"

# Fields covered by receipt_hash. Excludes receipt_hash itself.
_HASHED_FIELDS = (
    "schema_version",
    "created_at",
    "payload",
    "payload_hash",
    "signature",
    "public_key",
    "algorithm",
)


def _canonical(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"),
                      default=str).encode("utf-8")


def _hash(payload: Any) -> str:
    return hashlib.sha256(_canonical(payload)).hexdigest()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sign_receipt(payload: Any, terminal: str = "T") -> dict:
    """
    Build a signed receipt over `payload`.

    Returns the receipt dict, or {"signed": False, "error": ...} if signing is
    unavailable (for example `cryptography` is not installed). It never returns
    a receipt claiming a signature it does not have.
    """
    from perception.bridge_signatures import sign

    try:
        signed = sign(payload, terminal=terminal)
    except Exception as exc:
        return {"signed": False, "error": f"{type(exc).__name__}: {exc}"}

    receipt = {
        "schema_version": SCHEMA_VERSION,
        "created_at": _now_iso(),
        "payload": payload,
        "payload_hash": _hash(payload),
        "signature": signed["signature"],
        "public_key": signed["public_key"],
        "algorithm": signed.get("algorithm", "Ed25519"),
        "terminal": signed.get("terminal", terminal),
        "signed": True,
    }
    receipt["receipt_hash"] = _hash({k: receipt[k] for k in _HASHED_FIELDS})
    return receipt


def verify_receipt(receipt: dict) -> dict:
    """
    Verify a receipt: payload hash, Ed25519 signature, and receipt hash.

    Every check is reported separately so a caller can see which property broke.
    """
    for key in _HASHED_FIELDS + ("receipt_hash",):
        if key not in receipt:
            return {"valid": False, "reason": f"missing_field:{key}"}

    payload_hash_ok = _hash(receipt["payload"]) == receipt["payload_hash"]
    receipt_hash_ok = (
        _hash({k: receipt[k] for k in _HASHED_FIELDS}) == receipt["receipt_hash"]
    )

    signature_ok = False
    try:
        from perception.bridge_signatures import verify
        signature_ok = verify(
            receipt["payload"], receipt["signature"], receipt["public_key"]
        )
    except Exception:
        signature_ok = False

    return {
        "valid": bool(payload_hash_ok and receipt_hash_ok and signature_ok),
        "payload_hash_ok": payload_hash_ok,
        "receipt_hash_ok": receipt_hash_ok,
        "signature_ok": signature_ok,
        "algorithm": receipt.get("algorithm"),
        "created_at": receipt.get("created_at"),
    }


def format_receipt(receipt: dict) -> str:
    """One-line human summary of a receipt for logs and CLI output."""
    if not receipt.get("signed", "receipt_hash" in receipt):
        return f"❌ unsigned: {receipt.get('error', 'unknown')}"
    status = verify_receipt(receipt)
    mark = "✅" if status["valid"] else "❌"
    return (
        f"{mark} receipt {receipt.get('receipt_hash', '')[:12]} "
        f"alg={receipt.get('algorithm')} "
        f"sig={'ok' if status['signature_ok'] else 'BAD'} "
        f"hash={'ok' if status['receipt_hash_ok'] else 'BAD'}"
    )
