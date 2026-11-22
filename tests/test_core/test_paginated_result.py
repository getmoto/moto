import pytest

from moto.core.responses import PaginatedResult


@pytest.mark.parametrize(
    "expression,expected",
    [
        ("NextToken", ("NextToken", None)),
        ("DistributionList.NextMarker", ("DistributionList.NextMarker", None)),
        ("StreamDescription.Shards[-1].ShardId", (None, "ShardId")),
        ("NextMarker || Contents[-1].Key", ("NextMarker", "Key")),
    ],
)
def test_parse_output_token(
    expression: str, expected: tuple[str | None, str | None]
) -> None:
    assert PaginatedResult._parse_output_token(expression) == expected


@pytest.mark.parametrize(
    "expression",
    [
        ["NextKeyMarker", "NextUploadIdMarker"],
        "Items[0].Id",
        "length(Items)",
    ],
)
def test_parse_output_token_unsupported(expression: object) -> None:
    with pytest.raises(NotImplementedError):
        PaginatedResult._parse_output_token(expression)
