import os
from uuid import uuid4

import boto3
import pytest
import requests

from botocore.exceptions import ClientError
from botocore.handlers import disable_signing
from moto import mock_s3, settings
from .test_s3 import add_proxy_details

DEFAULT_REGION_NAME = "us-east-1"


@pytest.mark.parametrize(
    "type_key", [("CanonicalUser", "id", "ID"), ("Group", "url", "URI")]
)
@pytest.mark.parametrize(
    "value", ["AllUsers", "http://acs.amazonaws.com/groups/global/AllUsers"]
)
@pytest.mark.parametrize("has_quotes", [True, False])
@pytest.mark.parametrize("readwrite", ["Read", "Write"])
@mock_s3
def test_put_object_acl_using_grant(readwrite, type_key, value, has_quotes):
    s3_resource = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = str(uuid4())
    bucket = s3_resource.Bucket(bucket_name)
    bucket.create()
    keyname = "test.txt"

    bucket.put_object(Key=keyname, Body=b"asdf")
    _type, key, response_key = type_key
    header_value = f'"{value}"' if has_quotes else value
    args = {
        "Bucket": bucket_name,
        "Key": keyname,
        f"Grant{readwrite}": f"{key}={header_value}",
    }
    client.put_object_acl(**args)

    grants = client.get_object_acl(Bucket=bucket_name, Key=keyname)["Grants"]
    assert len(grants) == 1
    assert grants[0]["Grantee"] == {"Type": _type, response_key: value}
    assert grants[0]["Permission"] == readwrite.upper()


@mock_s3
def test_acl_switching_boto3():
    s3_resource = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket = s3_resource.Bucket("foobar")
    bucket.create()
    keyname = "test.txt"

    bucket.put_object(Key=keyname, Body=b"asdf", ACL="public-read")
    client.put_object_acl(ACL="private", Bucket="foobar", Key=keyname)

    grants = client.get_object_acl(Bucket="foobar", Key=keyname)["Grants"]
    assert {
        "Grantee": {
            "Type": "Group",
            "URI": "http://acs.amazonaws.com/groups/global/AllUsers",
        },
        "Permission": "READ",
    } not in grants


@mock_s3
def test_acl_switching_nonexistent_key():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket="mybucket")

    with pytest.raises(ClientError) as exc:
        s3_client.put_object_acl(Bucket="mybucket", Key="nonexistent", ACL="private")

    assert exc.value.response["Error"]["Code"] == "NoSuchKey"


@mock_s3
def test_s3_object_in_public_bucket():
    s3_resource = boto3.resource("s3")
    bucket = s3_resource.Bucket("test-bucket")
    bucket.create(
        ACL="public-read", CreateBucketConfiguration={"LocationConstraint": "us-west-1"}
    )
    bucket.put_object(Body=b"ABCD", Key="file.txt")

    s3_anonymous = boto3.resource("s3")
    s3_anonymous.meta.client.meta.events.register("choose-signer.s3.*", disable_signing)

    contents = (
        s3_anonymous.Object(key="file.txt", bucket_name="test-bucket")
        .get()["Body"]
        .read()
    )
    assert contents == b"ABCD"

    bucket.put_object(ACL="private", Body=b"ABCD", Key="file.txt")

    with pytest.raises(ClientError) as exc:
        s3_anonymous.Object(key="file.txt", bucket_name="test-bucket").get()
    assert exc.value.response["Error"]["Code"] == "403"


@mock_s3
def test_s3_object_in_public_bucket_using_multiple_presigned_urls():
    s3_resource = boto3.resource("s3")
    bucket = s3_resource.Bucket("test-bucket")
    bucket.create(
        ACL="public-read", CreateBucketConfiguration={"LocationConstraint": "us-west-1"}
    )
    bucket.put_object(Body=b"ABCD", Key="file.txt")

    params = {"Bucket": "test-bucket", "Key": "file.txt"}
    presigned_url = boto3.client("s3").generate_presigned_url(
        "get_object", params, ExpiresIn=900
    )
    kwargs = {}
    if settings.test_proxy_mode():
        add_proxy_details(kwargs)
    for i in range(1, 10):
        response = requests.get(presigned_url, **kwargs)
        assert response.status_code == 200, f"Failed on req number {i}"


@mock_s3
def test_s3_object_in_private_bucket():
    s3_resource = boto3.resource("s3")
    bucket = s3_resource.Bucket("test-bucket")
    bucket.create(
        ACL="private", CreateBucketConfiguration={"LocationConstraint": "us-west-1"}
    )
    bucket.put_object(ACL="private", Body=b"ABCD", Key="file.txt")

    s3_anonymous = boto3.resource("s3")
    s3_anonymous.meta.client.meta.events.register("choose-signer.s3.*", disable_signing)

    with pytest.raises(ClientError) as exc:
        s3_anonymous.Object(key="file.txt", bucket_name="test-bucket").get()
    assert exc.value.response["Error"]["Code"] == "403"

    bucket.put_object(ACL="public-read", Body=b"ABCD", Key="file.txt")
    contents = (
        s3_anonymous.Object(key="file.txt", bucket_name="test-bucket")
        .get()["Body"]
        .read()
    )
    assert contents == b"ABCD"


@mock_s3
def test_put_bucket_acl_body():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket="bucket")
    bucket_owner = s3_client.get_bucket_acl(Bucket="bucket")["Owner"]
    s3_client.put_bucket_acl(
        Bucket="bucket",
        AccessControlPolicy={
            "Grants": [
                {
                    "Grantee": {
                        "URI": "http://acs.amazonaws.com/groups/s3/LogDelivery",
                        "Type": "Group",
                    },
                    "Permission": "WRITE",
                },
                {
                    "Grantee": {
                        "URI": "http://acs.amazonaws.com/groups/s3/LogDelivery",
                        "Type": "Group",
                    },
                    "Permission": "READ_ACP",
                },
            ],
            "Owner": bucket_owner,
        },
    )

    result = s3_client.get_bucket_acl(Bucket="bucket")
    assert len(result["Grants"]) == 2
    for grant in result["Grants"]:
        assert (
            grant["Grantee"]["URI"] == "http://acs.amazonaws.com/groups/s3/LogDelivery"
        )
        assert grant["Grantee"]["Type"] == "Group"
        assert grant["Permission"] in ["WRITE", "READ_ACP"]

    # With one:
    s3_client.put_bucket_acl(
        Bucket="bucket",
        AccessControlPolicy={
            "Grants": [
                {
                    "Grantee": {
                        "URI": "http://acs.amazonaws.com/groups/s3/LogDelivery",
                        "Type": "Group",
                    },
                    "Permission": "WRITE",
                }
            ],
            "Owner": bucket_owner,
        },
    )
    result = s3_client.get_bucket_acl(Bucket="bucket")
    assert len(result["Grants"]) == 1

    # With no owner:
    with pytest.raises(ClientError) as err:
        s3_client.put_bucket_acl(
            Bucket="bucket",
            AccessControlPolicy={
                "Grants": [
                    {
                        "Grantee": {
                            "URI": "http://acs.amazonaws.com/groups/s3/LogDelivery",
                            "Type": "Group",
                        },
                        "Permission": "WRITE",
                    }
                ]
            },
        )
    assert err.value.response["Error"]["Code"] == "MalformedACLError"

    # With incorrect permission:
    with pytest.raises(ClientError) as err:
        s3_client.put_bucket_acl(
            Bucket="bucket",
            AccessControlPolicy={
                "Grants": [
                    {
                        "Grantee": {
                            "URI": "http://acs.amazonaws.com/groups/s3/LogDelivery",
                            "Type": "Group",
                        },
                        "Permission": "lskjflkasdjflkdsjfalisdjflkdsjf",
                    }
                ],
                "Owner": bucket_owner,
            },
        )
    assert err.value.response["Error"]["Code"] == "MalformedACLError"

    # Clear the ACLs:
    result = s3_client.put_bucket_acl(
        Bucket="bucket", AccessControlPolicy={"Grants": [], "Owner": bucket_owner}
    )
    assert not result.get("Grants")


@mock_s3
def test_object_acl_with_presigned_post():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)

    bucket_name = "imageS3Bucket"
    object_name = "text.txt"
    fields = {"acl": "public-read"}
    file = open("text.txt", "w", encoding="utf-8")
    file.write("test")
    file.close()

    s3_client.create_bucket(Bucket=bucket_name)
    response = s3_client.generate_presigned_post(
        bucket_name, object_name, Fields=fields, ExpiresIn=60000
    )

    with open(object_name, "rb") as fhandle:
        kwargs = {"files": {"file": (object_name, fhandle)}}
        if settings.test_proxy_mode():
            add_proxy_details(kwargs)
        requests.post(response["url"], data=response["fields"], **kwargs)

    response = s3_client.get_object_acl(Bucket=bucket_name, Key=object_name)

    assert "Grants" in response
    assert len(response["Grants"]) == 2
    assert response["Grants"][1]["Permission"] == "READ"

    response = s3_client.get_object(Bucket=bucket_name, Key=object_name)

    assert "ETag" in response
    assert "Body" in response
    os.remove("text.txt")


@mock_s3
def test_acl_setting_boto3():
    s3_resource = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket = s3_resource.Bucket("foobar")
    bucket.create()

    content = b"imafile"
    keyname = "test.txt"
    bucket.put_object(
        Key=keyname, Body=content, ContentType="text/plain", ACL="public-read"
    )

    grants = client.get_object_acl(Bucket="foobar", Key=keyname)["Grants"]
    assert {
        "Grantee": {
            "Type": "Group",
            "URI": "http://acs.amazonaws.com/groups/global/AllUsers",
        },
        "Permission": "READ",
    } in grants


@mock_s3
def test_acl_setting_via_headers_boto3():
    s3_resource = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket = s3_resource.Bucket("foobar")
    bucket.create()

    keyname = "test.txt"

    bucket.put_object(Key=keyname, Body=b"imafile")
    client.put_object_acl(ACL="public-read", Bucket="foobar", Key=keyname)

    grants = client.get_object_acl(Bucket="foobar", Key=keyname)["Grants"]
    assert {
        "Grantee": {
            "Type": "Group",
            "URI": "http://acs.amazonaws.com/groups/global/AllUsers",
        },
        "Permission": "READ",
    } in grants


@mock_s3
def test_raise_exception_for_grant_and_acl():
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_resource = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "bucketname"
    client.create_bucket(Bucket=bucket_name)
    bucket = s3_resource.Bucket(bucket_name)
    acl = client.get_bucket_acl(Bucket=bucket_name)
    acl_grantee_id = acl["Owner"]["ID"]

    # This should raise an exception or provide some error message,
    # but runs without exception instead.
    with pytest.raises(ClientError) as exc:
        bucket.put_object(
            ACL="bucket-owner-full-control",
            Body="example-file-path",
            Key="example-key",
            ContentType="text/plain",
            GrantFullControl=f'id="{acl_grantee_id}"',
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidRequest"
    assert (
        err["Message"] == "Specifying both Canned ACLs and Header Grants is not allowed"
    )
