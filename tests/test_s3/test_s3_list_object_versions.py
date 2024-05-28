from time import sleep
from unittest import SkipTest, mock
from uuid import uuid4

import boto3
import pytest

from moto import mock_aws, settings
from moto.s3.responses import DEFAULT_REGION_NAME

from . import s3_aws_verified


@mock_aws
def test_list_versions():
    s3_resource = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket = s3_resource.Bucket("foobar")
    bucket.create()
    bucket.Versioning().enable()

    key_versions = []

    key = bucket.put_object(Key="the-key", Body=b"Version 1")
    key_versions.append(key.version_id)
    key = bucket.put_object(Key="the-key", Body=b"Version 2")
    key_versions.append(key.version_id)
    assert len(key_versions) == 2

    versions = client.list_object_versions(Bucket="foobar")["Versions"]
    assert len(versions) == 2

    assert versions[0]["Key"] == "the-key"
    assert versions[0]["VersionId"] == key_versions[1]
    resp = client.get_object(Bucket="foobar", Key="the-key")
    assert resp["Body"].read() == b"Version 2"
    resp = client.get_object(
        Bucket="foobar", Key="the-key", VersionId=versions[0]["VersionId"]
    )
    assert resp["Body"].read() == b"Version 2"

    assert versions[1]["Key"] == "the-key"
    assert versions[1]["VersionId"] == key_versions[0]
    resp = client.get_object(
        Bucket="foobar", Key="the-key", VersionId=versions[1]["VersionId"]
    )
    assert resp["Body"].read() == b"Version 1"

    bucket.put_object(Key="the2-key", Body=b"Version 1")

    assert len(list(bucket.objects.all())) == 2
    versions = client.list_object_versions(Bucket="foobar", Prefix="the2")["Versions"]
    assert len(versions) == 1


@mock_aws
def test_list_object_versions():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "000" + str(uuid4())
    key = "key-with-versions"
    s3_client.create_bucket(Bucket=bucket_name)
    s3_client.put_bucket_versioning(
        Bucket=bucket_name, VersioningConfiguration={"Status": "Enabled"}
    )
    items = (b"v1", b"v2")
    for body in items:
        s3_client.put_object(Bucket=bucket_name, Key=key, Body=body)
    response = s3_client.list_object_versions(Bucket=bucket_name)
    # Two object versions should be returned
    assert len(response["Versions"]) == 2
    keys = {item["Key"] for item in response["Versions"]}
    assert keys == {key}

    # the first item in the list should be the latest
    assert response["Versions"][0]["IsLatest"] is True

    # Test latest object version is returned
    response = s3_client.get_object(Bucket=bucket_name, Key=key)
    assert response["Body"].read() == items[-1]


@pytest.mark.aws_verified
@s3_aws_verified
def test_list_object_versions_with_delimiter(bucket_name=None):
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    enable_versioning(bucket_name, s3_client)
    for key_index in list(range(1, 5)) + list(range(10, 14)):
        for version_index in range(1, 4):
            body = f"data-{version_index}".encode("UTF-8")
            s3_client.put_object(
                Bucket=bucket_name, Key=f"key{key_index}-with-data", Body=body
            )
            s3_client.put_object(
                Bucket=bucket_name, Key=f"key{key_index}-without-data", Body=b""
            )
    response = s3_client.list_object_versions(Bucket=bucket_name)
    # All object versions should be returned
    # 8 keys * 2 (one with, one without) * 3 versions per key
    assert len(response["Versions"]) == 48

    # Use start of key as delimiter
    response = s3_client.list_object_versions(Bucket=bucket_name, Delimiter="key1")
    assert response["CommonPrefixes"] == [{"Prefix": "key1"}]
    assert response["Delimiter"] == "key1"
    # 3 keys that do not contain the phrase 'key1' (key2, key3, key4) * * 2 *  3
    assert len(response["Versions"]) == 18

    # Use in-between key as delimiter
    response = s3_client.list_object_versions(Bucket=bucket_name, Delimiter="-with-")
    assert response["CommonPrefixes"] == [
        {"Prefix": "key1-with-"},
        {"Prefix": "key10-with-"},
        {"Prefix": "key11-with-"},
        {"Prefix": "key12-with-"},
        {"Prefix": "key13-with-"},
        {"Prefix": "key2-with-"},
        {"Prefix": "key3-with-"},
        {"Prefix": "key4-with-"},
    ]

    assert response["Delimiter"] == "-with-"
    # key(1/10/11/12/13)-without, key(2/3/4)-without
    assert len(response["Versions"]) == (8 * 1 * 3)

    # Use in-between key as delimiter
    response = s3_client.list_object_versions(Bucket=bucket_name, Delimiter="1-with-")
    assert response["CommonPrefixes"] == (
        [{"Prefix": "key1-with-"}, {"Prefix": "key11-with-"}]
    )
    assert response["Delimiter"] == "1-with-"
    assert len(response["Versions"]) == 42
    all_keys = {v["Key"] for v in response["Versions"]}
    assert "key1-without-data" in all_keys
    assert "key1-with-data" not in all_keys
    assert "key4-with-data" in all_keys
    assert "key4-without-data" in all_keys

    # Use in-between key as delimiter + prefix
    response = s3_client.list_object_versions(
        Bucket=bucket_name, Prefix="key1", Delimiter="with-"
    )
    assert response["CommonPrefixes"] == [
        {"Prefix": "key1-with-"},
        {"Prefix": "key10-with-"},
        {"Prefix": "key11-with-"},
        {"Prefix": "key12-with-"},
        {"Prefix": "key13-with-"},
    ]
    assert response["Delimiter"] == "with-"
    assert response["KeyMarker"] == ""
    assert "NextKeyMarker" not in response
    assert len(response["Versions"]) == 15
    all_keys = {v["Key"] for v in response["Versions"]}
    assert all_keys == {
        "key1-without-data",
        "key10-without-data",
        "key11-without-data",
        "key13-without-data",
        "key12-without-data",
    }

    # Start at KeyMarker, and filter using Prefix+Delimiter for all subsequent keys
    response = s3_client.list_object_versions(
        Bucket=bucket_name, Prefix="key1", Delimiter="with-", KeyMarker="key11"
    )
    assert response["CommonPrefixes"] == [
        {"Prefix": "key11-with-"},
        {"Prefix": "key12-with-"},
        {"Prefix": "key13-with-"},
    ]
    assert response["Delimiter"] == "with-"
    assert response["KeyMarker"] == "key11"
    assert "NextKeyMarker" not in response
    assert len(response["Versions"]) == 9
    all_keys = {v["Key"] for v in response["Versions"]}
    assert all_keys == (
        {"key11-without-data", "key12-without-data", "key13-without-data"}
    )

    # Delimiter with Prefix being the entire key
    response = s3_client.list_object_versions(
        Bucket=bucket_name, Prefix="key1-with-data", Delimiter="-"
    )
    assert len(response["Versions"]) == 3
    assert "CommonPrefixes" not in response

    # Delimiter without prefix
    response = s3_client.list_object_versions(Bucket=bucket_name, Delimiter="-with-")
    assert len(response["CommonPrefixes"]) == 8
    assert {"Prefix": "key1-with-"} in response["CommonPrefixes"]
    # Should return all keys -without-data
    assert len(response["Versions"]) == 24


@mock_aws
def test_list_object_versions_with_delimiter_for_deleted_objects():
    bucket_name = "tests_bucket"
    client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    # Create bucket with versioning
    client.create_bucket(Bucket=bucket_name)
    client.put_bucket_versioning(
        Bucket=bucket_name,
        VersioningConfiguration={"MFADelete": "Disabled", "Status": "Enabled"},
    )

    # Create a history of objects
    for pos in range(2):
        client.put_object(
            Bucket=bucket_name, Key=f"obj_{pos}", Body=f"object {pos}".encode("utf-8")
        )

    for pos in range(2):
        client.put_object(
            Bucket=bucket_name,
            Key=f"hist_obj_{pos}",
            Body=f"history object {pos}".encode("utf-8"),
        )
        for hist_pos in range(2):
            client.put_object(
                Bucket=bucket_name,
                Key=f"hist_obj_{pos}",
                Body=f"object {pos} {hist_pos}".encode("utf-8"),
            )

    for pos in range(2):
        client.put_object(
            Bucket=bucket_name,
            Key=f"del_obj_{pos}",
            Body=f"deleted object {pos}".encode("utf-8"),
        )
        client.delete_object(Bucket=bucket_name, Key=f"del_obj_{pos}")

    # Verify we only retrieve the DeleteMarkers that have this prefix
    objs = client.list_object_versions(Bucket=bucket_name)
    assert [dm["Key"] for dm in objs["DeleteMarkers"]] == ["del_obj_0", "del_obj_1"]

    hist_objs = client.list_object_versions(Bucket=bucket_name, Prefix="hist_obj")
    assert "DeleteMarkers" not in hist_objs

    del_objs = client.list_object_versions(Bucket=bucket_name, Prefix="del_obj_0")
    assert [dm["Key"] for dm in del_objs["DeleteMarkers"]] == ["del_obj_0"]


@mock_aws
def test_list_object_versions_with_versioning_disabled():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "mybucket"
    key = "key-with-versions"
    s3_client.create_bucket(Bucket=bucket_name)
    items = (b"v1", b"v2")
    for body in items:
        s3_client.put_object(Bucket=bucket_name, Key=key, Body=body)
    response = s3_client.list_object_versions(Bucket=bucket_name)

    # One object version should be returned
    assert len(response["Versions"]) == 1
    assert response["Versions"][0]["Key"] == key

    # The version id should be the string null
    assert response["Versions"][0]["VersionId"] == "null"

    # Test latest object version is returned
    response = s3_client.get_object(Bucket=bucket_name, Key=key)
    assert "VersionId" not in response["ResponseMetadata"]["HTTPHeaders"]
    assert response["Body"].read() == items[-1]


@mock_aws
def test_list_object_versions_with_versioning_enabled_late():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "mybucket"
    key = "key-with-versions"
    s3_client.create_bucket(Bucket=bucket_name)
    items = (b"v1", b"v2")
    s3_client.put_object(Bucket=bucket_name, Key=key, Body=b"v1")
    s3_client.put_bucket_versioning(
        Bucket=bucket_name, VersioningConfiguration={"Status": "Enabled"}
    )
    s3_client.put_object(Bucket=bucket_name, Key=key, Body=b"v2")
    response = s3_client.list_object_versions(Bucket=bucket_name)

    # Two object versions should be returned
    assert len(response["Versions"]) == 2
    keys = {item["Key"] for item in response["Versions"]}
    assert keys == {key}

    # There should still be a null version id.
    versions_id = {item["VersionId"] for item in response["Versions"]}
    assert "null" in versions_id

    # Test latest object version is returned
    response = s3_client.get_object(Bucket=bucket_name, Key=key)
    assert response["Body"].read() == items[-1]


@pytest.mark.aws_verified
@s3_aws_verified
def test_list_object_versions_with_paging(bucket_name=None):
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    enable_versioning(bucket_name, s3_client)

    obj1ver1 = s3_client.put_object(Bucket=bucket_name, Key="obj1", Body=b"ver1")
    obj1ver2 = s3_client.put_object(Bucket=bucket_name, Key="obj1", Body=b"ver2")
    obj1ver3 = s3_client.put_object(Bucket=bucket_name, Key="obj1", Body=b"ver3")

    page1 = s3_client.list_object_versions(
        Bucket=bucket_name,
        MaxKeys=2,
    )

    # Page should have two versions only, and should be truncated.
    assert len(page1["Versions"]) == 2
    assert "DeleteMarkers" not in page1
    assert page1["IsTruncated"] is True

    # This should be obj1 ver3 (latest).
    assert page1["Versions"][0]["VersionId"] == obj1ver3["VersionId"]
    assert page1["Versions"][0]["IsLatest"] is True

    # This should be obj1 ver2.
    assert page1["Versions"][1]["VersionId"] == obj1ver2["VersionId"]

    # The next key/version markers should point to obj1 ver1.
    assert "NextKeyMarker" in page1
    assert page1["NextKeyMarker"] == "obj1"
    assert "NextVersionIdMarker" in page1
    assert page1["NextVersionIdMarker"] == obj1ver2["VersionId"]

    # Second page should be the last page and have the oldest version.
    page2 = s3_client.list_object_versions(
        Bucket=bucket_name,
        MaxKeys=2,
        KeyMarker=page1["NextKeyMarker"],
        VersionIdMarker=page1["NextVersionIdMarker"],
    )

    # Page should have one version only, and not be truncated.
    assert len(page2["Versions"]) == 1
    assert "DeleteMarkers" not in page2
    assert page2["IsTruncated"] is False
    assert "NextKeyMarker" not in page2
    assert "NextVersionIdMarker" not in page2

    # This should be obj1 ver1.
    assert page2["Versions"][0]["VersionId"] == obj1ver1["VersionId"]


@pytest.mark.aws_verified
@s3_aws_verified
def test_list_object_versions_with_paging_and_delete_markers(bucket_name=None):
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    enable_versioning(bucket_name, s3_client)

    # A mix of versions and delete markers.
    obj1ver1 = s3_client.put_object(Bucket=bucket_name, Key="obj1", Body=b"ver1")
    obj2ver1 = s3_client.put_object(Bucket=bucket_name, Key="obj2", Body=b"ver1")
    obj1dmk1 = s3_client.delete_object(Bucket=bucket_name, Key="obj1")
    obj1dmk2 = s3_client.delete_object(Bucket=bucket_name, Key="obj1")
    obj1dmk3 = s3_client.delete_object(Bucket=bucket_name, Key="obj1")
    obj2dmk1 = s3_client.delete_object(Bucket=bucket_name, Key="obj2")

    page1 = s3_client.list_object_versions(
        Bucket=bucket_name,
        MaxKeys=2,
    )

    # Page should have one version and one delete marker, and be truncated.
    assert "Versions" not in page1
    assert len(page1["DeleteMarkers"]) == 2
    assert page1["IsTruncated"] is True

    # This should be obj1 dmk3 (latest).
    assert page1["DeleteMarkers"][0]["VersionId"] == obj1dmk3["VersionId"]
    assert page1["DeleteMarkers"][0]["IsLatest"] is True

    # This should be obj1 dmk2.
    assert page1["DeleteMarkers"][1]["VersionId"] == obj1dmk2["VersionId"]

    # The next key/version markers should point to obj1 dmk1.
    assert "NextKeyMarker" in page1
    assert page1["NextKeyMarker"] == "obj1"
    assert "NextVersionIdMarker" in page1
    assert page1["NextVersionIdMarker"] == obj1dmk2["VersionId"]

    page2 = s3_client.list_object_versions(
        Bucket=bucket_name,
        MaxKeys=2,
        KeyMarker=page1["NextKeyMarker"],
        VersionIdMarker=page1["NextVersionIdMarker"],
    )

    # Page should have one version and one delete marker, and be truncated.
    assert len(page2["Versions"]) == 1
    assert len(page2["DeleteMarkers"]) == 1
    assert page2["IsTruncated"] is True

    # This should be obj1 ver1.
    assert page2["Versions"][0]["VersionId"] == obj1ver1["VersionId"]

    # This should be obj1 dmk1.
    assert page2["DeleteMarkers"][0]["VersionId"] == obj1dmk1["VersionId"]

    # The next key/version markers should point to obj2 dmk1.
    assert "NextKeyMarker" in page2
    assert page2["NextKeyMarker"] == "obj1"
    assert "NextVersionIdMarker" in page2
    assert page2["NextVersionIdMarker"] == obj1ver1["VersionId"]

    page3 = s3_client.list_object_versions(
        Bucket=bucket_name,
        MaxKeys=2,
        KeyMarker=page2["NextKeyMarker"],
        VersionIdMarker=page2["NextVersionIdMarker"],
    )

    # Page should have one version and one delete marker, and not be truncated.
    assert len(page3["Versions"]) == 1
    assert len(page3["DeleteMarkers"]) == 1
    assert page3["IsTruncated"] is False

    # This should be obj2 ver1.
    assert page3["Versions"][0]["VersionId"] == obj2ver1["VersionId"]

    # This should be obj2 dmk1 (latest).
    assert page3["DeleteMarkers"][0]["VersionId"] == obj2dmk1["VersionId"]
    assert page3["DeleteMarkers"][0]["IsLatest"]

    # There should not be any next key/version marker.
    assert "NextKeyMarker" not in page3
    assert "NextVersionIdMarker" not in page3


@pytest.mark.aws_verified
@s3_aws_verified
def test_list_object_versions_with_paging_and_delimiter(bucket_name=None):
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)

    enable_versioning(bucket_name, s3_client)

    # Copied from test_list_object_versions_with_delimiter.
    for key_index in list(range(1, 5)) + list(range(10, 14)):
        for version_index in range(1, 4):
            body = f"data-{version_index}".encode("UTF-8")
            s3_client.put_object(
                Bucket=bucket_name, Key=f"key{key_index}-with-data", Body=body
            )
            s3_client.put_object(
                Bucket=bucket_name, Key=f"key{key_index}-without-data", Body=b""
            )

    page1 = s3_client.list_object_versions(
        Bucket=bucket_name,
        Delimiter="with-",
        Prefix="key1",
        KeyMarker="key11",
        MaxKeys=5,
    )

    assert "Versions" in page1
    assert len(page1["Versions"]) == 3
    assert [v["Key"] for v in page1["Versions"]] == [
        "key11-without-data",
        "key11-without-data",
        "key11-without-data",
    ]

    assert "CommonPrefixes" in page1
    assert [p["Prefix"] for p in page1["CommonPrefixes"]] == [
        "key11-with-",
        "key12-with-",
    ]

    assert page1["IsTruncated"] is True
    assert page1["NextKeyMarker"] == "key12-with-"
    assert "NextVersionIdMarker" not in page1

    page2 = s3_client.list_object_versions(
        Bucket=bucket_name,
        Delimiter="with-",
        Prefix="key1",
        KeyMarker="key12-with-",
        MaxKeys=5,
    )

    assert "Versions" in page2
    assert len(page2["Versions"]) == 4
    assert [v["Key"] for v in page2["Versions"]] == [
        "key12-without-data",
        "key12-without-data",
        "key12-without-data",
        "key13-without-data",
    ]

    assert "CommonPrefixes" in page2
    assert [p["Prefix"] for p in page2["CommonPrefixes"]] == [
        "key13-with-",
    ]

    assert page2["IsTruncated"] is True
    assert page2["NextKeyMarker"] == "key13-without-data"
    assert "NextVersionIdMarker" in page2  # FIXME check VersionId?

    page3 = s3_client.list_object_versions(
        Bucket=bucket_name,
        Delimiter="with-",
        Prefix="key1",
        KeyMarker="key13-without-data",
        VersionIdMarker=page2["NextVersionIdMarker"],
        MaxKeys=5,
    )

    assert "Versions" in page3
    assert len(page3["Versions"]) == 2
    assert [v["Key"] for v in page3["Versions"]] == [
        "key13-without-data",
        "key13-without-data",
    ]

    assert "CommonPrefixes" not in page3

    assert page3["IsTruncated"] is False
    assert "NextKeyMarker" not in page3
    assert "NextVersionIdMarker" not in page3


@mock_aws
def test_bad_prefix_list_object_versions():
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "mybucket"
    key = "key-with-versions"
    bad_prefix = "key-that-does-not-exist"
    s3_client.create_bucket(Bucket=bucket_name)
    s3_client.put_bucket_versioning(
        Bucket=bucket_name, VersioningConfiguration={"Status": "Enabled"}
    )
    items = (b"v1", b"v2")
    for body in items:
        s3_client.put_object(Bucket=bucket_name, Key=key, Body=body)
    response = s3_client.list_object_versions(Bucket=bucket_name, Prefix=bad_prefix)
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert "Versions" not in response
    assert "DeleteMarkers" not in response


@pytest.mark.aws_verified
@s3_aws_verified
def test_list_object_versions__sort_order(bucket_name=None):
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    enable_versioning(bucket_name, s3_client)

    # Put one object, and delete it
    upl = s3_client.put_object(Bucket=bucket_name, Key="bbb", Body=b"ver1")
    b_ver1 = upl["ResponseMetadata"]["HTTPHeaders"]["x-amz-version-id"]

    b_del = s3_client.delete_object(Bucket=bucket_name, Key="bbb")["VersionId"]

    # Asking for one version:
    # We'll get the deleted version first
    version_list = s3_client.list_object_versions(Bucket=bucket_name, MaxKeys=1)
    assert "Versions" not in version_list
    assert len(version_list["DeleteMarkers"]) == 1
    assert version_list["DeleteMarkers"][0]["VersionId"] == b_del

    # Create an object with a name that comes first alphabetically
    # We'll get this object first
    a_ver1 = s3_client.put_object(Bucket=bucket_name, Key="aaa", Body=b"ver1")[
        "VersionId"
    ]

    # Asking for one version:
    # We'll get the new object first (because it's alphabetically earlier)
    version_list = s3_client.list_object_versions(Bucket=bucket_name, MaxKeys=1)
    assert "DeleteMarkers" not in version_list
    assert len(version_list["Versions"]) == 1
    assert version_list["Versions"][0]["VersionId"] == a_ver1

    # To double-check: create another object that's alphabetically at the end, but most recent
    s3_client.put_object(Bucket=bucket_name, Key="zzz", Body=b"ver1")

    # Asking for one version:
    # We'll still get the a-object first (because it's alphabetically earlier)
    version_list = s3_client.list_object_versions(Bucket=bucket_name, MaxKeys=1)
    assert "DeleteMarkers" not in version_list
    assert len(version_list["Versions"]) == 1
    assert version_list["Versions"][0]["VersionId"] == a_ver1

    # Asking for two versions:
    # We'll get the a-object first, and the deleted version
    version_list = s3_client.list_object_versions(Bucket=bucket_name, MaxKeys=2)
    assert len(version_list["Versions"]) == 1
    assert version_list["Versions"][0]["VersionId"] == a_ver1
    assert len(version_list["DeleteMarkers"]) == 1
    assert version_list["DeleteMarkers"][0]["VersionId"] == b_del

    # Create a different version of the b-object
    b_ver2 = s3_client.put_object(Bucket=bucket_name, Key="bbb", Body=b"ver2")[
        "VersionId"
    ]

    # We'll still get the new object first
    version_list = s3_client.list_object_versions(Bucket=bucket_name, MaxKeys=1)
    assert len(version_list["Versions"]) == 1
    assert version_list["Versions"][0]["VersionId"] == a_ver1

    # Asking for two versions:
    # We'll get the latest version of b
    version_list = s3_client.list_object_versions(Bucket=bucket_name, MaxKeys=2)
    assert len(version_list["Versions"]) == 2
    assert version_list["Versions"][0]["VersionId"] == a_ver1
    assert version_list["Versions"][1]["VersionId"] == b_ver2

    # Asking for three versions:
    # We also get the deleted version
    # Which proves that we order by time first, and only then by type
    version_list = s3_client.list_object_versions(Bucket=bucket_name, MaxKeys=3)
    assert len(version_list["Versions"]) == 2
    assert version_list["Versions"][0]["VersionId"] == a_ver1
    assert version_list["Versions"][1]["VersionId"] == b_ver2
    assert len(version_list["DeleteMarkers"]) == 1
    assert version_list["DeleteMarkers"][0]["VersionId"] == b_del

    # Asking for four versions:
    # Only now do we get the initial b-object
    # Because it was created the earliest (of all a + b objects)
    version_list = s3_client.list_object_versions(Bucket=bucket_name, MaxKeys=4)
    assert len(version_list["Versions"]) == 3
    assert version_list["Versions"][0]["VersionId"] == a_ver1
    assert version_list["Versions"][1]["VersionId"] == b_ver2
    assert version_list["Versions"][2]["VersionId"] == b_ver1
    assert len(version_list["DeleteMarkers"]) == 1
    assert version_list["DeleteMarkers"][0]["VersionId"] == b_del


def enable_versioning(bucket_name, s3_client):
    s3_client.put_bucket_versioning(
        Bucket=bucket_name, VersioningConfiguration={"Status": "Enabled"}
    )
    # Versioning is not active immediately, so wait until we have confirmation the change has gone through
    resp = {}
    while resp.get("Status") != "Enabled":
        sleep(0.1)
        resp = s3_client.get_bucket_versioning(Bucket=bucket_name)


@mock_aws
@mock.patch.dict("os.environ", {"MOTO_S3_DEFAULT_MAX_KEYS": "5"})
def test_list_object_versions_with_custom_limit():
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("Can only set env var in DecoratorMode")
    s3_client = boto3.client("s3", region_name=DEFAULT_REGION_NAME)
    s3_resource = boto3.resource("s3", region_name=DEFAULT_REGION_NAME)
    bucket_name = "foobar"
    bucket = s3_resource.Bucket(bucket_name)
    bucket.create()
    bucket.Versioning().enable()

    for i in range(10):
        s3_client.put_object(
            Bucket=bucket_name, Key="obj", Body=b"ver" + str(i).encode("utf-8")
        )

    page1 = s3_client.list_object_versions(Bucket=bucket_name)
    assert page1["MaxKeys"] == 5
    assert len(page1["Versions"]) == 5
