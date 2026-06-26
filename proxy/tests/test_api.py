from app.main import app
from fastapi.testclient import TestClient

from tests.conftest import FakeGroqClient


def test_health():
    with TestClient(app) as c:
        r = c.get("/health")
        assert r.status_code == 200
        assert r.json()["groq_enabled"] is False


def test_missing_messages_returns_400():
    with TestClient(app) as c:
        r = c.post("/v1/chat/completions", json={"model": "x"})
        assert r.status_code == 400


def test_blocks_malicious_tool_call(malicious_completion):
    with TestClient(app) as c:
        fake = FakeGroqClient()
        fake.next_completion = malicious_completion
        app.state.engine.client = fake

        r = c.post(
            "/v1/chat/completions",
            json={
                "model": "victim",
                "messages": [{"role": "user", "content": "summarize invoice"}],
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body["firewall"]["action"] == "block"
        assert not body["choices"][0]["message"].get("tool_calls")

        receipts = c.get("/api/receipts").json()["receipts"]
        blocked = [x for x in receipts if x["decision"]["action"] == "block"]
        assert blocked
        verified = c.get(f"/api/receipts/{blocked[0]['id']}").json()
        assert verified["verified"] is True


def test_allows_benign_tool_call(benign_completion):
    with TestClient(app) as c:
        fake = FakeGroqClient()
        fake.next_completion = benign_completion
        app.state.engine.client = fake

        r = c.post(
            "/v1/chat/completions",
            json={"model": "victim", "messages": [{"role": "user", "content": "read invoice"}]},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["firewall"]["action"] == "allow"
        assert body["choices"][0]["message"]["tool_calls"]


def test_seed_and_stats():
    with TestClient(app) as c:
        c.post("/api/reset")
        assert c.post("/api/seed").json()["ok"] is True
        stats = c.get("/api/stats").json()
        assert {"allow", "redact", "block", "total"} <= set(stats)


def test_policy_endpoint():
    with TestClient(app) as c:
        pol = c.get("/api/policy").json()
        assert "tool_allowlist" in pol and "egress_allowlist" in pol
