import sure  # noqa # pylint: disable=unused-import

from moto.ses.utils import is_valid_address


def test_is_valid_address():
    valid, msg = is_valid_address("test@example.com")
    valid.should.equal(True)
    msg.should.equal(None)

    valid, msg = is_valid_address("test@")
    valid.should.equal(False)
    msg.should.be.a(str)

    valid, msg = is_valid_address("test")
    valid.should.equal(False)
    msg.should.be.a(str)
