import pytest

from moto.dynamodb.models.dynamo_type import DynamoType, _number_size


class TestNumberSize:
    """
    DynamoDB's Number attribute size is documented at
    https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/CapacityUnitCalculations.html
    as "approximately (1 byte per two significant digits) + (1 byte)", with
    leading/trailing zeroes trimmed before counting significant digits.

    Regression coverage for a bug where `DynamoType.size()` used
    `len(str(value))` -- the length of the raw decimal string -- instead of
    this compact, significant-digit-based encoding. That overcounted the
    size of any Number attribute whose string form is longer than its
    significant-digit encoding (which is most numbers), making moto's 400KB
    item-size check stricter than real DynamoDB and rejecting items that
    DynamoDB itself would accept.
    """

    @pytest.mark.parametrize(
        "raw_value,expected_size",
        [
            # Worked examples from AWS's own documentation/blog writeups.
            ("27", 2),
            ("-27", 3),
            ("461", 3),
            ("0", 1),
            # A 10-significant-digit Unix timestamp: the old `len(str(value))`
            # behavior returned 10 here instead of the documented 6.
            ("1786461547", 6),
            # Leading/trailing zeroes are trimmed before counting digits.
            ("100", 2),
            ("00042", 2),
            ("0.5", 2),
            ("-0.010", 3),
            # 38 significant digits is DynamoDB's documented maximum.
            ("1" * 38, 20),
        ],
    )
    def test_number_size_matches_documented_formula(self, raw_value, expected_size):
        assert _number_size(raw_value) == expected_size

    def test_dynamo_type_number_uses_significant_digit_encoding(self):
        # Same timestamp as the reported bug: previously sized as 10 bytes
        # (len of the decimal string) instead of the correct 6.
        assert DynamoType({"N": "1786461547"}).size() == 6

    def test_dynamo_type_number_set_sums_member_sizes(self):
        number_set = DynamoType({"NS": ["27", "-27", "461"]})
        assert number_set.size() == 2 + 3 + 3
