"""
Bridge signature round-trip (perception/bridge_signatures.py).

Ed25519 must reject tampered payloads and accept authentic ones.
"""

from perception import bridge_signatures as bs


def test_sign_verify_roundtrip():
    payload = {"command": "git status", "channel": "termux"}
    signed = bs.sign(payload, terminal="T")
    assert signed["algorithm"] == "Ed25519"
    assert bs.verify(payload, signed["signature"], signed["public_key"]) is True


def test_tampered_payload_rejected():
    payload = {"command": "git status"}
    signed = bs.sign(payload, terminal="T")
    tampered = {"command": "rm -rf /"}
    assert bs.verify(tampered, signed["signature"], signed["public_key"]) is False


def test_malformed_signature_rejected():
    assert bs.verify({"a": 1}, "not-base64!!", "also-bad") is False
