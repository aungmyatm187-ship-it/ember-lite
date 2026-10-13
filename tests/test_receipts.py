"""
Signed response receipts (perception/receipts.py).

A receipt must verify only for the exact payload it was signed over, and must
fail if the payload, the signature, or the receipt hash is altered.
"""


from perception import receipts


def test_sign_and_verify_roundtrip():
    payload = {"status": "ok", "data": {"blocks": 3, "tip": "abc"}}
    receipt = receipts.sign_receipt(payload, terminal="T")
    assert receipt["signed"] is True
    status = receipts.verify_receipt(receipt)
    assert status["valid"] is True
    assert status["signature_ok"] and status["payload_hash_ok"] and status["receipt_hash_ok"]


def test_tampered_payload_fails():
    receipt = receipts.sign_receipt({"v": 1}, terminal="T")
    receipt["payload"] = {"v": 2}
    status = receipts.verify_receipt(receipt)
    assert status["valid"] is False
    assert status["payload_hash_ok"] is False


def test_tampered_signature_fails():
    receipt = receipts.sign_receipt({"v": 1}, terminal="T")
    receipt["signature"] = "AAAA" + receipt["signature"][4:]
    assert receipts.verify_receipt(receipt)["valid"] is False


def test_tampered_receipt_hash_fails():
    receipt = receipts.sign_receipt({"v": 1}, terminal="T")
    receipt["created_at"] = "2000-01-01T00:00:00+00:00"
    status = receipts.verify_receipt(receipt)
    assert status["valid"] is False
    assert status["receipt_hash_ok"] is False


def test_missing_field_is_reported():
    receipt = receipts.sign_receipt({"v": 1}, terminal="T")
    del receipt["public_key"]
    status = receipts.verify_receipt(receipt)
    assert status["valid"] is False
    assert status["reason"] == "missing_field:public_key"


def test_receipt_is_self_contained():
    receipt = receipts.sign_receipt({"hello": "world"}, terminal="T")
    # Everything needed to verify is inside the receipt itself.
    for key in ("payload", "payload_hash", "signature", "public_key",
                "receipt_hash", "algorithm"):
        assert key in receipt
    assert receipts.format_receipt(receipt).startswith("✅")


def test_receipt_does_not_verify_after_payload_swap():
    a = receipts.sign_receipt({"who": "a"}, terminal="T")
    b = receipts.sign_receipt({"who": "b"}, terminal="T")
    # Splice b's payload into a -- a's signature no longer matches.
    a["payload"] = b["payload"]
    assert receipts.verify_receipt(a)["valid"] is False
