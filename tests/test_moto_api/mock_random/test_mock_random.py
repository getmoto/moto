from moto.moto_api._internal import mock_random


def test_semi_random_uuids():
    # Create random UUID first
    random_uuid = str(mock_random.uuid4())

    # Seed our generator - the next generation should be predetermined
    mock_random.seed(42)
    fixed_uuid = str(mock_random.uuid4())
    assert fixed_uuid == "bdd640fb-0667-4ad1-9c80-317fa3b1799d"

    # Ensure they are different
    assert fixed_uuid != random_uuid

    # Retrieving another 'fixed' UUID should not return a known UUID
    second_fixed = str(mock_random.uuid4())
    assert second_fixed != random_uuid
    assert second_fixed != fixed_uuid


def test_semi_random_hex_strings():
    # Create random HEX first
    random_hex = mock_random.get_random_hex()

    # Seed our generator - the next generation should be predetermined
    mock_random.seed(42)
    fixed_hex = mock_random.get_random_hex()
    assert fixed_hex == "30877432"

    # Ensure they are different
    assert fixed_hex != random_hex

    # Retrieving another 'fixed' UUID should not return a known UUID
    second_hex = mock_random.uuid4()
    assert second_hex != random_hex
    assert second_hex != fixed_hex
