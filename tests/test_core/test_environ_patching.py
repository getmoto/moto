import io
import os
import unittest
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


ORIGINAL_CREDS = {
    "AWS_ACCESS_KEY_ID": "original-key",
    "AWS_SECRET_ACCESS_KEY": "original-secret",
}


def test_aws_keys_are_restored_when_the_same_mock_is_started_twice() -> None:
    with patch.dict(os.environ, ORIGINAL_CREDS):
        mock = mock_aws()
        mock.start()
        mock.start()
        assert os.environ[KEY] == "FOOBARKEY"

        mock.stop()
        assert os.environ[KEY] == "FOOBARKEY"

        mock.stop()
        assert os.environ[KEY] == "original-key"
        assert os.environ["AWS_SECRET_ACCESS_KEY"] == "original-secret"


def test_aws_keys_are_restored_when_a_decorated_class_calls_its_own_methods() -> None:
    @mock_aws
    class TestWithHelper(unittest.TestCase):
        def helper(self) -> str:
            return os.environ[KEY]

        def test_calls_helper(self) -> None:
            assert self.helper() == "FOOBARKEY"

    with patch.dict(os.environ, ORIGINAL_CREDS):
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestWithHelper)
        result = unittest.TextTestRunner(stream=io.StringIO()).run(suite)
        assert result.wasSuccessful()

        assert os.environ[KEY] == "original-key"
        assert os.environ["AWS_SECRET_ACCESS_KEY"] == "original-secret"


def test_aws_keys_are_restored_when_mocks_stop_in_a_different_order() -> None:
    with patch.dict(os.environ, ORIGINAL_CREDS):
        first = mock_aws()
        second = mock_aws()
        first.start()
        second.start()

        first.stop()
        assert os.environ[KEY] == "FOOBARKEY"

        second.stop()
        assert os.environ[KEY] == "original-key"
        assert os.environ["AWS_SECRET_ACCESS_KEY"] == "original-secret"


def test_nested_mock_does_not_mock_the_aws_keys_again() -> None:
    with patch.dict(os.environ, ORIGINAL_CREDS):
        with mock_aws():
            os.environ[KEY] = "set-by-user"
            with mock_aws():
                assert os.environ[KEY] == "set-by-user"
            assert os.environ[KEY] == "set-by-user"
        assert os.environ[KEY] == "original-key"
        assert os.environ["AWS_SECRET_ACCESS_KEY"] == "original-secret"


def test_aws_keys_are_restored_when_the_inner_mock_does_not_patch_credentials() -> None:
    with patch.dict(os.environ, ORIGINAL_CREDS):
        outer = mock_aws()
        inner = mock_aws(config={"core": {"mock_credentials": False}})
        outer.start()
        inner.start()

        inner.stop()
        assert os.environ[KEY] == "FOOBARKEY"

        outer.stop()
        assert os.environ[KEY] == "original-key"
        assert os.environ["AWS_SECRET_ACCESS_KEY"] == "original-secret"
