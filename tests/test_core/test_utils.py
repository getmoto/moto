import pytest
from freezegun import freeze_time

from moto.core.utils import (
    camelcase_to_underscores,
    underscores_to_camelcase,
    unix_time,
    camelcase_to_pascal,
    pascal_to_camelcase,
    _unquote_hex_characters,
)


@pytest.mark.parametrize(
    "_input,expected",
    [
        ("theNewAttribute", "the_new_attribute"),
        ("attri bute With Space", "attribute_with_space"),
        ("FirstLetterCapital", "first_letter_capital"),
        ("ListMFADevices", "list_mfa_devices"),
    ],
)
def test_camelcase_to_underscores(_input, expected):
    assert camelcase_to_underscores(_input) == expected


@pytest.mark.parametrize(
    "_input,expected",
    [("the_new_attribute", "theNewAttribute"), ("attribute", "attribute")],
)
def test_underscores_to_camelcase(_input, expected):
    assert underscores_to_camelcase(_input) == expected


@pytest.mark.parametrize(
    "_input,expected",
    [("TheNewAttribute", "theNewAttribute"), ("Attribute", "attribute")],
)
def test_pascal_to_camelcase(_input, expected):
    assert pascal_to_camelcase(_input) == expected


@pytest.mark.parametrize(
    "_input,expected",
    [("theNewAttribute", "TheNewAttribute"), ("attribute", "Attribute")],
)
def test_camelcase_to_pascal(_input, expected):
    assert camelcase_to_pascal(_input) == expected


@freeze_time("2015-01-01 12:00:00")
def test_unix_time():
    assert unix_time() == 1420113600.0


@pytest.mark.parametrize(
    "original_url,result",
    [
        ("some%3Fkey", "some?key"),
        ("6T7\x159\x12\r\x08.txt", "6T7\x159\x12\r\x08.txt"),
        ("foobar/the-unicode-%E2%98%BA-key", "foobar/the-unicode-☺-key"),
        ("key-with%2Eembedded%2Eurl%2Eencoding", "key-with.embedded.url.encoding"),
        # Can represent a single character
        ("%E2%82%AC", "€"),
        ("%2E", "."),
        # Multiple chars in a row
        ("%E2%82%AC%E2%82%AC", "€€"),
        ("%2E%2E", ".."),
    ],
)
def test_quote_characters(original_url, result):
    assert _unquote_hex_characters(original_url) == result


@pytest.mark.parametrize("original_path", ["%2F%2F", "s%2Fs%2Fs%2F"])
def test_quote_characters__with_slashes(original_path):
    # If the string contains slashes, we ignore them
    # Werkzeug already takes care of those for us
    assert _unquote_hex_characters(original_path) == original_path
