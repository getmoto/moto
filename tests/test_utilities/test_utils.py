import hashlib
import re

import pytest

from moto.utilities.utils import ARN_PARTITION_REGEX, get_partition, md5_hash


def test_get_partition():
    assert get_partition(None) == "aws"
    assert get_partition("unknown") == "aws"
    assert get_partition("cn-north-1") == "aws-cn"


def test_md5_hash_when_md5_is_refused(monkeypatch):
    def unsupported(*args, **kwargs):
        raise ValueError("[digital envelope routines] unsupported")

    monkeypatch.setattr(hashlib, "md5", unsupported)
    assert md5_hash(b"data").hexdigest() == "8d777f385d3dfec8815d20f7496026dc"


def test_md5_hash_when_md5_is_absent(monkeypatch):
    monkeypatch.delattr(hashlib, "md5", raising=False)
    assert md5_hash(b"data").hexdigest() == "8d777f385d3dfec8815d20f7496026dc"


def test_md5_hash_unavailable(monkeypatch):
    def unsupported(*args, **kwargs):
        raise ValueError("[digital envelope routines] unsupported")

    monkeypatch.setattr(hashlib, "md5", unsupported)
    monkeypatch.setattr(hashlib, "new", unsupported)
    with pytest.raises(RuntimeError, match="MD5 hash, which is not available"):
        md5_hash(b"data")


def test_partition_regex():
    assert re.match(ARN_PARTITION_REGEX, "arn:aws:someservice")
    assert re.match(ARN_PARTITION_REGEX, "arn:aws-cn:someservice")
    assert not re.match(ARN_PARTITION_REGEX, "arn:partition:someservice")
    assert not re.match(ARN_PARTITION_REGEX, "someservice")
