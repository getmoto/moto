import sure  # noqa # pylint: disable=unused-import

from moto.ses.utils import is_valid_address


def test_is_valid_address():
    valid, msg = is_valid_address("test@example.com")
    valid.should.be.ok
    msg.should.be.none

    valid, msg = is_valid_address("test@")
    valid.should_not.be.ok
    msg.should.be.a(str)

    valid, msg = is_valid_address("test")
    valid.should_not.be.ok
    msg.should.be.a(str)
