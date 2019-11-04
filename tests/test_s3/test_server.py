# coding=utf-8

from __future__ import unicode_literals
import sure  # noqa

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
        return super(AuthenticatedClient, self).open(*args, **kwargs)


def authenticated_client():
    backend = server.create_backend_app("s3")
    backend.test_client_class = AuthenticatedClient
    return backend.test_client()


def test_s3_server_get():
    test_client = authenticated_client()
    res = test_client.get("/")

    res.data.should.contain(b"ListAllMyBucketsResult")


def test_s3_server_bucket_create():
    test_client = authenticated_client()

    res = test_client.put("/", "http://foobaz.localhost:5000/")
    res.status_code.should.equal(200)

    res = test_client.get("/")
    res.data.should.contain(b"<Name>foobaz</Name>")

    res = test_client.get("/", "http://foobaz.localhost:5000/")
    res.status_code.should.equal(200)
    res.data.should.contain(b"ListBucketResult")

    res = test_client.put("/bar", "http://foobaz.localhost:5000/", data="test value")
    res.status_code.should.equal(200)
    assert "ETag" in dict(res.headers)

    res = test_client.get("/bar", "http://foobaz.localhost:5000/")
    res.status_code.should.equal(200)
    res.data.should.equal(b"test value")


def test_s3_server_bucket_versioning():
    test_client = authenticated_client()

    # Just enough XML to enable versioning
    body = "<Status>Enabled</Status>"
    res = test_client.put("/?versioning", "http://foobaz.localhost:5000", data=body)
    res.status_code.should.equal(200)


def test_s3_server_post_to_bucket():
    test_client = authenticated_client()

    res = test_client.put("/", "http://tester.localhost:5000/")
    res.status_code.should.equal(200)

    test_client.post(
        "/",
        "https://tester.localhost:5000/",
        data={"key": "the-key", "file": "nothing"},
    )

    res = test_client.get("/the-key", "http://tester.localhost:5000/")
    res.status_code.should.equal(200)
    res.data.should.equal(b"nothing")


def test_s3_server_post_without_content_length():
    test_client = authenticated_client()

    res = test_client.put(
        "/", "http://tester.localhost:5000/", environ_overrides={"CONTENT_LENGTH": ""}
    )
    res.status_code.should.equal(411)

    res = test_client.post(
        "/", "https://tester.localhost:5000/", environ_overrides={"CONTENT_LENGTH": ""}
    )
    res.status_code.should.equal(411)


def test_s3_server_post_unicode_bucket_key():
    # Make sure that we can deal with non-ascii characters in request URLs (e.g., S3 object names)
    dispatcher = server.DomainDispatcherApplication(server.create_backend_app)
    backend_app = dispatcher.get_application(
        {"HTTP_HOST": "s3.amazonaws.com", "PATH_INFO": "/test-bucket/test-object-てすと"}
    )
    assert backend_app
    backend_app = dispatcher.get_application(
        {
            "HTTP_HOST": "s3.amazonaws.com",
            "PATH_INFO": "/test-bucket/test-object-てすと".encode("utf-8"),
        }
    )
    assert backend_app
