"""Tests for the AWS JSONPath dialect handled by extract_json.

https://github.com/getmoto/moto/issues/10078
"""

import pytest

from moto.stepfunctions.parser.asl.utils.json_path import (
    NoSuchJsonPathError,
    extract_json,
)


class TestFilterConjunctions:
    def test_double_ampersand_conjunction(self):
        data = {
            "items": [
                {"keep": True, "ready": True},
                {"keep": True, "ready": False},
                {"keep": False, "ready": True},
            ]
        }
        result = extract_json("$.items[?(@.keep == true && @.ready == true)]", data)
        assert result == [{"keep": True, "ready": True}]

    def test_double_pipe_disjunction_preserves_document_order(self):
        data = {"items": [{"k": "a"}, {"k": "c"}, {"k": "b"}]}
        result = extract_json("$.items[?(@.k == 'a' || @.k == 'b')]", data)
        assert result == [{"k": "a"}, {"k": "b"}]

    def test_conjunction_binds_tighter_than_disjunction(self):
        data = {"items": [{"k": "a"}, {"keep": True, "ready": True}]}
        result = extract_json(
            "$.items[?(@.keep == true && @.ready == true || @.k == 'a')]", data
        )
        assert result == [{"k": "a"}, {"keep": True, "ready": True}]

    def test_chained_disjunctions(self):
        data = {"items": [{"k": "a"}, {"k": "c"}, {"k": "b"}]}
        result = extract_json(
            "$.items[?(@.k == 'a' || @.k == 'b' || @.k == 'c')]", data
        )
        assert result == [{"k": "a"}, {"k": "c"}, {"k": "b"}]

    def test_operators_inside_string_literals_are_preserved(self):
        data = {"name": [{"v": "x && y || z"}]}
        result = extract_json("$.name[?(@.v == 'x && y || z')]", data)
        assert result == [{"v": "x && y || z"}]


class TestEmptyFilterResult:
    def test_filter_matching_nothing_yields_empty_list(self):
        result = extract_json("$.items[?(@.k == 'NONE')]", {"items": [{"k": "a"}]})
        assert result == []

    def test_disjunction_matching_nothing_yields_empty_list(self):
        result = extract_json(
            "$.items[?(@.k == 'X' || @.k == 'Y')]", {"items": [{"k": "a"}]}
        )
        assert result == []


class TestExistingBehaviour:
    def test_definite_path(self):
        assert extract_json("$.a.b", {"a": {"b": 42}}) == 42

    def test_missing_definite_path_still_raises(self):
        with pytest.raises(NoSuchJsonPathError):
            extract_json("$.a.missing", {"a": {"b": 42}})

    def test_wildcard_matching_nothing_yields_empty_list(self):
        assert extract_json("$.items[*].k", {"items": []}) == []

    def test_index_access(self):
        assert extract_json("$.items[0]", {"items": [{"k": "a"}]}) == {"k": "a"}
