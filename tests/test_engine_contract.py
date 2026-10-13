"""
The ember-lite <-> ember-signal seam.

ember-signal runs ember-lite in a subprocess (ember_signal/engine.py) and calls
a fixed set of names. Those names are the integration contract. If a rename or
signature change lands in ember-lite without updating ember-signal, the
subprocess returns engine_error at runtime instead of failing at review time,
so pin the contract here where CI sees it.
"""

import inspect


def test_perception_layer_surface():
    from perception import layer

    assert callable(layer.perceive)
    assert callable(layer.perceive_summary)
    # engine.py calls perceive_summary(report) on the dict perceive() returns.
    assert list(inspect.signature(layer.perceive_summary).parameters) == ["report"]


def test_release_gate_surface():
    from perception import release_gate

    assert callable(release_gate.evaluate_release)
    assert callable(release_gate.format_gate_report)


def test_evaluate_release_returns_the_documented_keys():
    from perception.release_gate import evaluate_release

    result = evaluate_release(None)  # no perception report
    for key in ("decision", "gates_unknown", "score"):
        assert key in result, f"engine.py relies on evaluate_release[{key!r}]"
    assert result["decision"] in {"SHIP", "REVIEW", "NO_SHIP"}
    # A missing report must not read as a pass.
    assert isinstance(result["gates_unknown"], int)
    assert result["decision"] != "SHIP"


def test_governance_surface():
    from perception.governance import get_governance_summary

    summary = get_governance_summary()
    for key in ("active_policies", "allowed_capabilities", "approval_gates"):
        assert key in summary


def test_evidence_chain_surface():
    from perception.evidence_chain import get_chain_summary, verify_chain

    summary = get_chain_summary()
    assert summary["schema_version"] == "2.0"
    for key in ("blocks", "signed", "anchored", "verified"):
        assert key in summary

    result = verify_chain()
    assert isinstance(result["valid"], bool)
    assert "blocks" in result
