from moto.ses.utils import is_valid_address


def test_is_valid_address():
    msg = is_valid_address("test@example.com")
    assert msg is None

    msg = is_valid_address("test@")
    assert isinstance(msg, str)

    msg = is_valid_address("test")
    assert isinstance(msg, str)
