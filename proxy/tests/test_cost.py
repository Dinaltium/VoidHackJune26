from app.detect.cost import check_budget, estimate_tokens
from app.schemas import Status


def test_estimate_tokens_counts_content():
    payload = {"messages": [{"role": "user", "content": "x" * 400}]}
    assert estimate_tokens(payload) >= 100


def test_budget_ok_under_limit(policy):
    assert check_budget(100, policy).status is Status.PASS


def test_budget_block_over_limit(policy):
    over = policy.token_budget_per_session + 1
    assert check_budget(over, policy).status is Status.BLOCK
