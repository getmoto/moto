import io
from urllib.parse import urlparse, parse_qs
import sure  # noqa # pylint: disable=unused-import
import requests
import pytest
import xmltodict

from flask.testing import FlaskClient
import moto.server as server
from moto.moto_server.threaded_moto_server import ThreadedMotoServer
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


@pytest.mark.parametrize("key_name", ["bar_baz", "bar+baz", "baz bar"])
def test_s3_server_bucket_create(key_name):
    test_client = authenticated_client()

    res = test_client.put("/", "http://foobaz.localhost:5000/")
    res.status_code.should.equal(200)

    res = test_client.get("/")
    res.data.should.contain(b"<Name>foobaz</Name>")

    res = test_client.get("/", "http://foobaz.localhost:5000/")
    res.status_code.should.equal(200)
    res.data.should.contain(b"ListBucketResult")

    res = test_client.put(
        f"/{key_name}", "http://foobaz.localhost:5000/", data="test value"
    )
    res.status_code.should.equal(200)
    assert "ETag" in dict(res.headers)

    # ListBuckets
    res = test_client.get(
        "/", "http://foobaz.localhost:5000/", query_string={"prefix": key_name}
    )
    res.status_code.should.equal(200)
    content = xmltodict.parse(res.data)["ListBucketResult"]["Contents"]
    # If we receive a dict, we only received one result
    # If content is of type list, our call returned multiple results - which is not correct
    content.should.be.a(dict)
    content["Key"].should.equal(key_name)

    # GetBucket
    res = test_client.head("http://foobaz.localhost:5000")
    assert res.status_code == 200
    assert res.headers.get("x-amz-bucket-region") == "us-east-1"

    # HeadObject
    res = test_client.head(f"/{key_name}", "http://foobaz.localhost:5000/")
    res.status_code.should.equal(200)
    assert res.headers.get("Accept-Ranges") == "bytes"

    # GetObject
    res = test_client.get(f"/{key_name}", "http://foobaz.localhost:5000/")
    res.status_code.should.equal(200)
    res.data.should.equal(b"test value")
    assert res.headers.get("Accept-Ranges") == "bytes"


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
    real_key = f"asdf/the-key/{filename}"
    res.status_code.should.equal(303)
    redirect = res.headers["location"]
    assert redirect.startswith(redirect_base)

    parts = urlparse(redirect)
    args = parse_qs(parts.query)
    assert args["key"][0] == real_key
    assert args["bucket"][0] == "tester"

    res = test_client.get(f"/{real_key}", "http://tester.localhost:5000/")
    res.status_code.should.equal(200)
    res.data.should.equal(filecontent.encode("utf8"))


def test_s3_server_post_without_content_length():
    test_client = authenticated_client()

    # You can create a bucket without specifying Content-Length
    res = test_client.put(
        "/", "http://tester.localhost:5000/", environ_overrides={"CONTENT_LENGTH": ""}
    )
    res.status_code.should.equal(200)

    # You can specify a bucket in another region without specifying Content-Length
    # (The body is just ignored..)
    res = test_client.put(
        "/",
        "http://tester.localhost:5000/",
        environ_overrides={"CONTENT_LENGTH": ""},
        data="<CreateBucketConfiguration><LocationConstraint>us-west-2</LocationConstraint></CreateBucketConfiguration>",
    )
    res.status_code.should.equal(200)

    # You cannot make any other bucket-related requests without specifying Content-Length
    for path in ["/?versioning", "/?policy"]:
        res = test_client.put(
            path, "http://t.localhost:5000", environ_overrides={"CONTENT_LENGTH": ""}
        )
        res.status_code.should.equal(411)

    # You cannot make any POST-request
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
    # github.com/getmoto/moto/issues/4220

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
    valid_origin = "https://example.org"
    preflight_headers = {
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "origin, x-requested-with",
        "Origin": valid_origin,
    }
    # Returns 403 on non existing bucket
    preflight_response = test_client.options(
        "/", "http://testcors.localhost:5000/", headers=preflight_headers
    )
    assert preflight_response.status_code == 403

    # Create the bucket & file
    test_client.put("/", "http://testcors.localhost:5000/")
    test_client.put("/test", "http://testcors.localhost:5000/")
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

    # Test GET key response
    # A regular GET should not receive any CORS headers
    resp = test_client.get("/test", "http://testcors.localhost:5000/")
    assert "Access-Control-Allow-Methods" not in resp.headers
    assert "Access-Control-Expose-Headers" not in resp.headers

    # A GET with mismatched Origin-header should not receive any CORS headers
    resp = test_client.get(
        "/test", "http://testcors.localhost:5000/", headers={"Origin": "something.com"}
    )
    assert "Access-Control-Allow-Methods" not in resp.headers
    assert "Access-Control-Expose-Headers" not in resp.headers

    # Only a GET with matching Origin-header should receive CORS headers
    resp = test_client.get(
        "/test", "http://testcors.localhost:5000/", headers={"Origin": valid_origin}
    )
    assert (
        resp.headers["Access-Control-Allow-Methods"] == "HEAD, GET, PUT, POST, DELETE"
    )
    assert resp.headers["Access-Control-Expose-Headers"] == "ETag"

    # Test PUT key response
    # A regular PUT should not receive any CORS headers
    resp = test_client.put("/test", "http://testcors.localhost:5000/")
    assert "Access-Control-Allow-Methods" not in resp.headers
    assert "Access-Control-Expose-Headers" not in resp.headers

    # A PUT with mismatched Origin-header should not receive any CORS headers
    resp = test_client.put(
        "/test", "http://testcors.localhost:5000/", headers={"Origin": "something.com"}
    )
    assert "Access-Control-Allow-Methods" not in resp.headers
    assert "Access-Control-Expose-Headers" not in resp.headers

    # Only a PUT with matching Origin-header should receive CORS headers
    resp = test_client.put(
        "/test", "http://testcors.localhost:5000/", headers={"Origin": valid_origin}
    )
    assert (
        resp.headers["Access-Control-Allow-Methods"] == "HEAD, GET, PUT, POST, DELETE"
    )
    assert resp.headers["Access-Control-Expose-Headers"] == "ETag"


def test_s3_server_post_cors_multiple_origins():
    """Test that Moto only responds with the Origin that we that hosts the server"""
    # github.com/getmoto/moto/issues/6003

    cors_config_payload = """<CORSConfiguration xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
  <CORSRule>
    <AllowedOrigin>https://example.org</AllowedOrigin>
    <AllowedOrigin>https://localhost:6789</AllowedOrigin>
    <AllowedMethod>POST</AllowedMethod>
  </CORSRule>
</CORSConfiguration>
    """

    thread = ThreadedMotoServer(port="6789", verbose=False)
    thread.start()

    # Create the bucket
    requests.put("http://testcors.localhost:6789/")
    requests.put("http://testcors.localhost:6789/?cors", data=cors_config_payload)

    # Test only our requested origin is returned
    preflight_response = requests.options(
        "http://testcors.localhost:6789/test2",
        headers={
            "Access-Control-Request-Method": "POST",
            "Origin": "https://localhost:6789",
        },
    )
    assert preflight_response.status_code == 200
    assert (
        preflight_response.headers["Access-Control-Allow-Origin"]
        == "https://localhost:6789"
    )
    assert preflight_response.content == b""

    # Verify a request with unknown origin fails
    preflight_response = requests.options(
        "http://testcors.localhost:6789/test2",
        headers={
            "Access-Control-Request-Method": "POST",
            "Origin": "https://unknown.host",
        },
    )
    assert preflight_response.status_code == 403
    assert b"<Code>AccessForbidden</Code>" in preflight_response.content

    # Verify we can use a wildcard anywhere in the origin
    cors_config_payload = """<CORSConfiguration xmlns="http://s3.amazonaws.com/doc/2006-03-01/"><CORSRule>
            <AllowedOrigin>https://*.google.com</AllowedOrigin>
            <AllowedMethod>POST</AllowedMethod>
          </CORSRule></CORSConfiguration>"""
    requests.put("http://testcors.localhost:6789/?cors", data=cors_config_payload)
    for origin in ["https://sth.google.com", "https://a.google.com"]:
        preflight_response = requests.options(
            "http://testcors.localhost:6789/test2",
            headers={"Access-Control-Request-Method": "POST", "Origin": origin},
        )
        assert preflight_response.status_code == 200
        assert preflight_response.headers["Access-Control-Allow-Origin"] == origin

    # Non-matching requests throw an error though - it does not act as a full wildcard
    preflight_response = requests.options(
        "http://testcors.localhost:6789/test2",
        headers={
            "Access-Control-Request-Method": "POST",
            "Origin": "sth.microsoft.com",
        },
    )
    assert preflight_response.status_code == 403
    assert b"<Code>AccessForbidden</Code>" in preflight_response.content

    # Verify we can use a wildcard as the origin
    cors_config_payload = """<CORSConfiguration xmlns="http://s3.amazonaws.com/doc/2006-03-01/"><CORSRule>
                <AllowedOrigin>*</AllowedOrigin>
                <AllowedMethod>POST</AllowedMethod>
              </CORSRule></CORSConfiguration>"""
    requests.put("http://testcors.localhost:6789/?cors", data=cors_config_payload)
    for origin in ["https://a.google.com", "http://b.microsoft.com", "any"]:
        preflight_response = requests.options(
            "http://testcors.localhost:6789/test2",
            headers={"Access-Control-Request-Method": "POST", "Origin": origin},
        )
        assert preflight_response.status_code == 200
        assert preflight_response.headers["Access-Control-Allow-Origin"] == origin

    thread.stop()
