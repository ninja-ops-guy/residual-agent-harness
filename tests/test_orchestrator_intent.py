import pytest

from residual.core import ContractError
from residual.orchestrator import Intent


def test_intent_minimal_valid():
    intent = Intent(goal="ship orchestration")
    assert intent.goal == "ship orchestration"
    assert intent.constraints == ()
    assert intent.context_refs == ()


def test_intent_rejects_empty_goal():
    with pytest.raises(ContractError):
        Intent(goal="   ")
    with pytest.raises(ContractError):
        Intent(goal="")


def test_intent_rejects_non_sequence_constraints():
    with pytest.raises(ContractError):
        Intent(goal="g", constraints="not-a-sequence")


def test_intent_rejects_blank_entries():
    with pytest.raises(ContractError):
        Intent(goal="g", constraints=("",))
    with pytest.raises(ContractError):
        Intent(goal="g", context_refs=(None,))


def test_intent_canonicalizes_order_and_duplicates():
    a = Intent(goal="g", constraints=("b", "a", "b"), context_refs=("z", "y"))
    b = Intent(goal="g", constraints=("a", "b"), context_refs=("y", "z"))
    assert a.constraints == ("a", "b")
    assert a == b
    assert a.content_hash == b.content_hash


def test_intent_roundtrip():
    intent = Intent(goal="g", constraints=("c1",), context_refs=("docs/x.md",))
    clone = Intent.from_dict(intent.to_dict())
    assert clone == intent
    assert clone.content_hash == intent.content_hash


def test_intent_hash_is_hex_sha256():
    h = Intent(goal="g").content_hash
    assert len(h) == 64
    int(h, 16)


def test_intent_immutable():
    intent = Intent(goal="g")
    with pytest.raises(Exception):
        intent.goal = "other"
