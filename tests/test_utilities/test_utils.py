import re

from moto.utilities.utils import ARN_PARTITION_REGEX, get_partition


def test_get_partition():
    assert get_partition(None) == "aws"
    assert get_partition("unknown") == "aws"
    assert get_partition("cn-north-1") == "aws-cn"


def test_partition_regex():
    assert re.match(ARN_PARTITION_REGEX, "arn:aws:someservice")
    assert re.match(ARN_PARTITION_REGEX, "arn:aws-cn:someservice")
    assert not re.match(ARN_PARTITION_REGEX, "arn:partition:someservice")
    assert not re.match(ARN_PARTITION_REGEX, "someservice")
