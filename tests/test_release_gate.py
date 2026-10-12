"""
Release gate decision semantics (perception/release_gate.py).

Two properties matter for trust:
1. A gate with no usable input is UNKNOWN, never a silent default.
2. SHIP is impossible unless every gate was actually evaluated.
"""

import sqlite3

from perception import bridge_router, bridge_transport, evidence_chain
from perception import release_gate as rg
import provenance


def _seed_perception(path, status="healthy", confidence=95):
    conn = sqlite3.connect(path)
    conn.execute(
        "INSERT INTO observations (source, category, status, confidence, data) "
        "VALUES ('backend', 'health', ?, ?, '{}')",
        (status, confidence),
    )
    conn.commit()
    conn.close()


def _seed_evidence():
    bridge_router._add_signed_node(
        node_type="command", label="test", data={"cmd": "ls"}, terminal="T"
    )


def _seed_transport():
    bridge_transport.init_bridge_db()
    bridge_transport.create_channel("ember://test/main")
    bridge_transport.send_message(
        channel="ember://test/main",
        sender="T",
        payload={"hello": "world"},
        recipient="@",
        idempotency_key="seed-1",
    )


def _seed_regression_history():
    rg.init_gate_db()
    conn = sqlite3.connect(rg.DB_PATH)
    for i, score in enumerate((95, 95)):
        conn.execute(
            "INSERT INTO evaluations "
            "(evaluation_id, decision, score, gates_passed, gates_total, summary) "
            "VALUES (?, 'SHIP', ?, 6, 6, 'seed')",
            (f"seed-{i}", score),
        )
    conn.commit()
    conn.close()


def test_missing_data_never_ships(isolated_dbs):
    """With no evidence anywhere, the gate must not claim SHIP."""
    result = rg.evaluate_release(None)
    assert result["decision"] != "SHIP"
    assert result["gates_unknown"] > 0
    unknown = [r for r in result["results"] if r["status"] == "UNKNOWN"]
    assert unknown, "expected at least one UNKNOWN gate"
    assert all("reason" in r["details"] for r in unknown)


def test_unknown_gates_excluded_from_score(isolated_dbs, perception_db):
    """Only the one present gate (security) contributes to the score."""
    _seed_perception(perception_db, status="healthy")
    result = rg.evaluate_release(None)
    security = next(r for r in result["results"] if r["gate"] == "security")
    assert security["status"] == "PASS"
    assert result["score"] == 100  # nothing but the security gate counted
    assert result["decision"] == "REVIEW"  # yet it cannot SHIP


def test_critical_observation_fails_security(isolated_dbs, perception_db):
    _seed_perception(perception_db, status="critical")
    result = rg.evaluate_release(None)
    security = next(r for r in result["results"] if r["gate"] == "security")
    assert security["status"] == "FAIL"
    assert result["decision"] == "NO_SHIP"


def test_all_gates_present_can_ship(isolated_dbs, perception_db):
    _seed_perception(perception_db, status="healthy")
    _seed_evidence()
    _seed_transport()
    _seed_regression_history()
    provenance.init_db()

    result = rg.evaluate_release({"analysis": {"overall_confidence": 95}})
    assert result["gates_unknown"] == 0
    assert result["gates_passed"] == result["gates_total"] == 6
    assert result["score"] >= 90
    assert result["decision"] == "SHIP"
