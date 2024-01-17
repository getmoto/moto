import boto3
import pytest
import requests
from botocore.client import ClientError

from moto import mock_aws, settings
from moto.s3.responses import DEFAULT_REGION_NAME

from . import s3_aws_verified
from .test_s3 import add_proxy_details


@mock_aws
def test_get_bucket_tagging_unknown_bucket():
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)

    with pytest.raises(ClientError) as ex:
        client.get_bucket_tagging(Bucket="foobar")
    assert ex.value.response["Error"]["Code"] == "NoSuchBucket"
    assert ex.value.response["Error"]["Message"] == (
        "The specified bucket does not exist"
    )


@pytest.mark.aws_verified
@s3_aws_verified
def test_put_object_with_tagging(bucket_name=None):
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    key = "key-with-tags"

    # using system tags will fail
    with pytest.raises(ClientError) as err:
        s3_client.put_object(
            Bucket=bucket_name, Key=key, Body="test", Tagging="aws:foo=bar"
        )

    err = err.value.response["Error"]
    assert err["Code"] == "InvalidTag"
    assert err["Message"] == "Your TagKey cannot be prefixed with aws:"

    s3_client.put_object(Bucket=bucket_name, Key=key, Body="test", Tagging="foo=bar")

    tags = s3_client.get_object_tagging(Bucket=bucket_name, Key=key)
    assert {"Key": "foo", "Value": "bar"} in tags["TagSet"]

    resp = s3_client.get_object(Bucket=bucket_name, Key=key)
    assert resp["TagCount"] == 1

    s3_client.delete_object_tagging(Bucket=bucket_name, Key=key)

    tags = s3_client.get_object_tagging(Bucket=bucket_name, Key=key)
    assert tags["TagSet"] == []


@pytest.mark.aws_verified
@s3_aws_verified
def test_put_bucket_tagging(bucket_name=None):
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)

    # With 1 tag:
    resp = s3_client.put_bucket_tagging(
        Bucket=bucket_name, Tagging={"TagSet": [{"Key": "TagOne", "Value": "ValueOne"}]}
    )
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 204

    # With multiple tags:
    resp = s3_client.put_bucket_tagging(
        Bucket=bucket_name,
        Tagging={
            "TagSet": [
                {"Key": "TagOne", "Value": "ValueOne"},
                {"Key": "TagTwo", "Value": "ValueTwo"},
                {"Key": "TagThree", "Value": ""},
            ]
        },
    )

    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 204

    # With duplicate tag keys:
    with pytest.raises(ClientError) as err:
        s3_client.put_bucket_tagging(
            Bucket=bucket_name,
            Tagging={
                "TagSet": [
                    {"Key": "TagOne", "Value": "ValueOne"},
                    {"Key": "TagOne", "Value": "ValueOneAgain"},
                ]
            },
        )
    err = err.value.response["Error"]
    assert err["Code"] == "InvalidTag"
    assert err["Message"] == "Cannot provide multiple Tags with the same key"

    # Cannot put tags that are "system" tags - i.e. tags that start with "aws:"
    with pytest.raises(ClientError) as ce_exc:
        s3_client.put_bucket_tagging(
            Bucket=bucket_name,
            Tagging={"TagSet": [{"Key": "aws:sometag", "Value": "nope"}]},
        )
    err = ce_exc.value.response["Error"]
    assert err["Code"] == "InvalidTag"
    assert err["Message"] == "System tags cannot be added/updated by requester"

    # This is OK though:
    s3_client.put_bucket_tagging(
        Bucket=bucket_name,
        Tagging={"TagSet": [{"Key": "something:aws:stuff", "Value": "this is fine"}]},
    )


@pytest.mark.aws_verified
@s3_aws_verified
def test_get_bucket_tagging(bucket_name=None):
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)

    s3_client.put_bucket_tagging(
        Bucket=bucket_name,
        Tagging={
            "TagSet": [
                {"Key": "TagOne", "Value": "ValueOne"},
                {"Key": "TagTwo", "Value": "ValueTwo"},
            ]
        },
    )

    # Get the tags for the bucket:
    resp = s3_client.get_bucket_tagging(Bucket=bucket_name)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert len(resp["TagSet"]) == 2
    assert {"Key": "TagOne", "Value": "ValueOne"} in resp["TagSet"]
    assert {"Key": "TagTwo", "Value": "ValueTwo"} in resp["TagSet"]

    # With no tags:
    s3_client.put_bucket_tagging(Bucket=bucket_name, Tagging={"TagSet": []})

    with pytest.raises(ClientError) as exc:
        s3_client.get_bucket_tagging(Bucket=bucket_name)

    err = exc.value.response["Error"]
    assert err["Code"] == "NoSuchTagSet"
    assert err["Message"] == "The TagSet does not exist"


@mock_aws
def test_delete_bucket_tagging():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "mybucket"
    s3_client.create_bucket(Bucket=bucket_name)

    s3_client.put_bucket_tagging(
        Bucket=bucket_name,
        Tagging={
            "TagSet": [
                {"Key": "TagOne", "Value": "ValueOne"},
                {"Key": "TagTwo", "Value": "ValueTwo"},
            ]
        },
    )

    resp = s3_client.delete_bucket_tagging(Bucket=bucket_name)
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 204

    with pytest.raises(ClientError) as err:
        s3_client.get_bucket_tagging(Bucket=bucket_name)

    err_value = err.value
    assert err_value.response["Error"]["Code"] == "NoSuchTagSet"
    assert err_value.response["Error"]["Message"] == "The TagSet does not exist"


@pytest.mark.aws_verified
@s3_aws_verified
def test_put_object_tagging(bucket_name=None):
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    key = "key-with-tags"

    with pytest.raises(ClientError) as err:
        s3_client.put_object_tagging(
            Bucket=bucket_name,
            Key=key,
            Tagging={
                "TagSet": [
                    {"Key": "item1", "Value": "foo"},
                    {"Key": "item2", "Value": "bar"},
                ]
            },
        )

    err = err.value.response["Error"]
    assert err["Code"] == "NoSuchKey"
    assert err["Message"] == "The specified key does not exist."
    assert err["Key"] == key

    s3_client.put_object(Bucket=bucket_name, Key=key, Body="test")

    # using system tags will fail
    with pytest.raises(ClientError) as err:
        s3_client.put_object_tagging(
            Bucket=bucket_name,
            Key=key,
            Tagging={"TagSet": [{"Key": "aws:item1", "Value": "foo"}]},
        )

    err_value = err.value
    assert err_value.response["Error"]["Code"] == "InvalidTag"

    # Can't put more than 10 tags at the same time
    with pytest.raises(ClientError) as exc:
        s3_client.put_object_tagging(
            Bucket=bucket_name,
            Key=key,
            Tagging={
                "TagSet": [{"Key": f"tag{i}", "Value": "too_many"} for i in range(11)]
            },
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "BadRequest"
    assert err["Message"] == "Object tags cannot be greater than 10"

    resp = s3_client.put_object_tagging(
        Bucket=bucket_name,
        Key=key,
        Tagging={
            "TagSet": [
                {"Key": "item1", "Value": "foo"},
                {"Key": "item2", "Value": "bar"},
                {"Key": "item3", "Value": ""},
            ]
        },
    )

    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200


@mock_aws
def test_put_object_tagging_on_earliest_version():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "mybucket"
    key = "key-with-tags"
    s3_client.create_bucket(Bucket=bucket_name)
    s3_resource = boto3.resource("s3")
    bucket_versioning = s3_resource.BucketVersioning(bucket_name)
    bucket_versioning.enable()
    assert bucket_versioning.status == "Enabled"

    with pytest.raises(ClientError) as err:
        s3_client.put_object_tagging(
            Bucket=bucket_name,
            Key=key,
            Tagging={
                "TagSet": [
                    {"Key": "item1", "Value": "foo"},
                    {"Key": "item2", "Value": "bar"},
                ]
            },
        )

    err_value = err.value
    assert err_value.response["Error"] == {
        "Code": "NoSuchKey",
        "Message": "The specified key does not exist.",
        "Key": "key-with-tags",
        "RequestID": "7a62c49f-347e-4fc4-9331-6e8eEXAMPLE",
    }

    s3_client.put_object(Bucket=bucket_name, Key=key, Body="test")
    s3_client.put_object(Bucket=bucket_name, Key=key, Body="test_updated")

    object_versions = list(s3_resource.Bucket(bucket_name).object_versions.all())
    first_object = object_versions[0]
    second_object = object_versions[1]

    resp = s3_client.put_object_tagging(
        Bucket=bucket_name,
        Key=key,
        Tagging={
            "TagSet": [
                {"Key": "item1", "Value": "foo"},
                {"Key": "item2", "Value": "bar"},
            ]
        },
        VersionId=first_object.id,
    )

    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    # Older version has tags while the most recent does not
    resp = s3_client.get_object_tagging(
        Bucket=bucket_name, Key=key, VersionId=first_object.id
    )
    assert resp["VersionId"] == first_object.id
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    sorted_tagset = sorted(resp["TagSet"], key=lambda t: t["Key"])
    assert sorted_tagset == [
        {"Key": "item1", "Value": "foo"},
        {"Key": "item2", "Value": "bar"},
    ]

    resp = s3_client.get_object_tagging(
        Bucket=bucket_name, Key=key, VersionId=second_object.id
    )
    assert resp["VersionId"] == second_object.id
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert resp["TagSet"] == []


@mock_aws
def test_put_object_tagging_on_both_version():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "mybucket"
    key = "key-with-tags"
    s3_client.create_bucket(Bucket=bucket_name)
    s3_resource = boto3.resource("s3")
    bucket_versioning = s3_resource.BucketVersioning(bucket_name)
    bucket_versioning.enable()
    assert bucket_versioning.status == "Enabled"

    with pytest.raises(ClientError) as err:
        s3_client.put_object_tagging(
            Bucket=bucket_name,
            Key=key,
            Tagging={
                "TagSet": [
                    {"Key": "item1", "Value": "foo"},
                    {"Key": "item2", "Value": "bar"},
                ]
            },
        )

    err_value = err.value
    assert err_value.response["Error"] == {
        "Code": "NoSuchKey",
        "Message": "The specified key does not exist.",
        "Key": "key-with-tags",
        "RequestID": "7a62c49f-347e-4fc4-9331-6e8eEXAMPLE",
    }

    s3_client.put_object(Bucket=bucket_name, Key=key, Body="test")
    s3_client.put_object(Bucket=bucket_name, Key=key, Body="test_updated")

    object_versions = list(s3_resource.Bucket(bucket_name).object_versions.all())
    first_object = object_versions[0]
    second_object = object_versions[1]

    resp = s3_client.put_object_tagging(
        Bucket=bucket_name,
        Key=key,
        Tagging={
            "TagSet": [
                {"Key": "item1", "Value": "foo"},
                {"Key": "item2", "Value": "bar"},
            ]
        },
        VersionId=first_object.id,
    )
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    resp = s3_client.put_object_tagging(
        Bucket=bucket_name,
        Key=key,
        Tagging={
            "TagSet": [
                {"Key": "item1", "Value": "baz"},
                {"Key": "item2", "Value": "bin"},
            ]
        },
        VersionId=second_object.id,
    )
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    resp = s3_client.get_object_tagging(
        Bucket=bucket_name, Key=key, VersionId=first_object.id
    )
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    sorted_tagset = sorted(resp["TagSet"], key=lambda t: t["Key"])
    assert sorted_tagset == [
        {"Key": "item1", "Value": "foo"},
        {"Key": "item2", "Value": "bar"},
    ]

    resp = s3_client.get_object_tagging(
        Bucket=bucket_name, Key=key, VersionId=second_object.id
    )
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    sorted_tagset = sorted(resp["TagSet"], key=lambda t: t["Key"])
    assert sorted_tagset == [
        {"Key": "item1", "Value": "baz"},
        {"Key": "item2", "Value": "bin"},
    ]


@mock_aws
def test_put_object_tagging_with_single_tag():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "mybucket"
    key = "key-with-tags"
    s3_client.create_bucket(Bucket=bucket_name)

    s3_client.put_object(Bucket=bucket_name, Key=key, Body="test")

    resp = s3_client.put_object_tagging(
        Bucket=bucket_name,
        Key=key,
        Tagging={"TagSet": [{"Key": "item1", "Value": "foo"}]},
    )

    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200


@mock_aws
def test_get_object_tagging():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "mybucket"
    key = "key-with-tags"
    s3_client.create_bucket(Bucket=bucket_name)

    s3_client.put_object(Bucket=bucket_name, Key=key, Body="test")

    resp = s3_client.get_object_tagging(Bucket=bucket_name, Key=key)
    assert not resp["TagSet"]

    s3_client.put_object_tagging(
        Bucket=bucket_name,
        Key=key,
        Tagging={
            "TagSet": [
                {"Key": "item1", "Value": "foo"},
                {"Key": "item2", "Value": "bar"},
            ]
        },
    )
    resp = s3_client.get_object_tagging(Bucket=bucket_name, Key=key)

    assert len(resp["TagSet"]) == 2
    assert {"Key": "item1", "Value": "foo"} in resp["TagSet"]
    assert {"Key": "item2", "Value": "bar"} in resp["TagSet"]


@mock_aws
def test_objects_tagging_with_same_key_name():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    key_name = "file.txt"

    bucket1 = "bucket-1"
    s3_client.create_bucket(Bucket=bucket1)
    tagging = "variable=one"

    s3_client.put_object(Bucket=bucket1, Body=b"test", Key=key_name, Tagging=tagging)

    bucket2 = "bucket-2"
    s3_client.create_bucket(Bucket=bucket2)
    tagging2 = "variable=two"

    s3_client.put_object(Bucket=bucket2, Body=b"test", Key=key_name, Tagging=tagging2)

    variable1 = s3_client.get_object_tagging(Bucket=bucket1, Key=key_name)["TagSet"][0][
        "Value"
    ]
    variable2 = s3_client.get_object_tagging(Bucket=bucket2, Key=key_name)["TagSet"][0][
        "Value"
    ]

    assert variable1 == "one"
    assert variable2 == "two"


@mock_aws
def test_generate_url_for_tagged_object():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_client.create_bucket(Bucket="my-bucket")
    s3_client.put_object(
        Bucket="my-bucket", Key="test.txt", Body=b"abc", Tagging="MyTag=value"
    )
    url = s3_client.generate_presigned_url(
        "get_object", Params={"Bucket": "my-bucket", "Key": "test.txt"}
    )
    kwargs = {}
    if settings.is_test_proxy_mode():
        add_proxy_details(kwargs)
    response = requests.get(url, **kwargs)
    assert response.content == b"abc"
    assert response.headers["x-amz-tagging-count"] == "1"
