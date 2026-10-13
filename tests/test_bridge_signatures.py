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


def test_sign_returns_truthful_key_id_and_payload_hash():
    import hashlib
    import json

    payload = {"a": 1, "b": [2, 3]}
    out = bs.sign(payload, terminal="T")

    # payload_hash is the real sha256 of the canonical signed bytes.
    data = json.dumps(payload, sort_keys=True).encode()
    assert out["payload_hash"] == hashlib.sha256(data).hexdigest()
    assert len(out["payload_hash"]) == 64

    # key_id is a stable fingerprint of the public key; the old "lib" field is gone.
    assert len(out["key_id"]) == 16
    assert "lib" not in out


def test_key_id_is_stable_and_key_specific(tmp_path, monkeypatch):
    monkeypatch.setattr(bs, "KEY_DIR", str(tmp_path / "keys"))
    a = bs.sign({"x": 1}, terminal="A")
    a2 = bs.sign({"x": 2}, terminal="A")
    b = bs.sign({"x": 1}, terminal="B")
    assert a["key_id"] == a2["key_id"]   # same key -> same id
    assert a["key_id"] != b["key_id"]    # different key -> different id

