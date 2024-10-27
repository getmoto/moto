from datetime import datetime

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.s3.responses import DEFAULT_REGION_NAME


@mock_aws
def test_lifecycle_with_filters():
    client = boto3.client("s3", DEFAULT_REGION_NAME)
    client.create_bucket(Bucket="bucket")

    # Create a lifecycle rule with a Filter (no tags):
    lfc = {
        "Rules": [
            {
                "Expiration": {"Days": 7},
                "ID": "wholebucket",
                "Filter": {"Prefix": ""},
                "Status": "Enabled",
            }
        ]
    }
    client.put_bucket_lifecycle_configuration(
        Bucket="bucket", LifecycleConfiguration=lfc
    )
    result = client.get_bucket_lifecycle_configuration(Bucket="bucket")
    assert len(result["Rules"]) == 1
    assert result["Rules"][0]["Filter"]["Prefix"] == ""
    assert not result["Rules"][0]["Filter"].get("And")
    assert not result["Rules"][0]["Filter"].get("Tag")
    with pytest.raises(KeyError):
        assert result["Rules"][0]["Prefix"]

    # Without any prefixes and an empty filter (this is by default a prefix for the whole bucket):
    lfc = {
        "Rules": [
            {
                "Expiration": {"Days": 7},
                "ID": "wholebucket",
                "Filter": {},
                "Status": "Enabled",
            }
        ]
    }
    client.put_bucket_lifecycle_configuration(
        Bucket="bucket", LifecycleConfiguration=lfc
    )
    result = client.get_bucket_lifecycle_configuration(Bucket="bucket")
    assert len(result["Rules"]) == 1
    with pytest.raises(KeyError):
        assert result["Rules"][0]["Prefix"]

    # If we remove the filter -- and don't specify a Prefix, then this is bad:
    lfc["Rules"][0].pop("Filter")
    with pytest.raises(ClientError) as err:
        client.put_bucket_lifecycle_configuration(
            Bucket="bucket", LifecycleConfiguration=lfc
        )
    assert err.value.response["Error"]["Code"] == "MalformedXML"

    # With a tag:
    lfc["Rules"][0]["Filter"] = {"Tag": {"Key": "mytag", "Value": "mytagvalue"}}
    client.put_bucket_lifecycle_configuration(
        Bucket="bucket", LifecycleConfiguration=lfc
    )
    result = client.get_bucket_lifecycle_configuration(Bucket="bucket")
    assert len(result["Rules"]) == 1
    with pytest.raises(KeyError):
        assert result["Rules"][0]["Filter"]["Prefix"]
    assert not result["Rules"][0]["Filter"].get("And")
    assert result["Rules"][0]["Filter"]["Tag"]["Key"] == "mytag"
    assert result["Rules"][0]["Filter"]["Tag"]["Value"] == "mytagvalue"
    with pytest.raises(KeyError):
        assert result["Rules"][0]["Prefix"]

    # With And (single tag):
    lfc["Rules"][0]["Filter"] = {
        "And": {
            "Prefix": "some/prefix",
            "Tags": [{"Key": "mytag", "Value": "mytagvalue"}],
        }
    }
    client.put_bucket_lifecycle_configuration(
        Bucket="bucket", LifecycleConfiguration=lfc
    )
    result = client.get_bucket_lifecycle_configuration(Bucket="bucket")
    assert len(result["Rules"]) == 1
    assert not result["Rules"][0]["Filter"].get("Prefix")
    assert result["Rules"][0]["Filter"]["And"]["Prefix"] == "some/prefix"
    assert len(result["Rules"][0]["Filter"]["And"]["Tags"]) == 1
    assert result["Rules"][0]["Filter"]["And"]["Tags"][0]["Key"] == "mytag"
    assert result["Rules"][0]["Filter"]["And"]["Tags"][0]["Value"] == "mytagvalue"
    with pytest.raises(KeyError):
        assert result["Rules"][0]["Prefix"]

    # With multiple And tags:
    lfc["Rules"][0]["Filter"]["And"] = {
        "Prefix": "some/prefix",
        "Tags": [
            {"Key": "mytag", "Value": "mytagvalue"},
            {"Key": "mytag2", "Value": "mytagvalue2"},
        ],
    }
    client.put_bucket_lifecycle_configuration(
        Bucket="bucket", LifecycleConfiguration=lfc
    )
    result = client.get_bucket_lifecycle_configuration(Bucket="bucket")
    assert len(result["Rules"]) == 1
    assert not result["Rules"][0]["Filter"].get("Prefix")
    assert result["Rules"][0]["Filter"]["And"]["Prefix"] == "some/prefix"
    assert len(result["Rules"][0]["Filter"]["And"]["Tags"]) == 2
    assert result["Rules"][0]["Filter"]["And"]["Tags"][0]["Key"] == "mytag"
    assert result["Rules"][0]["Filter"]["And"]["Tags"][0]["Value"] == "mytagvalue"
    assert result["Rules"][0]["Filter"]["And"]["Tags"][1]["Key"] == "mytag2"
    assert result["Rules"][0]["Filter"]["And"]["Tags"][1]["Value"] == "mytagvalue2"
    with pytest.raises(KeyError):
        assert result["Rules"][0]["Prefix"]

    # And filter without Prefix but multiple Tags:
    lfc["Rules"][0]["Filter"]["And"] = {
        "Tags": [
            {"Key": "mytag", "Value": "mytagvalue"},
            {"Key": "mytag2", "Value": "mytagvalue2"},
        ]
    }
    client.put_bucket_lifecycle_configuration(
        Bucket="bucket", LifecycleConfiguration=lfc
    )
    result = client.get_bucket_lifecycle_configuration(Bucket="bucket")
    assert len(result["Rules"]) == 1
    with pytest.raises(KeyError):
        assert result["Rules"][0]["Filter"]["And"]["Prefix"]
    assert len(result["Rules"][0]["Filter"]["And"]["Tags"]) == 2
    assert result["Rules"][0]["Filter"]["And"]["Tags"][0]["Key"] == "mytag"
    assert result["Rules"][0]["Filter"]["And"]["Tags"][0]["Value"] == "mytagvalue"
    assert result["Rules"][0]["Filter"]["And"]["Tags"][1]["Key"] == "mytag2"
    assert result["Rules"][0]["Filter"]["And"]["Tags"][1]["Value"] == "mytagvalue2"
    with pytest.raises(KeyError):
        assert result["Rules"][0]["Prefix"]

    # Can't have both filter and prefix:
    lfc["Rules"][0]["Prefix"] = ""
    with pytest.raises(ClientError) as err:
        client.put_bucket_lifecycle_configuration(
            Bucket="bucket", LifecycleConfiguration=lfc
        )
    assert err.value.response["Error"]["Code"] == "MalformedXML"

    lfc["Rules"][0]["Prefix"] = "some/path"
    with pytest.raises(ClientError) as err:
        client.put_bucket_lifecycle_configuration(
            Bucket="bucket", LifecycleConfiguration=lfc
        )
    assert err.value.response["Error"]["Code"] == "MalformedXML"

    # No filters -- just a prefix:
    del lfc["Rules"][0]["Filter"]
    client.put_bucket_lifecycle_configuration(
        Bucket="bucket", LifecycleConfiguration=lfc
    )
    result = client.get_bucket_lifecycle_configuration(Bucket="bucket")
    assert not result["Rules"][0].get("Filter")
    assert result["Rules"][0]["Prefix"] == "some/path"

    # Can't have Tag, Prefix, and And in a filter:
    del lfc["Rules"][0]["Prefix"]
    lfc["Rules"][0]["Filter"] = {
        "Prefix": "some/prefix",
        "Tag": {"Key": "mytag", "Value": "mytagvalue"},
    }
    with pytest.raises(ClientError) as err:
        client.put_bucket_lifecycle_configuration(
            Bucket="bucket", LifecycleConfiguration=lfc
        )
    assert err.value.response["Error"]["Code"] == "MalformedXML"

    lfc["Rules"][0]["Filter"] = {
        "Tag": {"Key": "mytag", "Value": "mytagvalue"},
        "And": {
            "Prefix": "some/prefix",
            "Tags": [
                {"Key": "mytag", "Value": "mytagvalue"},
                {"Key": "mytag2", "Value": "mytagvalue2"},
            ],
        },
    }
    with pytest.raises(ClientError) as err:
        client.put_bucket_lifecycle_configuration(
            Bucket="bucket", LifecycleConfiguration=lfc
        )
    assert err.value.response["Error"]["Code"] == "MalformedXML"

    # Make sure multiple rules work:
    lfc = {
        "Rules": [
            {
                "Expiration": {"Days": 7},
                "ID": "wholebucket",
                "Filter": {"Prefix": ""},
                "Status": "Enabled",
            },
            {
                "Expiration": {"Days": 10},
                "ID": "Tags",
                "Filter": {"Tag": {"Key": "somekey", "Value": "somevalue"}},
                "Status": "Enabled",
            },
        ]
    }
    client.put_bucket_lifecycle_configuration(
        Bucket="bucket", LifecycleConfiguration=lfc
    )
    result = client.get_bucket_lifecycle_configuration(Bucket="bucket")["Rules"]
    assert len(result) == 2
    assert result[0]["ID"] == "wholebucket"
    assert result[1]["ID"] == "Tags"


@mock_aws
def test_lifecycle_with_eodm():
    client = boto3.client("s3", DEFAULT_REGION_NAME)
    client.create_bucket(Bucket="bucket")

    lfc = {
        "Rules": [
            {
                "Expiration": {"ExpiredObjectDeleteMarker": True},
                "ID": "wholebucket",
                "Filter": {"Prefix": ""},
                "Status": "Enabled",
            }
        ]
    }
    client.put_bucket_lifecycle_configuration(
        Bucket="bucket", LifecycleConfiguration=lfc
    )
    result = client.get_bucket_lifecycle_configuration(Bucket="bucket")
    assert len(result["Rules"]) == 1
    assert result["Rules"][0]["Expiration"]["ExpiredObjectDeleteMarker"]

    # Set to False:
    lfc["Rules"][0]["Expiration"]["ExpiredObjectDeleteMarker"] = False
    client.put_bucket_lifecycle_configuration(
        Bucket="bucket", LifecycleConfiguration=lfc
    )
    result = client.get_bucket_lifecycle_configuration(Bucket="bucket")
    assert len(result["Rules"]) == 1
    assert not result["Rules"][0]["Expiration"]["ExpiredObjectDeleteMarker"]

    # With failure:
    lfc["Rules"][0]["Expiration"]["Days"] = 7
    with pytest.raises(ClientError) as err:
        client.put_bucket_lifecycle_configuration(
            Bucket="bucket", LifecycleConfiguration=lfc
        )
    assert err.value.response["Error"]["Code"] == "MalformedXML"
    del lfc["Rules"][0]["Expiration"]["Days"]

    lfc["Rules"][0]["Expiration"]["Date"] = datetime(2015, 1, 1)
    with pytest.raises(ClientError) as err:
        client.put_bucket_lifecycle_configuration(
            Bucket="bucket", LifecycleConfiguration=lfc
        )
    assert err.value.response["Error"]["Code"] == "MalformedXML"


@mock_aws
def test_lifecycle_with_nve():
    client = boto3.client("s3", DEFAULT_REGION_NAME)
    client.create_bucket(Bucket="bucket")

    lfc = {
        "Rules": [
            {
                "NoncurrentVersionExpiration": {"NoncurrentDays": 30},
                "ID": "wholebucket",
                "Filter": {"Prefix": ""},
                "Status": "Enabled",
            }
        ]
    }
    client.put_bucket_lifecycle_configuration(
        Bucket="bucket", LifecycleConfiguration=lfc
    )
    result = client.get_bucket_lifecycle_configuration(Bucket="bucket")
    assert len(result["Rules"]) == 1
    assert result["Rules"][0]["NoncurrentVersionExpiration"]["NoncurrentDays"] == 30

    # Change NoncurrentDays:
    lfc["Rules"][0]["NoncurrentVersionExpiration"]["NoncurrentDays"] = 10
    client.put_bucket_lifecycle_configuration(
        Bucket="bucket", LifecycleConfiguration=lfc
    )
    result = client.get_bucket_lifecycle_configuration(Bucket="bucket")
    assert len(result["Rules"]) == 1
    assert result["Rules"][0]["NoncurrentVersionExpiration"]["NoncurrentDays"] == 10

    # TODO: Add test for failures due to missing children


@mock_aws
def test_lifecycle_with_nvt():
    client = boto3.client("s3", DEFAULT_REGION_NAME)
    client.create_bucket(Bucket="bucket")

    lfc = {
        "Rules": [
            {
                "NoncurrentVersionTransitions": [
                    {"NoncurrentDays": 30, "StorageClass": "ONEZONE_IA"}
                ],
                "ID": "wholebucket",
                "Filter": {"Prefix": ""},
                "Status": "Enabled",
            }
        ]
    }
    client.put_bucket_lifecycle_configuration(
        Bucket="bucket", LifecycleConfiguration=lfc
    )
    result = client.get_bucket_lifecycle_configuration(Bucket="bucket")
    assert len(result["Rules"]) == 1
    assert result["Rules"][0]["NoncurrentVersionTransitions"][0]["NoncurrentDays"] == 30
    assert (
        result["Rules"][0]["NoncurrentVersionTransitions"][0]["StorageClass"]
        == "ONEZONE_IA"
    )

    # Change NoncurrentDays:
    lfc["Rules"][0]["NoncurrentVersionTransitions"][0]["NoncurrentDays"] = 10
    client.put_bucket_lifecycle_configuration(
        Bucket="bucket", LifecycleConfiguration=lfc
    )
    result = client.get_bucket_lifecycle_configuration(Bucket="bucket")
    assert len(result["Rules"]) == 1
    assert result["Rules"][0]["NoncurrentVersionTransitions"][0]["NoncurrentDays"] == 10

    # Change StorageClass:
    lfc["Rules"][0]["NoncurrentVersionTransitions"][0]["StorageClass"] = "GLACIER"
    client.put_bucket_lifecycle_configuration(
        Bucket="bucket", LifecycleConfiguration=lfc
    )
    result = client.get_bucket_lifecycle_configuration(Bucket="bucket")
    assert len(result["Rules"]) == 1
    assert (
        result["Rules"][0]["NoncurrentVersionTransitions"][0]["StorageClass"]
        == "GLACIER"
    )

    # With failures for missing children:
    del lfc["Rules"][0]["NoncurrentVersionTransitions"][0]["NoncurrentDays"]
    with pytest.raises(ClientError) as err:
        client.put_bucket_lifecycle_configuration(
            Bucket="bucket", LifecycleConfiguration=lfc
        )
    assert err.value.response["Error"]["Code"] == "MalformedXML"
    lfc["Rules"][0]["NoncurrentVersionTransitions"][0]["NoncurrentDays"] = 30

    del lfc["Rules"][0]["NoncurrentVersionTransitions"][0]["StorageClass"]
    with pytest.raises(ClientError) as err:
        client.put_bucket_lifecycle_configuration(
            Bucket="bucket", LifecycleConfiguration=lfc
        )
    assert err.value.response["Error"]["Code"] == "MalformedXML"


@mock_aws
def test_lifecycle_with_multiple_nvt():
    client = boto3.client("s3", DEFAULT_REGION_NAME)
    client.create_bucket(Bucket="bucket")

    lfc = {
        "Rules": [
            {
                "NoncurrentVersionTransitions": [
                    {"NoncurrentDays": 30, "StorageClass": "ONEZONE_IA"},
                    {"NoncurrentDays": 50, "StorageClass": "GLACIER"},
                ],
                "ID": "wholebucket",
                "Filter": {"Prefix": ""},
                "Status": "Enabled",
            }
        ]
    }
    client.put_bucket_lifecycle_configuration(
        Bucket="bucket", LifecycleConfiguration=lfc
    )
    result = client.get_bucket_lifecycle_configuration(Bucket="bucket")
    assert len(result["Rules"]) == 1
    assert result["Rules"][0]["NoncurrentVersionTransitions"][0] == {
        "NoncurrentDays": 30,
        "StorageClass": "ONEZONE_IA",
    }
    assert result["Rules"][0]["NoncurrentVersionTransitions"][1] == {
        "NoncurrentDays": 50,
        "StorageClass": "GLACIER",
    }


@mock_aws
def test_lifecycle_with_multiple_transitions():
    client = boto3.client("s3", DEFAULT_REGION_NAME)
    client.create_bucket(Bucket="bucket")

    lfc = {
        "Rules": [
            {
                "Transitions": [
                    {"Days": 30, "StorageClass": "ONEZONE_IA"},
                    {"Days": 50, "StorageClass": "GLACIER"},
                ],
                "ID": "wholebucket",
                "Filter": {"Prefix": ""},
                "Status": "Enabled",
            }
        ]
    }
    client.put_bucket_lifecycle_configuration(
        Bucket="bucket", LifecycleConfiguration=lfc
    )
    result = client.get_bucket_lifecycle_configuration(Bucket="bucket")
    assert len(result["Rules"]) == 1
    assert result["Rules"][0]["Transitions"][0] == {
        "Days": 30,
        "StorageClass": "ONEZONE_IA",
    }
    assert result["Rules"][0]["Transitions"][1] == {
        "Days": 50,
        "StorageClass": "GLACIER",
    }


@mock_aws
def test_lifecycle_with_aimu():
    client = boto3.client("s3", DEFAULT_REGION_NAME)
    client.create_bucket(Bucket="bucket")

    lfc = {
        "Rules": [
            {
                "AbortIncompleteMultipartUpload": {"DaysAfterInitiation": 7},
                "ID": "wholebucket",
                "Filter": {"Prefix": ""},
                "Status": "Enabled",
            }
        ]
    }
    client.put_bucket_lifecycle_configuration(
        Bucket="bucket", LifecycleConfiguration=lfc
    )
    result = client.get_bucket_lifecycle_configuration(Bucket="bucket")
    assert len(result["Rules"]) == 1
    assert (
        result["Rules"][0]["AbortIncompleteMultipartUpload"]["DaysAfterInitiation"] == 7
    )

    # Change DaysAfterInitiation:
    lfc["Rules"][0]["AbortIncompleteMultipartUpload"]["DaysAfterInitiation"] = 30
    client.put_bucket_lifecycle_configuration(
        Bucket="bucket", LifecycleConfiguration=lfc
    )
    result = client.get_bucket_lifecycle_configuration(Bucket="bucket")
    assert len(result["Rules"]) == 1
    assert (
        result["Rules"][0]["AbortIncompleteMultipartUpload"]["DaysAfterInitiation"]
        == 30
    )

    # TODO: Add test for failures due to missing children


@mock_aws
def test_lifecycle_with_glacier_transition_boto3():
    s3_resource = boto3.resource("s3", region_name="us-east-1")
    client = boto3.client("s3", region_name="us-east-1")
    s3_resource.create_bucket(Bucket="foobar")

    client.put_bucket_lifecycle_configuration(
        Bucket="foobar",
        LifecycleConfiguration={
            "Rules": [
                {
                    "ID": "myid",
                    "Prefix": "",
                    "Status": "Enabled",
                    "Transitions": [{"Days": 30, "StorageClass": "GLACIER"}],
                }
            ]
        },
    )

    response = client.get_bucket_lifecycle_configuration(Bucket="foobar")
    assert "Rules" in response
    rules = response["Rules"]
    assert len(rules) == 1
    assert rules[0]["ID"] == "myid"
    transition = rules[0]["Transitions"][0]
    assert transition["Days"] == 30
    assert transition["StorageClass"] == "GLACIER"
    assert "Date" not in transition


@mock_aws
def test_lifecycle_multi_boto3():
    s3_resource = boto3.resource("s3", region_name="us-east-1")
    client = boto3.client("s3", region_name="us-east-1")
    s3_resource.create_bucket(Bucket="foobar")

    date = "2022-10-12T00:00:00.000Z"
    storage_class = "GLACIER"

    client.put_bucket_lifecycle_configuration(
        Bucket="foobar",
        LifecycleConfiguration={
            "Rules": [
                {"ID": "1", "Prefix": "1/", "Status": "Enabled"},
                {
                    "ID": "2",
                    "Prefix": "2/",
                    "Status": "Enabled",
                    "Expiration": {"Days": 2},
                },
                {
                    "ID": "3",
                    "Prefix": "3/",
                    "Status": "Enabled",
                    "Expiration": {"Date": date},
                },
                {
                    "ID": "4",
                    "Prefix": "4/",
                    "Status": "Enabled",
                    "Transitions": [{"Days": 4, "StorageClass": "GLACIER"}],
                },
                {
                    "ID": "5",
                    "Prefix": "5/",
                    "Status": "Enabled",
                    "Transitions": [{"Date": date, "StorageClass": "GLACIER"}],
                },
            ]
        },
    )

    # read the lifecycle back
    rules = client.get_bucket_lifecycle_configuration(Bucket="foobar")["Rules"]

    for rule in rules:
        if rule["ID"] == "1":
            assert rule["Prefix"] == "1/"
            assert "Expiration" not in rule
        elif rule["ID"] == "2":
            assert rule["Prefix"] == "2/"
            assert rule["Expiration"]["Days"] == 2
        elif rule["ID"] == "3":
            assert rule["Prefix"] == "3/"
            assert isinstance(rule["Expiration"]["Date"], datetime)
            assert rule["Expiration"]["Date"].strftime("%Y-%m-%dT%H:%M:%S.000Z") == date
        elif rule["ID"] == "4":
            assert rule["Prefix"] == "4/"
            assert rule["Transitions"][0]["Days"] == 4
            assert rule["Transitions"][0]["StorageClass"] == storage_class
        elif rule["ID"] == "5":
            assert rule["Prefix"] == "5/"
            assert isinstance(rule["Transitions"][0]["Date"], datetime)
            assert (
                rule["Transitions"][0]["Date"].strftime("%Y-%m-%dT%H:%M:%S.000Z")
                == date
            )
            assert rule["Transitions"][0]["StorageClass"] == storage_class
        else:
            assert False, "Invalid rule id"


@mock_aws
def test_lifecycle_delete_boto3():
    s3_resource = boto3.resource("s3", region_name="us-east-1")
    client = boto3.client("s3", region_name="us-east-1")
    s3_resource.create_bucket(Bucket="foobar")

    client.put_bucket_lifecycle_configuration(
        Bucket="foobar",
        LifecycleConfiguration={
            "Rules": [{"ID": "myid", "Prefix": "", "Status": "Enabled"}]
        },
    )

    client.delete_bucket_lifecycle(Bucket="foobar")

    with pytest.raises(ClientError) as ex:
        client.get_bucket_lifecycle_configuration(Bucket="foobar")
    assert ex.value.response["Error"]["Code"] == "NoSuchLifecycleConfiguration"
    assert ex.value.response["Error"]["Message"] == (
        "The lifecycle configuration does not exist"
    )
