from __future__ import unicode_literals

import boto
import boto3
from boto.exception import S3ResponseError
from boto.s3.lifecycle import Lifecycle, Transition, Expiration, Rule

import sure  # noqa
from botocore.exceptions import ClientError
from datetime import datetime
import pytest

from moto import mock_s3_deprecated, mock_s3


@mock_s3_deprecated
def test_lifecycle_create():
    conn = boto.s3.connect_to_region("us-west-1")
    bucket = conn.create_bucket("foobar", location="us-west-1")

    lifecycle = Lifecycle()
    lifecycle.add_rule("myid", "", "Enabled", 30)
    bucket.configure_lifecycle(lifecycle)
    response = bucket.get_lifecycle_config()
    len(response).should.equal(1)
    lifecycle = response[0]
    lifecycle.id.should.equal("myid")
    lifecycle.prefix.should.equal("")
    lifecycle.status.should.equal("Enabled")
    list(lifecycle.transition).should.equal([])


@mock_s3
def test_lifecycle_with_filters():
    client = boto3.client("s3")
    client.create_bucket(
        Bucket="bucket", CreateBucketConfiguration={"LocationConstraint": "us-west-1"}
    )

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


@mock_s3
def test_lifecycle_with_eodm():
    client = boto3.client("s3")
    client.create_bucket(
        Bucket="bucket", CreateBucketConfiguration={"LocationConstraint": "us-west-1"}
    )

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


@mock_s3
def test_lifecycle_with_nve():
    client = boto3.client("s3")
    client.create_bucket(
        Bucket="bucket", CreateBucketConfiguration={"LocationConstraint": "us-west-1"}
    )

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


@mock_s3
def test_lifecycle_with_nvt():
    client = boto3.client("s3")
    client.create_bucket(
        Bucket="bucket", CreateBucketConfiguration={"LocationConstraint": "us-west-1"}
    )

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


@mock_s3
def test_lifecycle_with_aimu():
    client = boto3.client("s3")
    client.create_bucket(
        Bucket="bucket", CreateBucketConfiguration={"LocationConstraint": "us-west-1"}
    )

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


@mock_s3_deprecated
def test_lifecycle_with_glacier_transition():
    conn = boto.s3.connect_to_region("us-west-1")
    bucket = conn.create_bucket("foobar", location="us-west-1")

    lifecycle = Lifecycle()
    transition = Transition(days=30, storage_class="GLACIER")
    rule = Rule(
        "myid", prefix="", status="Enabled", expiration=None, transition=transition
    )
    lifecycle.append(rule)
    bucket.configure_lifecycle(lifecycle)
    response = bucket.get_lifecycle_config()
    transition = response[0].transition
    transition.days.should.equal(30)
    transition.storage_class.should.equal("GLACIER")
    transition.date.should.equal(None)


@mock_s3_deprecated
def test_lifecycle_multi():
    conn = boto.s3.connect_to_region("us-west-1")
    bucket = conn.create_bucket("foobar", location="us-west-1")

    date = "2022-10-12T00:00:00.000Z"
    sc = "GLACIER"
    lifecycle = Lifecycle()
    lifecycle.add_rule("1", "1/", "Enabled", 1)
    lifecycle.add_rule("2", "2/", "Enabled", Expiration(days=2))
    lifecycle.add_rule("3", "3/", "Enabled", Expiration(date=date))
    lifecycle.add_rule("4", "4/", "Enabled", None, Transition(days=4, storage_class=sc))
    lifecycle.add_rule(
        "5", "5/", "Enabled", None, Transition(date=date, storage_class=sc)
    )

    bucket.configure_lifecycle(lifecycle)
    # read the lifecycle back
    rules = bucket.get_lifecycle_config()

    for rule in rules:
        if rule.id == "1":
            rule.prefix.should.equal("1/")
            rule.expiration.days.should.equal(1)
        elif rule.id == "2":
            rule.prefix.should.equal("2/")
            rule.expiration.days.should.equal(2)
        elif rule.id == "3":
            rule.prefix.should.equal("3/")
            rule.expiration.date.should.equal(date)
        elif rule.id == "4":
            rule.prefix.should.equal("4/")
            rule.transition.days.should.equal(4)
            rule.transition.storage_class.should.equal(sc)
        elif rule.id == "5":
            rule.prefix.should.equal("5/")
            rule.transition.date.should.equal(date)
            rule.transition.storage_class.should.equal(sc)
        else:
            assert False, "Invalid rule id"


@mock_s3_deprecated
def test_lifecycle_delete():
    conn = boto.s3.connect_to_region("us-west-1")
    bucket = conn.create_bucket("foobar", location="us-west-1")

    lifecycle = Lifecycle()
    lifecycle.add_rule(expiration=30)
    bucket.configure_lifecycle(lifecycle)
    response = bucket.get_lifecycle_config()
    response.should.have.length_of(1)

    bucket.delete_lifecycle_configuration()
    bucket.get_lifecycle_config.when.called_with().should.throw(S3ResponseError)
