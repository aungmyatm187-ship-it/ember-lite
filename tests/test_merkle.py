"""
Merkle tree integrity (perception/merkle.py).

The tree backs anchor commitments: a single root must commit to exactly one
set of leaves. The tests below pin the two properties a broken tree breaks --
no root collisions across different leaf sets, and proofs that verify against
only the root they belong to.
"""

import pytest

from perception import merkle


def _leaves(n):
    return [merkle.hash_leaf({"i": i}) for i in range(n)]


def test_empty_batch_has_no_root():
    assert merkle.build_tree([]) == []
    with pytest.raises(ValueError):
        merkle.root_hash([])


def test_single_leaf_root_is_the_leaf():
    leaf = merkle.hash_leaf({"only": 1})
    assert merkle.root_hash([leaf]) == leaf


@pytest.mark.parametrize("n", range(1, 17))
def test_every_proof_verifies(n):
    leaves = _leaves(n)
    root = merkle.root_hash(leaves)
    for i in range(n):
        proof = merkle.build_proof(leaves, i)
        assert merkle.verify_proof(leaves[i], proof, root), f"leaf {i} of {n}"


def test_tampered_leaf_is_rejected():
    leaves = _leaves(6)
    root = merkle.root_hash(leaves)
    proof = merkle.build_proof(leaves, 3)
    tampered = merkle.hash_leaf({"i": 3, "v": "edited"})
    assert not merkle.verify_proof(tampered, proof, root)


def test_proof_does_not_verify_against_a_different_root():
    proof = merkle.build_proof(_leaves(5), 1)
    other_root = merkle.root_hash(_leaves(7))
    assert not merkle.verify_proof(_leaves(5)[1], proof, other_root)


def test_odd_length_duplication_no_longer_collides():
    # The old builder duplicated a trailing node, so [a, b, c] and [a, b, c, c]
    # shared a root. Different leaf sets must have different roots.
    a, b, c = (merkle.hash_leaf({"i": x}) for x in "abc")
    assert merkle.root_hash([a, b, c]) != merkle.root_hash([a, b, c, c])


def test_leaf_and_internal_node_are_domain_separated():
    a, b = merkle.hash_leaf({"i": 0}), merkle.hash_leaf({"i": 1})
    # A pair hash must never equal a leaf hash of the same serialized inputs.
    assert merkle._hash_pair(a, b) != merkle.hash_leaf({"0": a, "1": b})
    assert merkle.hash_leaf("x") != merkle.hash_leaf({"x": 1})


def test_build_proof_rejects_out_of_range():
    leaves = _leaves(4)
    with pytest.raises(IndexError):
        merkle.build_proof(leaves, 4)
    with pytest.raises(IndexError):
        merkle.build_proof(leaves, -1)


def test_legacy_root_matches_only_for_even_batches():
    even = _leaves(4)
    assert merkle.legacy_root_hash(even) == merkle.root_hash(even)
    odd = _leaves(5)
    assert merkle.legacy_root_hash(odd) != merkle.root_hash(odd)


def test_root_is_deterministic():
    assert merkle.root_hash(_leaves(9)) == merkle.root_hash(_leaves(9))


def test_payload_helper_matches_manual_hashing():
    payloads = [{"a": 1}, {"b": 2}, {"c": 3}]
    manual = merkle.root_hash([merkle.hash_leaf(p) for p in payloads])
    assert merkle.merkle_root_from_payloads(payloads) == manual
