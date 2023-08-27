import pytest

from moto.logs.logs_query.query_parser import parse_query


@pytest.mark.parametrize(
    "query,fields,limit,sort",
    [
        ("fields @timestamp", ["@timestamp"], None, []),
        ("fields @timestamp, @message", ["@timestamp", "@message"], None, []),
        ("limit 42", [], 42, []),
        ("sort @timestamp desc", [], None, [("@timestamp", "desc")]),
        ("sort @timestamp asc", [], None, [("@timestamp", "asc")]),
        ("sort @timestamp", [], None, [("@timestamp", "desc")]),
        ("fields @timestamp | limit 42", ["@timestamp"], 42, []),
        ("limit 42 | fields @timestamp", ["@timestamp"], 42, []),
        ("fields @fld | sort @fld | limit 42", ["@fld"], 42, [("@fld", "desc")]),
        ("sort @fld asc | fields @fld | limit 42", ["@fld"], 42, [("@fld", "asc")]),
        ("limit 42 | sort @fld | fields @fld", ["@fld"], 42, [("@fld", "desc")]),
    ],
)
def test_query(query, fields, limit, sort):
    parsed = parse_query(query)
    assert parsed.fields == fields
    assert parsed.limit == limit
    assert parsed.sort == sort
