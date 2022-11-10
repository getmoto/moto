import io
from urllib.parse import urlparse, parse_qs
import sure  # noqa # pylint: disable=unused-import

from flask.testing import FlaskClient
import moto.server as server
from unittest.mock import patch

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

    for key_name in ("bar_baz", "bar+baz"):
        res = test_client.put(
            f"/{key_name}", "http://foobaz.localhost:5000/", data="test value"
        )
        res.status_code.should.equal(200)
        assert "ETag" in dict(res.headers)

        res = test_client.get(
            "/", "http://foobaz.localhost:5000/", query_string={"prefix": key_name}
        )
        res.status_code.should.equal(200)
        res.data.should.contain(b"Contents")

        res = test_client.get(f"/{key_name}", "http://foobaz.localhost:5000/")
        res.status_code.should.equal(200)
        res.data.should.equal(b"test value")


def test_s3_server_ignore_subdomain_for_bucketnames():
    with patch("moto.settings.S3_IGNORE_SUBDOMAIN_BUCKETNAME", True):
        test_client = authenticated_client()

        res = test_client.put("/mybucket", "http://foobaz.localhost:5000/")
        res.status_code.should.equal(200)
        res.data.should.contain(b"mybucket")


def test_s3_server_bucket_versioning():
    test_client = authenticated_client()

    res = test_client.put("/", "http://foobaz.localhost:5000/")
    res.status_code.should.equal(200)

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


def test_s3_server_post_to_bucket_redirect():
    test_client = authenticated_client()

    res = test_client.put("/", "http://tester.localhost:5000/")
    res.status_code.should.equal(200)

    redirect_base = "https://redirect.com/success/"
    filecontent = "nothing"
    filename = "test_filename.txt"
    res = test_client.post(
        "/",
        "https://tester.localhost:5000/",
        data={
            "key": "asdf/the-key/${filename}",
            "file": (io.BytesIO(filecontent.encode("utf8")), filename),
            "success_action_redirect": redirect_base,
        },
    )
    real_key = "asdf/the-key/{}".format(filename)
    res.status_code.should.equal(303)
    redirect = res.headers["location"]
    assert redirect.startswith(redirect_base)

    parts = urlparse(redirect)
    args = parse_qs(parts.query)
    assert args["key"][0] == real_key
    assert args["bucket"][0] == "tester"

    res = test_client.get("/{}".format(real_key), "http://tester.localhost:5000/")
    res.status_code.should.equal(200)
    res.data.should.equal(filecontent.encode("utf8"))


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


def test_s3_server_post_cors():
    """Test default CORS headers set by flask-cors plugin"""
    test_client = authenticated_client()
    # Create the bucket
    test_client.put("/", "http://tester.localhost:5000/")

    preflight_headers = {
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "origin, x-requested-with",
        "Origin": "https://localhost:9000",
    }

    res = test_client.options(
        "/", "http://tester.localhost:5000/", headers=preflight_headers
    )
    assert res.status_code in [200, 204]

    expected_methods = set(["DELETE", "PATCH", "PUT", "GET", "HEAD", "POST", "OPTIONS"])
    assert (
        set(res.headers["Access-Control-Allow-Methods"].split(", ")) == expected_methods
    )

    res.headers.should.have.key("Access-Control-Allow-Origin").which.should.equal(
        "https://localhost:9000"
    )
    res.headers.should.have.key("Access-Control-Allow-Headers").which.should.equal(
        "origin, x-requested-with"
    )


def test_s3_server_post_cors_exposed_header():
    """Test that we can override default CORS headers with custom bucket rules"""
    # github.com/spulec/moto/issues/4220

    cors_config_payload = """<CORSConfiguration xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
  <CORSRule>
    <AllowedOrigin>https://example.org</AllowedOrigin>
    <AllowedMethod>HEAD</AllowedMethod>
    <AllowedMethod>GET</AllowedMethod>
    <AllowedMethod>PUT</AllowedMethod>
    <AllowedMethod>POST</AllowedMethod>
    <AllowedMethod>DELETE</AllowedMethod>
    <AllowedHeader>*</AllowedHeader>
    <ExposeHeader>ETag</ExposeHeader>
    <MaxAgeSeconds>3000</MaxAgeSeconds>
  </CORSRule>
</CORSConfiguration>
    """

    test_client = authenticated_client()
    preflight_headers = {
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "origin, x-requested-with",
        "Origin": "https://localhost:9000",
    }
    # Returns 403 on non existing bucket
    preflight_response = test_client.options(
        "/", "http://testcors.localhost:5000/", headers=preflight_headers
    )
    assert preflight_response.status_code == 403

    # Create the bucket
    test_client.put("/", "http://testcors.localhost:5000/")
    res = test_client.put(
        "/?cors", "http://testcors.localhost:5000", data=cors_config_payload
    )
    assert res.status_code == 200

    cors_res = test_client.get("/?cors", "http://testcors.localhost:5000")
    assert b"<ExposedHeader>ETag</ExposedHeader>" in cors_res.data

    # Test OPTIONS bucket response and key response
    for key_name in ("/", "/test"):
        preflight_response = test_client.options(
            key_name, "http://testcors.localhost:5000/", headers=preflight_headers
        )
        assert preflight_response.status_code == 200
        expected_cors_headers = {
            "Access-Control-Allow-Methods": "HEAD, GET, PUT, POST, DELETE",
            "Access-Control-Allow-Origin": "https://example.org",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Expose-Headers": "ETag",
            "Access-Control-Max-Age": "3000",
        }
        for header_name, header_value in expected_cors_headers.items():
            assert header_name in preflight_response.headers
            assert preflight_response.headers[header_name] == header_value
