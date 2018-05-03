from __future__ import unicode_literals

import boto
import boto3
from boto.exception import S3ResponseError
from boto.s3.lifecycle import Lifecycle, Transition, Expiration, Rule

import sure  # noqa
from botocore.exceptions import ClientError
from datetime import datetime
from nose.tools import assert_raises

from moto import mock_s3_deprecated, mock_s3


@mock_s3_deprecated
def test_lifecycle_create():
    conn = boto.s3.connect_to_region("us-west-1")
    bucket = conn.create_bucket("foobar")

    lifecycle = Lifecycle()
    lifecycle.add_rule('myid', '', 'Enabled', 30)
    bucket.configure_lifecycle(lifecycle)
    response = bucket.get_lifecycle_config()
    len(response).should.equal(1)
    lifecycle = response[0]
    lifecycle.id.should.equal('myid')
    lifecycle.prefix.should.equal('')
    lifecycle.status.should.equal('Enabled')
    list(lifecycle.transition).should.equal([])


@mock_s3
def test_lifecycle_with_filters():
    client = boto3.client("s3")
    client.create_bucket(Bucket="bucket")

    # Create a lifecycle rule with a Filter (no tags):
    lfc = {
        "Rules": [
            {
                "Expiration": {
                    "Days": 7
                },
                "ID": "wholebucket",
                "Filter": {
                    "Prefix": ""
                },
                "Status": "Enabled"
            }
        ]
    }
    client.put_bucket_lifecycle_configuration(Bucket="bucket", LifecycleConfiguration=lfc)
    result = client.get_bucket_lifecycle_configuration(Bucket="bucket")
    assert len(result["Rules"]) == 1
    assert result["Rules"][0]["Filter"]["Prefix"] == ''
    assert not result["Rules"][0]["Filter"].get("And")
    assert not result["Rules"][0]["Filter"].get("Tag")
    with assert_raises(KeyError):
        assert result["Rules"][0]["Prefix"]

    # With a tag:
    lfc["Rules"][0]["Filter"]["Tag"] = {
        "Key": "mytag",
        "Value": "mytagvalue"
    }
    client.put_bucket_lifecycle_configuration(Bucket="bucket", LifecycleConfiguration=lfc)
    result = client.get_bucket_lifecycle_configuration(Bucket="bucket")
    assert len(result["Rules"]) == 1
    assert result["Rules"][0]["Filter"]["Prefix"] == ''
    assert not result["Rules"][0]["Filter"].get("And")
    assert result["Rules"][0]["Filter"]["Tag"]["Key"] == "mytag"
    assert result["Rules"][0]["Filter"]["Tag"]["Value"] == "mytagvalue"
    with assert_raises(KeyError):
        assert result["Rules"][0]["Prefix"]

    # With And (single tag):
    lfc["Rules"][0]["Filter"]["And"] = {
        "Prefix": "some/prefix",
        "Tags": [
            {
                "Key": "mytag",
                "Value": "mytagvalue"
            }
        ]
    }
    client.put_bucket_lifecycle_configuration(Bucket="bucket", LifecycleConfiguration=lfc)
    result = client.get_bucket_lifecycle_configuration(Bucket="bucket")
    assert len(result["Rules"]) == 1
    assert result["Rules"][0]["Filter"]["Prefix"] == ""
    assert result["Rules"][0]["Filter"]["And"]["Prefix"] == "some/prefix"
    assert len(result["Rules"][0]["Filter"]["And"]["Tags"]) == 1
    assert result["Rules"][0]["Filter"]["And"]["Tags"][0]["Key"] == "mytag"
    assert result["Rules"][0]["Filter"]["And"]["Tags"][0]["Value"] == "mytagvalue"
    assert result["Rules"][0]["Filter"]["Tag"]["Key"] == "mytag"
    assert result["Rules"][0]["Filter"]["Tag"]["Value"] == "mytagvalue"
    with assert_raises(KeyError):
        assert result["Rules"][0]["Prefix"]

    # With multiple And tags:
    lfc["Rules"][0]["Filter"]["And"] = {
        "Prefix": "some/prefix",
        "Tags": [
            {
                "Key": "mytag",
                "Value": "mytagvalue"
            },
            {
                "Key": "mytag2",
                "Value": "mytagvalue2"
            }
        ]
    }
    client.put_bucket_lifecycle_configuration(Bucket="bucket", LifecycleConfiguration=lfc)
    result = client.get_bucket_lifecycle_configuration(Bucket="bucket")
    assert len(result["Rules"]) == 1
    assert result["Rules"][0]["Filter"]["Prefix"] == ""
    assert result["Rules"][0]["Filter"]["And"]["Prefix"] == "some/prefix"
    assert len(result["Rules"][0]["Filter"]["And"]["Tags"]) == 2
    assert result["Rules"][0]["Filter"]["And"]["Tags"][0]["Key"] == "mytag"
    assert result["Rules"][0]["Filter"]["And"]["Tags"][0]["Value"] == "mytagvalue"
    assert result["Rules"][0]["Filter"]["Tag"]["Key"] == "mytag"
    assert result["Rules"][0]["Filter"]["Tag"]["Value"] == "mytagvalue"
    assert result["Rules"][0]["Filter"]["And"]["Tags"][1]["Key"] == "mytag2"
    assert result["Rules"][0]["Filter"]["And"]["Tags"][1]["Value"] == "mytagvalue2"
    assert result["Rules"][0]["Filter"]["Tag"]["Key"] == "mytag"
    assert result["Rules"][0]["Filter"]["Tag"]["Value"] == "mytagvalue"
    with assert_raises(KeyError):
        assert result["Rules"][0]["Prefix"]

    # Can't have both filter and prefix:
    lfc["Rules"][0]["Prefix"] = ''
    with assert_raises(ClientError) as err:
        client.put_bucket_lifecycle_configuration(Bucket="bucket", LifecycleConfiguration=lfc)
    assert err.exception.response["Error"]["Code"] == "MalformedXML"

    lfc["Rules"][0]["Prefix"] = 'some/path'
    with assert_raises(ClientError) as err:
        client.put_bucket_lifecycle_configuration(Bucket="bucket", LifecycleConfiguration=lfc)
    assert err.exception.response["Error"]["Code"] == "MalformedXML"

    # No filters -- just a prefix:
    del lfc["Rules"][0]["Filter"]
    client.put_bucket_lifecycle_configuration(Bucket="bucket", LifecycleConfiguration=lfc)
    result = client.get_bucket_lifecycle_configuration(Bucket="bucket")
    assert not result["Rules"][0].get("Filter")
    assert result["Rules"][0]["Prefix"] == "some/path"


@mock_s3
def test_lifecycle_with_eodm():
    client = boto3.client("s3")
    client.create_bucket(Bucket="bucket")

    lfc = {
        "Rules": [
            {
                "Expiration": {
                    "ExpiredObjectDeleteMarker": True
                },
                "ID": "wholebucket",
                "Filter": {
                    "Prefix": ""
                },
                "Status": "Enabled"
            }
        ]
    }
    client.put_bucket_lifecycle_configuration(Bucket="bucket", LifecycleConfiguration=lfc)
    result = client.get_bucket_lifecycle_configuration(Bucket="bucket")
    assert len(result["Rules"]) == 1
    assert result["Rules"][0]["Expiration"]["ExpiredObjectDeleteMarker"]

    # Set to False:
    lfc["Rules"][0]["Expiration"]["ExpiredObjectDeleteMarker"] = False
    client.put_bucket_lifecycle_configuration(Bucket="bucket", LifecycleConfiguration=lfc)
    result = client.get_bucket_lifecycle_configuration(Bucket="bucket")
    assert len(result["Rules"]) == 1
    assert not result["Rules"][0]["Expiration"]["ExpiredObjectDeleteMarker"]

    # With failure:
    lfc["Rules"][0]["Expiration"]["Days"] = 7
    with assert_raises(ClientError) as err:
        client.put_bucket_lifecycle_configuration(Bucket="bucket", LifecycleConfiguration=lfc)
    assert err.exception.response["Error"]["Code"] == "MalformedXML"
    del lfc["Rules"][0]["Expiration"]["Days"]

    lfc["Rules"][0]["Expiration"]["Date"] = datetime(2015, 1, 1)
    with assert_raises(ClientError) as err:
        client.put_bucket_lifecycle_configuration(Bucket="bucket", LifecycleConfiguration=lfc)
    assert err.exception.response["Error"]["Code"] == "MalformedXML"


@mock_s3_deprecated
def test_lifecycle_with_glacier_transition():
    conn = boto.s3.connect_to_region("us-west-1")
    bucket = conn.create_bucket("foobar")

    lifecycle = Lifecycle()
    transition = Transition(days=30, storage_class='GLACIER')
    rule = Rule('myid', prefix='', status='Enabled', expiration=None,
                transition=transition)
    lifecycle.append(rule)
    bucket.configure_lifecycle(lifecycle)
    response = bucket.get_lifecycle_config()
    transition = response[0].transition
    transition.days.should.equal(30)
    transition.storage_class.should.equal('GLACIER')
    transition.date.should.equal(None)


@mock_s3_deprecated
def test_lifecycle_multi():
    conn = boto.s3.connect_to_region("us-west-1")
    bucket = conn.create_bucket("foobar")

    date = '2022-10-12T00:00:00.000Z'
    sc = 'GLACIER'
    lifecycle = Lifecycle()
    lifecycle.add_rule("1", "1/", "Enabled", 1)
    lifecycle.add_rule("2", "2/", "Enabled", Expiration(days=2))
    lifecycle.add_rule("3", "3/", "Enabled", Expiration(date=date))
    lifecycle.add_rule("4", "4/", "Enabled", None,
                       Transition(days=4, storage_class=sc))
    lifecycle.add_rule("5", "5/", "Enabled", None,
                       Transition(date=date, storage_class=sc))

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
    bucket = conn.create_bucket("foobar")

    lifecycle = Lifecycle()
    lifecycle.add_rule(expiration=30)
    bucket.configure_lifecycle(lifecycle)
    response = bucket.get_lifecycle_config()
    response.should.have.length_of(1)

    bucket.delete_lifecycle_configuration()
    bucket.get_lifecycle_config.when.called_with().should.throw(S3ResponseError)
