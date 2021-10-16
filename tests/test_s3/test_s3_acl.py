import boto3
import os
import pytest
import requests
import sure  # noqa

from botocore.exceptions import ClientError
from botocore.handlers import disable_signing
from moto import mock_s3
from uuid import uuid4

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
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = str(uuid4())
    bucket = s3.Bucket(bucket_name)
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
    grants.should.have.length_of(1)
    grants[0].should.have.key("Grantee").equal({"Type": _type, response_key: value})
    grants[0].should.have.key("Permission").equal(readwrite.upper())


@mock_s3
def test_acl_switching_boto3():
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket = s3.Bucket("foobar")
    bucket.create()
    keyname = "test.txt"

    bucket.put_object(Key=keyname, Body=b"asdf", ACL="public-read")
    client.put_object_acl(ACL="private", Bucket="foobar", Key=keyname)

    grants = client.get_object_acl(Bucket="foobar", Key=keyname)["Grants"]
    grants.shouldnt.contain(
        {
            "Grantee": {
                "Type": "Group",
                "URI": "http://acs.amazonaws.com/groups/global/AllUsers",
            },
            "Permission": "READ",
        }
    )


@mock_s3
def test_acl_switching_nonexistent_key():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket="mybucket")

    with pytest.raises(ClientError) as e:
        s3.put_object_acl(Bucket="mybucket", Key="nonexistent", ACL="private")

    e.value.response["Error"]["Code"].should.equal("NoSuchKey")


@mock_s3
def test_s3_object_in_public_bucket():
    s3 = boto3.resource("s3")
    bucket = s3.Bucket("test-bucket")
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
    contents.should.equal(b"ABCD")

    bucket.put_object(ACL="private", Body=b"ABCD", Key="file.txt")

    with pytest.raises(ClientError) as exc:
        s3_anonymous.Object(key="file.txt", bucket_name="test-bucket").get()
    exc.value.response["Error"]["Code"].should.equal("403")


@mock_s3
def test_s3_object_in_public_bucket_using_multiple_presigned_urls():
    s3 = boto3.resource("s3")
    bucket = s3.Bucket("test-bucket")
    bucket.create(
        ACL="public-read", CreateBucketConfiguration={"LocationConstraint": "us-west-1"}
    )
    bucket.put_object(Body=b"ABCD", Key="file.txt")

    params = {"Bucket": "test-bucket", "Key": "file.txt"}
    presigned_url = boto3.client("s3").generate_presigned_url(
        "get_object", params, ExpiresIn=900
    )
    for i in range(1, 10):
        response = requests.get(presigned_url)
        assert response.status_code == 200, "Failed on req number {}".format(i)


@mock_s3
def test_s3_object_in_private_bucket():
    s3 = boto3.resource("s3")
    bucket = s3.Bucket("test-bucket")
    bucket.create(
        ACL="private", CreateBucketConfiguration={"LocationConstraint": "us-west-1"}
    )
    bucket.put_object(ACL="private", Body=b"ABCD", Key="file.txt")

    s3_anonymous = boto3.resource("s3")
    s3_anonymous.meta.client.meta.events.register("choose-signer.s3.*", disable_signing)

    with pytest.raises(ClientError) as exc:
        s3_anonymous.Object(key="file.txt", bucket_name="test-bucket").get()
    exc.value.response["Error"]["Code"].should.equal("403")

    bucket.put_object(ACL="public-read", Body=b"ABCD", Key="file.txt")
    contents = (
        s3_anonymous.Object(key="file.txt", bucket_name="test-bucket")
        .get()["Body"]
        .read()
    )
    contents.should.equal(b"ABCD")


@mock_s3
def test_put_bucket_acl_body():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3.create_bucket(Bucket="bucket")
    bucket_owner = s3.get_bucket_acl(Bucket="bucket")["Owner"]
    s3.put_bucket_acl(
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

    result = s3.get_bucket_acl(Bucket="bucket")
    assert len(result["Grants"]) == 2
    for g in result["Grants"]:
        assert g["Grantee"]["URI"] == "http://acs.amazonaws.com/groups/s3/LogDelivery"
        assert g["Grantee"]["Type"] == "Group"
        assert g["Permission"] in ["WRITE", "READ_ACP"]

    # With one:
    s3.put_bucket_acl(
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
    result = s3.get_bucket_acl(Bucket="bucket")
    assert len(result["Grants"]) == 1

    # With no owner:
    with pytest.raises(ClientError) as err:
        s3.put_bucket_acl(
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
        s3.put_bucket_acl(
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
    result = s3.put_bucket_acl(
        Bucket="bucket", AccessControlPolicy={"Grants": [], "Owner": bucket_owner}
    )
    assert not result.get("Grants")


@mock_s3
def test_object_acl_with_presigned_post():
    s3 = boto3.client("s3", region_name=DEFAULT_REGION_NAME)

    bucket_name = "imageS3Bucket"
    object_name = "text.txt"
    fields = {"acl": "public-read"}
    file = open("text.txt", "w")
    file.write("test")
    file.close()

    s3.create_bucket(Bucket=bucket_name)
    response = s3.generate_presigned_post(
        bucket_name, object_name, Fields=fields, ExpiresIn=60000
    )

    with open(object_name, "rb") as f:
        files = {"file": (object_name, f)}
        requests.post(response["url"], data=response["fields"], files=files)

    response = s3.get_object_acl(Bucket=bucket_name, Key=object_name)

    assert "Grants" in response
    assert len(response["Grants"]) == 2
    assert response["Grants"][1]["Permission"] == "READ"

    response = s3.get_object(Bucket=bucket_name, Key=object_name)

    assert "ETag" in response
    assert "Body" in response
    os.remove("text.txt")


@mock_s3
def test_acl_setting_boto3():
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket = s3.Bucket("foobar")
    bucket.create()

    content = b"imafile"
    keyname = "test.txt"
    bucket.put_object(
        Key=keyname, Body=content, ContentType="text/plain", ACL="public-read"
    )

    grants = client.get_object_acl(Bucket="foobar", Key=keyname)["Grants"]
    grants.should.contain(
        {
            "Grantee": {
                "Type": "Group",
                "URI": "http://acs.amazonaws.com/groups/global/AllUsers",
            },
            "Permission": "READ",
        }
    )


@mock_s3
def test_acl_setting_via_headers_boto3():
    s3 = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket = s3.Bucket("foobar")
    bucket.create()

    keyname = "test.txt"

    bucket.put_object(Key=keyname, Body=b"imafile")
    client.put_object_acl(ACL="public-read", Bucket="foobar", Key=keyname)

    grants = client.get_object_acl(Bucket="foobar", Key=keyname)["Grants"]
    grants.should.contain(
        {
            "Grantee": {
                "Type": "Group",
                "URI": "http://acs.amazonaws.com/groups/global/AllUsers",
            },
            "Permission": "READ",
        }
    )
