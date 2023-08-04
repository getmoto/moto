"""Test the different server responses."""
from flask.testing import FlaskClient
import moto.server as server


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

    assert b"ListAllMyBucketsResult" in res.data


def test_s3_server_bucket_create():
    test_client = authenticated_client()

    res = test_client.put("/foobar", "http://localhost:5000")
    assert res.status_code == 200

    res = test_client.get("/")
    assert b"<Name>foobar</Name>" in res.data

    res = test_client.get("/foobar", "http://localhost:5000")
    assert res.status_code == 200
    assert b"ListBucketResult" in res.data

    res = test_client.put("/foobar2/", "http://localhost:5000")
    assert res.status_code == 200

    res = test_client.get("/")
    assert b"<Name>foobar2</Name>" in res.data

    res = test_client.get("/foobar2/", "http://localhost:5000")
    assert res.status_code == 200
    assert b"ListBucketResult" in res.data

    res = test_client.get("/missing-bucket", "http://localhost:5000")
    assert res.status_code == 404

    res = test_client.put("/foobar/bar", "http://localhost:5000", data="test value")
    assert res.status_code == 200

    res = test_client.get("/foobar/bar", "http://localhost:5000")
    assert res.status_code == 200
    assert res.data == b"test value"


def test_s3_server_post_to_bucket():
    test_client = authenticated_client()

    res = test_client.put("/foobar2", "http://localhost:5000/")
    assert res.status_code == 200

    test_client.post(
        "/foobar2",
        "https://localhost:5000/",
        data={"key": "the-key", "file": "nothing"},
    )

    res = test_client.get("/foobar2/the-key", "http://localhost:5000/")
    assert res.status_code == 200
    assert res.data == b"nothing"


def test_s3_server_put_ipv6():
    test_client = authenticated_client()

    res = test_client.put("/foobar2", "http://[::]:5000/")
    assert res.status_code == 200

    test_client.post(
        "/foobar2", "https://[::]:5000/", data={"key": "the-key", "file": "nothing"}
    )

    res = test_client.get("/foobar2/the-key", "http://[::]:5000/")
    assert res.status_code == 200
    assert res.data == b"nothing"


def test_s3_server_put_ipv4():
    test_client = authenticated_client()

    res = test_client.put("/foobar2", "http://127.0.0.1:5000/")
    assert res.status_code == 200

    test_client.post(
        "/foobar2",
        "https://127.0.0.1:5000/",
        data={"key": "the-key", "file": "nothing"},
    )

    res = test_client.get("/foobar2/the-key", "http://127.0.0.1:5000/")
    assert res.status_code == 200
    assert res.data == b"nothing"
