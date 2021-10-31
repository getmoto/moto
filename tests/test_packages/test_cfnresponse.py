import pytest
import sure  # noqa # pylint: disable=unused-import

from moto.packages.cfnresponse import cfnresponse


@pytest.mark.parametrize(
    "url,expected_host,expected_port,expected_path",
    [
        ("localhost:5000/", "localhost", "5000", "/"),
        ("http://localhost:4567/", "http://localhost", "4567", "/"),
        ("https://localhost:4567/secure", "https://localhost", "4567", "/secure"),
        (
            "http://localhost:4567/someredonkulouslongpath",
            "http://localhost",
            "4567",
            "/someredonkulouslongpath",
        ),
    ],
)
def test_url_deconstruction(url, expected_host, expected_port, expected_path):
    host, port, path = cfnresponse.get_host_port_path(url)
    host.should.equal(expected_host)
    port.should.equal(expected_port)
    path.should.equal(expected_path)
