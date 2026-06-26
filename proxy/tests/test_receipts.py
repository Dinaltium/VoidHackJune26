from app.receipts import sign, verify
from app.schemas import Action, Decision, Receipt


def _receipt() -> Receipt:
    return Receipt(
        id="rcpt-1",
        ts="2026-06-27T00:00:00+00:00",
        session_id="s1",
        model="victim",
        direction="outbound",
        decision=Decision(action=Action.BLOCK, reason="egress blocked"),
        request_summary={"model": "victim", "n_messages": 2},
    )


def test_sign_then_verify_ok():
    r = sign(_receipt(), "secret")
    assert r.payload_hash and r.signature
    assert verify(r, "secret") is True


def test_tampered_decision_fails_verification():
    r = sign(_receipt(), "secret")
    r.decision.reason = "tampered"  # mutate after signing
    assert verify(r, "secret") is False


def test_wrong_secret_fails():
    r = sign(_receipt(), "secret")
    assert verify(r, "other-secret") is False


def test_tampered_signature_fails():
    r = sign(_receipt(), "secret")
    r.signature = "0" * 64
    assert verify(r, "secret") is False
