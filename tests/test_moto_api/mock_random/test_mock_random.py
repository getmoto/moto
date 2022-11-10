import sure  # noqa # pylint: disable=unused-import
from moto.moto_api._internal import mock_random


def test_semi_random_uuids():
    # Create random UUID first
    random_uuid = str(mock_random.uuid4())

    # Seed our generator - the next generation should be predetermined
    mock_random.seed(42)
    fixed_uuid = str(mock_random.uuid4())
    fixed_uuid.should.equal("bdd640fb-0667-4ad1-9c80-317fa3b1799d")

    # Ensure they are different
    fixed_uuid.shouldnt.equal(random_uuid)

    # Retrieving another 'fixed' UUID should not return a known UUID
    second_fixed = str(mock_random.uuid4())
    second_fixed.shouldnt.equal(random_uuid)
    second_fixed.shouldnt.equal(fixed_uuid)


def test_semi_random_hex_strings():
    # Create random HEX first
    random_hex = mock_random.get_random_hex()

    # Seed our generator - the next generation should be predetermined
    mock_random.seed(42)
    fixed_hex = mock_random.get_random_hex()
    fixed_hex.should.equal("30877432")

    # Ensure they are different
    fixed_hex.shouldnt.equal(random_hex)

    # Retrieving another 'fixed' UUID should not return a known UUID
    second_hex = mock_random.uuid4()
    second_hex.shouldnt.equal(random_hex)
    second_hex.shouldnt.equal(fixed_hex)
