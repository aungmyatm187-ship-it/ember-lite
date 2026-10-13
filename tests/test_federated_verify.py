"""
Anchor verification across the Merkle scheme change (perception/federated_verify.py).

An anchor created before 2026-10-13 used the duplicated-trailing-node root. After
the fix, verification must still accept that anchor (its commitment is authentic)
while labelling which scheme it used -- and must reject a genuine mismatch.
"""

from perception import federated_verify as fv
from perception import merkle


def _anchor(root, block_count):
    a = {
        "anchor_id": "anc-test",
        "schema_version": "1.0",
        "device_id": "T",
        "sequence_number": 1,
        "merkle_root": root,
        "first_block_index": 1,
        "last_block_index": block_count,
        "block_count": block_count,
        "previous_anchor_hash": None,
        "created_at": "2026-01-01T00:00:00+00:00",
    }
    a["anchor_hash"] = fv._hash(a)
    return a


def _block_hashes(n):
    return [merkle.hash_leaf({"block": i}) for i in range(n)]


def test_new_scheme_anchor_verifies_as_promote():
    blocks = _block_hashes(5)  # odd count exercises the promote path
    leaves = [merkle.hash_leaf(b) for b in blocks]
    a = _anchor(merkle.root_hash(leaves), len(blocks))
    r = fv.verify_anchor_bundle(a, blocks)
    assert r["merkle_ok"] is True
    assert r["merkle_scheme"] == "promote"


def test_legacy_scheme_anchor_still_verifies():
    blocks = _block_hashes(63)  # odd count, like the committed 63-block vault
    leaves = [merkle.hash_leaf(b) for b in blocks]
    a = _anchor(merkle.legacy_root_hash(leaves), len(blocks))
    r = fv.verify_anchor_bundle(a, blocks)
    assert r["merkle_ok"] is True
    assert r["merkle_scheme"] == "legacy_duplicate"


def test_wrong_root_is_rejected():
    blocks = _block_hashes(6)
    a = _anchor("f" * 64, len(blocks))
    r = fv.verify_anchor_bundle(a, blocks)
    assert r["merkle_ok"] is False
    assert r["valid"] is False


def test_block_count_mismatch_is_rejected():
    blocks = _block_hashes(4)
    leaves = [merkle.hash_leaf(b) for b in blocks]
    a = _anchor(merkle.root_hash(leaves), 5)
    r = fv.verify_anchor_bundle(a, blocks)
    assert r["merkle_ok"] is False
