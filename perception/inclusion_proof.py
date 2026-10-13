"""
Merkle inclusion proofs for the evidence chain (Phase C)
=========================================================
Prove that a single block is included in an anchor's Merkle commitment without
revealing the rest of the chain.

Flow:
    anchor  -> commits to merkle_root over N block hashes
    proof   -> (leaf, sibling path) proving one block is under that root
    verifier-> recompute the root from leaf + path, compare to the anchor root

This is the offline-friendly half of an anchor: a holder of the anchor root and
one block's proof can verify inclusion with no access to the chain database.

Anchors created before 2026-10-13 used the duplicated-trailing-node root, so
verification accepts either scheme and reports which one matched.
"""

from __future__ import annotations

import sqlite3

from perception.evidence_chain import DB_PATH, init_chain_db
from perception.merkle import (
    build_proof,
    hash_leaf,
    legacy_root_hash,
    root_hash,
    verify_proof,
)

SCHEMA_VERSION = "1.0"


def _chain_leaves(db_path: str) -> tuple[list[int], list[str], list[str]]:
    """Return (block_indexes, block_hashes, leaf_hashes) in ascending order."""
    init_chain_db()
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT block_index, block_hash FROM chain ORDER BY block_index ASC"
        ).fetchall()
    finally:
        conn.close()
    indexes = [r[0] for r in rows]
    hashes = [r[1] for r in rows]
    leaves = [hash_leaf(h) for h in hashes]
    return indexes, hashes, leaves


def build_chain_inclusion_proof(
    block_index: int,
    db_path: str | None = None,
) -> dict:
    """
    Build an inclusion proof for one block of the chain.

    Returns a self-contained bundle: the block hash, its leaf hash, the sibling
    path, and the Merkle root over the whole chain at this moment.
    """
    path = db_path or DB_PATH
    indexes, hashes, leaves = _chain_leaves(path)

    if block_index not in indexes:
        return {"error": "block_not_found", "block_index": block_index}

    pos = indexes.index(block_index)
    root = root_hash(leaves)

    return {
        "schema_version": SCHEMA_VERSION,
        "block_index": block_index,
        "block_hash": hashes[pos],
        "leaf": leaves[pos],
        "proof": build_proof(leaves, pos),
        "merkle_root": root,
        "block_count": len(leaves),
        "scheme": "promote",
    }


def verify_chain_inclusion_proof(bundle: dict) -> dict:
    """
    Verify a proof bundle on its own terms: does the leaf, with its path,
    recompute the bundle's own Merkle root?
    """
    required = ("leaf", "proof", "merkle_root")
    for key in required:
        if key not in bundle:
            return {"valid": False, "reason": f"missing_field:{key}"}

    ok = verify_proof(bundle["leaf"], bundle["proof"], bundle["merkle_root"])
    return {
        "valid": ok,
        "block_index": bundle.get("block_index"),
        "merkle_root": bundle["merkle_root"],
        "scheme": "promote",
    }


def verify_inclusion_against_anchor(
    bundle: dict,
    anchor: dict,
    block_hashes: list[str] | None = None,
) -> dict:
    """
    Verify a proof bundle against an anchor commitment.

    Checks two independent things:
      1. The bundle's Merkle root equals the anchor's merkle_root.
      2. The leaf + proof path recompute that root.

    If `block_hashes` is provided, the anchor's root is also recomputed from the
    claimed leaves, so the caller does not have to trust the anchor's stored
    root. Either the promote or the legacy root is accepted, and the matching
    scheme is reported.
    """
    anchor_root = anchor.get("merkle_root")
    if anchor_root is None:
        return {"valid": False, "reason": "anchor_missing_merkle_root"}

    root_matches = bundle.get("merkle_root") == anchor_root
    proof_ok = verify_proof(
        bundle.get("leaf"), bundle.get("proof", []), anchor_root
    )

    scheme = None
    if block_hashes is not None:
        leaves = [hash_leaf(bh) for bh in block_hashes]
        if len(leaves) != anchor.get("block_count", len(leaves)):
            return {"valid": False, "reason": "block_count_mismatch"}
        if root_hash(leaves) == anchor_root:
            scheme = "promote"
        elif legacy_root_hash(leaves) == anchor_root:
            scheme = "legacy_duplicate"
        else:
            return {"valid": False, "reason": "anchor_root_mismatch"}

    return {
        "valid": bool(root_matches and proof_ok),
        "root_matches_anchor": bool(root_matches),
        "proof_ok": bool(proof_ok),
        "block_index": bundle.get("block_index"),
        "merkle_root": anchor_root,
        "scheme": scheme,
    }
