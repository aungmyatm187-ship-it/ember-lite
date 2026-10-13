"""
Merkle inclusion proofs (perception/inclusion_proof.py).

A proof must let a holder of one block and an anchor root confirm inclusion
without the rest of the chain, and must fail when the block or root is wrong.
"""

import pytest

from perception import evidence_chain, merkle
from perception import inclusion_proof as ip


@pytest.fixture()
def chain(tmp_path, monkeypatch):
    db = str(tmp_path / "chain.db")
    monkeypatch.setattr(evidence_chain, "DB_PATH", db)
    for i in range(5):  # odd count exercises the promote path
        evidence_chain.add_observation({"kind": "test", "i": i}, terminal="T")
    return db


def _anchor_for(db):
    _, _, leaves = ip._chain_leaves(db)
    return {
        "merkle_root": merkle.root_hash(leaves),
        "block_count": len(leaves),
    }


def test_proof_verifies_for_every_block(chain):
    indexes, _, _ = ip._chain_leaves(chain)
    for idx in indexes:
        bundle = ip.build_chain_inclusion_proof(idx, db_path=chain)
        assert ip.verify_chain_inclusion_proof(bundle)["valid"], idx


def test_proof_bundle_is_self_contained(chain):
    bundle = ip.build_chain_inclusion_proof(1, db_path=chain)
    for key in ("block_index", "block_hash", "leaf", "proof",
                "merkle_root", "block_count", "scheme"):
        assert key in bundle


def test_missing_block_reports_not_found(chain):
    assert ip.build_chain_inclusion_proof(999, db_path=chain)["error"] == "block_not_found"


def test_tampered_leaf_fails(chain):
    bundle = ip.build_chain_inclusion_proof(0, db_path=chain)
    bundle["leaf"] = merkle.hash_leaf({"tampered": True})
    assert ip.verify_chain_inclusion_proof(bundle)["valid"] is False


def test_verifies_against_anchor(chain):
    anchor = _anchor_for(chain)
    bundle = ip.build_chain_inclusion_proof(2, db_path=chain)
    _, hashes, _ = ip._chain_leaves(chain)
    r = ip.verify_inclusion_against_anchor(bundle, anchor, block_hashes=hashes)
    assert r["valid"] is True
    assert r["scheme"] == "promote"


def test_proof_for_one_block_does_not_verify_against_another_blocks_root(chain):
    bundle = ip.build_chain_inclusion_proof(0, db_path=chain)
    wrong_anchor = {"merkle_root": "f" * 64, "block_count": 5}
    assert ip.verify_inclusion_against_anchor(bundle, wrong_anchor)["valid"] is False


def test_legacy_anchor_scheme_is_recognised(chain):
    _, hashes, leaves = ip._chain_leaves(chain)
    legacy_root = merkle.legacy_root_hash(leaves)
    # A legacy anchor root is not the promote root; a promote proof cannot match
    # it, but verification names the scheme when recomputing from leaves.
    bundle = ip.build_chain_inclusion_proof(0, db_path=chain)
    anchor = {"merkle_root": legacy_root, "block_count": len(leaves)}
    r = ip.verify_inclusion_against_anchor(bundle, anchor, block_hashes=hashes)
    assert r["scheme"] == "legacy_duplicate"
    # The promote proof is correctly rejected against the legacy root.
    assert r["valid"] is False


def test_block_count_mismatch_is_rejected(chain):
    anchor = _anchor_for(chain)
    bundle = ip.build_chain_inclusion_proof(0, db_path=chain)
    _, hashes, _ = ip._chain_leaves(chain)
    bad = {"merkle_root": anchor["merkle_root"], "block_count": len(hashes) + 1}
    r = ip.verify_inclusion_against_anchor(bundle, bad, block_hashes=hashes)
    assert r["valid"] is False
    assert r["reason"] == "block_count_mismatch"
