import pytest
from pydantic import ValidationError

from cee.answer.schema import Answer


def test_empty_string_list_fields_become_empty_lists():
    # Q20 real run 2026-10-30: the model sent claims="" and the run crashed.
    a = Answer(answerable=False, behavior="refuse", claims="", adjacent=" ", gaps="", caveats="")
    assert a.claims == [] and a.adjacent == [] and a.gaps == [] and a.caveats == []


def test_json_encoded_list_is_parsed():
    a = Answer(answerable=True, behavior="answer",
               claims='[{"text": "x", "chunk_ids": ["MS-10K-2025#1"]}]')
    assert a.claims[0].chunk_ids == ["MS-10K-2025#1"]


@pytest.mark.parametrize("bad", ["not a list", '{"text": "x"}'])
def test_other_strings_still_fail(bad):
    with pytest.raises(ValidationError):
        Answer(answerable=True, behavior="answer", claims=bad)
