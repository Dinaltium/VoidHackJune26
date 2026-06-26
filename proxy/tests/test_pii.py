from app.detect.pii import redact, scan_and_redact
from app.schemas import Status


def test_redacts_email_and_ssn(policy):
    text = "Contact john.doe@example.com, SSN 123-45-6789."
    out, labels = redact(text, policy)
    assert "john.doe@example.com" not in out
    assert "123-45-6789" not in out
    assert "email" in labels and "ssn" in labels


def test_redacts_secret_key_first(policy):
    text = "key is gsk_ABCDEFGHIJKLMNOPQRSTUV here"
    out, labels = redact(text, policy)
    assert "gsk_ABCDEFGHIJKLMNOPQRSTUV" not in out
    assert "groq_key" in labels


def test_clean_text_untouched(policy):
    text = "The invoice total is 1,828.50 dollars."
    out, labels = redact(text, policy)
    assert out == text
    assert labels == []


def test_scan_and_redact_flags(policy):
    _, check = scan_and_redact("mail me at a@b.com", policy)
    assert check.status is Status.FLAG
    assert "email" in check.meta["labels"]
