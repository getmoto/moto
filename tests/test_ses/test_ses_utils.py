import sure  # noqa # pylint: disable=unused-import

from moto.ses.utils import is_valid_address


def test_is_valid_address():
    msg = is_valid_address("test@example.com")
    msg.should.equal(None)

    msg = is_valid_address("test@")
    msg.should.be.a(str)

    msg = is_valid_address("test")
    msg.should.be.a(str)
