import os
from unittest.mock import patch

from moto import mock_aws

KEY = "AWS_ACCESS_KEY_ID"


def test_aws_keys_are_patched() -> None:
    with mock_aws():
        assert os.environ[KEY] == "FOOBARKEY"


def test_aws_keys_are_not_patched_when_user_configured() -> None:
    with patch.dict(os.environ, {"AWS_ACCESS_KEY_ID": "diff_value"}):
        # Sanity check
        assert os.environ["AWS_ACCESS_KEY_ID"] == "diff_value"

        # Moto will not mock the credentials, and we see the 'original' value
        with mock_aws(config={"core": {"mock_credentials": False}}):
            assert os.environ[KEY] == "diff_value"

            # Nested mocks are possible
            # For the duration of the inner mock, Moto will patch the credentials
            with mock_aws(config={"core": {"mock_credentials": True}}):
                assert os.environ[KEY] == "FOOBARKEY"

            # The moment the inner patch ends, we're back to the 'original' value
            assert os.environ[KEY] == "diff_value"


def test_aws_keys_can_be_none() -> None:
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
        with mock_aws():
            assert os.environ[KEY] == "FOOBARKEY"
        # Verify that the os.environ[KEY] is unpatched, and reverts to None
        assert os.environ.get(KEY) is None
    finally:
        # Reset the value original - don't want to change the users system
        os.environ[KEY] = original
