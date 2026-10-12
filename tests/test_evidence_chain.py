"""
Evidence chain integrity (perception/evidence_chain.py).

The chain's whole promise ("no record, no evidence") rests on verify_chain
recomputing hashes and refusing to trust stored values.
"""

import json
import sqlite3

from perception import evidence_chain as ec


def test_empty_chain_is_valid(isolated_dbs):
    result = ec.verify_chain()
    assert result["valid"] is True
    assert result["blocks"] == 0


def test_append_then_verify(isolated_dbs):
    first = ec.add_observation({"a": 1}, terminal="T")
    second = ec.add_observation({"a": 2}, terminal="T")

    assert first["recorded"] is True
    assert first["signed"] is True
    assert second["previous_hash"] == first["block_hash"]

    result = ec.verify_chain()
    assert result["valid"] is True
    assert result["blocks"] == 2
    assert result["verified"] == 2
    assert result["unverified"] == 0


def test_summary_reports_true_flags(isolated_dbs):
    ec.add_observation({"a": 1}, terminal="T")
    ec.add_observation({"a": 2}, terminal="T")

    summary = ec.get_chain_summary()
    assert summary["blocks"] == 2
    assert summary["signed"] == 2
    assert summary["anchored"] == 0  # nothing was anchored yet
    assert summary["tip_hash"] != "0" * 16


def test_tampered_payload_is_detected(isolated_dbs):
    ec.add_observation({"a": 1}, terminal="T")

    conn = sqlite3.connect(str(isolated_dbs["chain"]))
    payload = json.loads(
        conn.execute("SELECT canonical_payload FROM chain").fetchone()[0]
    )
    payload["created_at"] = "1999-01-01T00:00:00+00:00"
    conn.execute(
        "UPDATE chain SET canonical_payload = ?",
        (json.dumps(payload, sort_keys=True, separators=(",", ":")),),
    )
    conn.commit()
    conn.close()

    result = ec.verify_chain()
    assert result["valid"] is False
    assert result["broken_reason"] == "hash_mismatch_at_1"


def test_broken_chain_link_is_detected(isolated_dbs):
    ec.add_observation({"a": 1}, terminal="T")
    ec.add_observation({"a": 2}, terminal="T")

    conn = sqlite3.connect(str(isolated_dbs["chain"]))
    conn.execute("UPDATE chain SET previous_hash = ? WHERE block_index = 2", ("f" * 64,))
    conn.commit()
    conn.close()

    result = ec.verify_chain()
    assert result["valid"] is False
    assert result["broken_reason"] == "broken_link_at_2"
