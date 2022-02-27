import sure  # noqa # pylint: disable=unused-import
import pytest

from moto import mock_dynamodb


def test_deprecation_warning():
    with pytest.warns(None) as record:
        mock_dynamodb()
    str(record[0].message).should.contain(
        "Module mock_dynamodb has been deprecated, and will be repurposed in a later release"
    )
