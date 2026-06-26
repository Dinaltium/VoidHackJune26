from app.detect.rules import inspect_tool_call
from app.schemas import FunctionCall, Status, ToolCall


def _call(name: str, arguments: str) -> ToolCall:
    return ToolCall(id="c", type="function", function=FunctionCall(name=name, arguments=arguments))


def test_denied_tool_blocked(policy):
    f = inspect_tool_call(_call("send_email", '{"to":"a@example.com"}'), policy)
    assert f.status is Status.BLOCK
    assert any("denied" in r or "allowlist" in r for r in f.reasons)


def test_unknown_tool_blocked(policy):
    f = inspect_tool_call(_call("run_shell", "{}"), policy)
    assert f.status is Status.BLOCK


def test_allowed_tool_passes(policy):
    f = inspect_tool_call(_call("read_doc", '{"name":"invoice"}'), policy)
    assert f.status is Status.PASS


def test_egress_allowlisted_host_passes(policy):
    f = inspect_tool_call(_call("http_fetch", '{"url":"https://example.com/x"}'), policy)
    assert f.status is Status.PASS


def test_egress_bad_host_blocked(policy):
    f = inspect_tool_call(_call("http_fetch", '{"url":"https://attacker.com/x"}'), policy)
    assert f.status is Status.BLOCK
    assert any("egress" in r for r in f.reasons)


def test_email_domain_treated_as_egress(policy):
    f = inspect_tool_call(_call("http_fetch", '{"note":"mail to x@evil-exfil.com"}'), policy)
    assert f.status is Status.BLOCK


def test_non_http_scheme_egress_blocked(policy):
    f = inspect_tool_call(_call("http_fetch", '{"url":"ftp://attacker.com/x"}'), policy)
    assert f.status is Status.BLOCK
    assert "attacker.com" in f.hosts


def test_scheme_relative_egress_blocked(policy):
    f = inspect_tool_call(_call("http_fetch", '{"url":"//attacker.com/collect"}'), policy)
    assert f.status is Status.BLOCK


def test_subdomain_of_allowlisted_host_passes(policy):
    f = inspect_tool_call(_call("http_fetch", '{"url":"https://docs.example.com/p"}'), policy)
    assert f.status is Status.PASS


def test_lookalike_suffix_host_blocked(policy):
    f = inspect_tool_call(_call("http_fetch", '{"url":"https://example.com.evil.com/x"}'), policy)
    assert f.status is Status.BLOCK


def test_prefix_lookalike_host_blocked(policy):
    f = inspect_tool_call(_call("http_fetch", '{"url":"https://notexample.com/x"}'), policy)
    assert f.status is Status.BLOCK


def test_secret_in_args_blocked(policy):
    f = inspect_tool_call(
        _call("http_fetch", '{"url":"https://example.com","note":"gsk_ABCDEFGHIJKLMNOPQRSTUV"}'),
        policy,
    )
    assert f.status is Status.BLOCK
    assert f.secrets
