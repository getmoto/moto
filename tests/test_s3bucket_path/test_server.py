import sure  # noqa # pylint: disable=unused-import

from flask.testing import FlaskClient
import moto.server as server

"""
Test the different server responses
"""


class AuthenticatedClient(FlaskClient):
    def open(self, *args, **kwargs):
        kwargs["headers"] = kwargs.get("headers", {})
        kwargs["headers"]["Authorization"] = "Any authorization header"
        kwargs["content_length"] = 0  # Fixes content-length complaints.
        return super().open(*args, **kwargs)


def authenticated_client():
    backend = server.create_backend_app("s3bucket_path")
    backend.test_client_class = AuthenticatedClient
    return backend.test_client()


def test_s3_server_get():
    test_client = authenticated_client()

    res = test_client.get("/")

    res.data.should.contain(b"ListAllMyBucketsResult")


def test_s3_server_bucket_create():
    test_client = authenticated_client()

    res = test_client.put("/foobar", "http://localhost:5000")
    res.status_code.should.equal(200)

    res = test_client.get("/")
    res.data.should.contain(b"<Name>foobar</Name>")

    res = test_client.get("/foobar", "http://localhost:5000")
    res.status_code.should.equal(200)
    res.data.should.contain(b"ListBucketResult")

    res = test_client.put("/foobar2/", "http://localhost:5000")
    res.status_code.should.equal(200)

    res = test_client.get("/")
    res.data.should.contain(b"<Name>foobar2</Name>")

    res = test_client.get("/foobar2/", "http://localhost:5000")
    res.status_code.should.equal(200)
    res.data.should.contain(b"ListBucketResult")

    res = test_client.get("/missing-bucket", "http://localhost:5000")
    res.status_code.should.equal(404)

    res = test_client.put("/foobar/bar", "http://localhost:5000", data="test value")
    res.status_code.should.equal(200)

    res = test_client.get("/foobar/bar", "http://localhost:5000")
    res.status_code.should.equal(200)
    res.data.should.equal(b"test value")


def test_s3_server_post_to_bucket():
    test_client = authenticated_client()

    res = test_client.put("/foobar2", "http://localhost:5000/")
    res.status_code.should.equal(200)

    test_client.post(
        "/foobar2",
        "https://localhost:5000/",
        data={"key": "the-key", "file": "nothing"},
    )

    res = test_client.get("/foobar2/the-key", "http://localhost:5000/")
    res.status_code.should.equal(200)
    res.data.should.equal(b"nothing")


def test_s3_server_put_ipv6():
    test_client = authenticated_client()

    res = test_client.put("/foobar2", "http://[::]:5000/")
    res.status_code.should.equal(200)

    test_client.post(
        "/foobar2", "https://[::]:5000/", data={"key": "the-key", "file": "nothing"}
    )

    res = test_client.get("/foobar2/the-key", "http://[::]:5000/")
    res.status_code.should.equal(200)
    res.data.should.equal(b"nothing")


def test_s3_server_put_ipv4():
    test_client = authenticated_client()

    res = test_client.put("/foobar2", "http://127.0.0.1:5000/")
    res.status_code.should.equal(200)

    test_client.post(
        "/foobar2",
        "https://127.0.0.1:5000/",
        data={"key": "the-key", "file": "nothing"},
    )

    res = test_client.get("/foobar2/the-key", "http://127.0.0.1:5000/")
    res.status_code.should.equal(200)
    res.data.should.equal(b"nothing")
