"""Tests for governance consolidation fixes."""

from shared.governance.primitives import (
    Candidate,
    FallbackChain,
    Veto,
    VetoChain,
)


def test_fallback_chain_evaluates_nested_veto_chain():
    """Candidate with a denying veto_chain should be skipped."""
    deny_chain: VetoChain[str] = VetoChain([Veto("always_deny", lambda _ctx: False, axiom="test")])
    chain: FallbackChain[str, str] = FallbackChain(
        [
            Candidate("vetoed", lambda _ctx: True, "action_a", veto_chain=deny_chain),
            Candidate("allowed", lambda _ctx: True, "action_b"),
        ],
        default="fallback",
    )
    result = chain.select("any_context")
    assert result.action == "action_b"
    assert result.selected_by == "allowed"


def test_fallback_chain_nested_veto_allows():
    """Candidate with an allowing veto_chain should be selected."""
    allow_chain: VetoChain[str] = VetoChain([Veto("always_allow", lambda _ctx: True)])
    chain: FallbackChain[str, str] = FallbackChain(
        [Candidate("gated", lambda _ctx: True, "action_a", veto_chain=allow_chain)],
        default="fallback",
    )
    result = chain.select("any_context")
    assert result.action == "action_a"
    assert result.selected_by == "gated"


def test_governor_wrapper_collects_all_denials():
    """GovernorWrapper should evaluate all policies, not stop at first denial."""
    from shared.governance.consent_label import ConsentLabel
    from shared.governance.governor import GovernorPolicy, GovernorWrapper
    from shared.governance.labeled import Labeled

    gov = GovernorWrapper("test-agent")
    gov.add_input_policy(GovernorPolicy("policy_a", lambda _aid, _data: False, axiom_id="ax1"))
    gov.add_input_policy(GovernorPolicy("policy_b", lambda _aid, _data: False, axiom_id="ax2"))
    data = Labeled(value="test", label=ConsentLabel.bottom())
    result = gov.check_input(data)
    assert not result.allowed
    assert result.denial is not None
    assert "policy_a" in result.denial.reason
    assert "policy_b" in result.denial.reason
    assert "ax1" in result.denial.axiom_ids
    assert "ax2" in result.denial.axiom_ids
