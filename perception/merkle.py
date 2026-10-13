"""
Ember Merkle Tree (Phase 6)
=============================
Minimal, auditable Merkle tree for evidence-chain batching.

Design:
    - SHA-256, canonical leaf ordering (ascending block_index)
    - Domain separation: leaf prefix 0x00, internal node prefix 0x01
      (RFC 6962 style), so a leaf can never be read as an internal node
    - Non-recursive construction (fits Tab A memory)
    - A lone node at the end of a level is PROMOTED unchanged; it is never
      duplicated. Duplication lets two different leaf sets share a root.
    - Inclusion proof generation and offline verification
    - No external dependencies

Why Merkle:
    A single anchor root commits to every block in the batch. Anyone can prove
    that any block is included without seeing the rest.

Compatibility note (2026-10-13):
    Older builds duplicated a trailing odd node (Bitcoin-style) and let
    build_proof pad each level independently of build_tree. That made
    root([a, b, c]) equal root([a, b, c, c]) and could emit a proof that paired
    a node with itself. root_hash() now promotes the lone node instead.
    legacy_root_hash() reproduces the old value only so a pre-existing anchor
    can still be re-verified during migration; never use it for new anchors.

Pure Python stdlib only.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def _hash_leaf(data: Any) -> str:
    """Leaf hash: SHA256(0x00 || canonical_bytes)."""
    if isinstance(data, (dict, list)):
        payload = json.dumps(
            data, sort_keys=True, separators=(",", ":"), default=str,
        ).encode("utf-8")
    elif isinstance(data, bytes):
        payload = data
    else:
        payload = str(data).encode("utf-8")
    return hashlib.sha256(b"\x00" + payload).hexdigest()


def _hash_pair(left: str, right: str) -> str:
    """Internal node: SHA256(0x01 || left || right)."""
    return hashlib.sha256(
        b"\x01" + left.encode("ascii") + right.encode("ascii")
    ).hexdigest()


def _next_level(current: list[str]) -> list[str]:
    """One level up: pair left-to-right, promote a lone trailing node."""
    nxt = [
        _hash_pair(current[i], current[i + 1])
        for i in range(0, len(current) - 1, 2)
    ]
    if len(current) % 2 == 1:
        nxt.append(current[-1])
    return nxt


def build_tree(leaves: list[str]) -> list[list[str]]:
    """
    Build a Merkle tree bottom-up from already-hashed leaves.

    Returns levels; levels[0] = leaf hashes, levels[-1] = [root]. An empty
    input returns [] -- there is no root of nothing.
    """
    if not leaves:
        return []
    current = list(leaves)
    levels = [current]
    while len(current) > 1:
        current = _next_level(current)
        levels.append(current)
    return levels


def root_hash(leaves: list[str]) -> str:
    """Root over `leaves`. Raises ValueError on an empty batch."""
    levels = build_tree(leaves)
    if not levels:
        raise ValueError("cannot compute a Merkle root over an empty batch")
    return levels[-1][0]


def legacy_root_hash(leaves: list[str]) -> str:
    """
    Reproduce the pre-2026-10-13 root, which duplicated a trailing odd node.

    Kept only so an anchor created by an older build can be re-verified. This
    construction is cryptographically unsound; do not use it for new anchors.
    """
    if not leaves:
        raise ValueError("cannot compute a Merkle root over an empty batch")
    current = list(leaves)
    while len(current) > 1:
        if len(current) % 2 == 1:
            current = current + [current[-1]]
        current = [
            _hash_pair(current[i], current[i + 1])
            for i in range(0, len(current), 2)
        ]
    return current[0]


def build_proof(leaves: list[str], index: int) -> list[dict]:
    """
    Build a Merkle proof for the leaf at `index`.

    A list of {"position": "left"|"right", "hash": str}. Each step comes from
    the same level walk build_tree uses, so a proof never pairs a node with
    itself.
    """
    if index < 0 or index >= len(leaves):
        raise IndexError(f"index {index} out of range")

    proof: list[dict] = []
    current = list(leaves)
    idx = index
    while len(current) > 1:
        if idx % 2 == 1:
            proof.append({"position": "left", "hash": current[idx - 1]})
        elif idx + 1 < len(current):
            proof.append({"position": "right", "hash": current[idx + 1]})
        # else: idx is the promoted lone node -- no sibling at this level.
        current = _next_level(current)
        idx //= 2
    return proof


def verify_proof(leaf: str, proof: list[dict], expected_root: str) -> bool:
    """Recompute the root from a leaf hash + proof and compare."""
    current = leaf
    for step in proof:
        if step["position"] == "left":
            current = _hash_pair(step["hash"], current)
        elif step["position"] == "right":
            current = _hash_pair(current, step["hash"])
        else:
            return False
    return current == expected_root


def merkle_root_from_payloads(payloads: list[Any]) -> str:
    """Convenience: hash a list of payloads and return the root."""
    return root_hash([_hash_leaf(p) for p in payloads])


def hash_leaf(data: Any) -> str:
    """Public wrapper for leaf hashing."""
    return _hash_leaf(data)


if __name__ == "__main__":
    payloads = [{"i": i, "v": f"obs-{i}"} for i in range(7)]
    leaves = [_hash_leaf(p) for p in payloads]
    root = root_hash(leaves)
    print("Root:", root[:24], "...")
    for i in range(len(leaves)):
        assert verify_proof(leaves[i], build_proof(leaves, i), root), i
    print(f"OK: all {len(leaves)} proofs verified")
    assert not verify_proof(_hash_leaf({"tampered": True}), build_proof(leaves, 0), root)
    print("OK: tampered leaf rejected")
    a, b, c = (_hash_leaf({"i": x}) for x in "abc")
    assert root_hash([a, b, c]) != root_hash([a, b, c, c])
    print("OK: odd-length duplication no longer collides")
