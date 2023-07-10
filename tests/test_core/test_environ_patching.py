import os
from moto import mock_ec2, mock_s3

KEY = "AWS_ACCESS_KEY_ID"


def test_aws_keys_are_patched():
    with mock_ec2():
        patched_value = os.environ[KEY]
        assert patched_value == "foobar_key"


def test_aws_keys_can_be_none():
    """
    Verify that the os.environ[KEY] can be None
    Patching the None-value shouldn't be an issue
    """
    original = os.environ.get(KEY, "value-set-by-user")
    # Delete the original value by the user
    try:
        del os.environ[KEY]
    except KeyError:
        pass  # Value might not be set on this system in the first place
    try:
        # Verify that the os.environ[KEY] is patched
        with mock_s3():
            patched_value = os.environ[KEY]
            assert patched_value == "foobar_key"
        # Verify that the os.environ[KEY] is unpatched, and reverts to None
        assert os.environ.get(KEY) is None
    finally:
        # Reset the value original - don't want to change the users system
        os.environ[KEY] = original
