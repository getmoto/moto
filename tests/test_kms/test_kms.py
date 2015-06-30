from __future__ import unicode_literals

import boto.kms
from boto.exception import JSONResponseError
import sure  # noqa

from moto import mock_kms


@mock_kms
def test_create_key():
    conn = boto.kms.connect_to_region("us-west-2")

    key = conn.create_key(policy="my policy", description="my key", key_usage='ENCRYPT_DECRYPT')

    key['KeyMetadata']['Description'].should.equal("my key")
    key['KeyMetadata']['KeyUsage'].should.equal("ENCRYPT_DECRYPT")
    key['KeyMetadata']['Enabled'].should.equal(True)


@mock_kms
def test_describe_key():
    conn = boto.kms.connect_to_region("us-west-2")
    key = conn.create_key(policy="my policy", description="my key", key_usage='ENCRYPT_DECRYPT')
    key_id = key['KeyMetadata']['KeyId']

    key = conn.describe_key(key_id)
    key['KeyMetadata']['Description'].should.equal("my key")
    key['KeyMetadata']['KeyUsage'].should.equal("ENCRYPT_DECRYPT")


@mock_kms
def test_describe_missing_key():
    conn = boto.kms.connect_to_region("us-west-2")
    conn.describe_key.when.called_with("not-a-key").should.throw(JSONResponseError)


@mock_kms
def test_list_keys():
    conn = boto.kms.connect_to_region("us-west-2")

    conn.create_key(policy="my policy", description="my key1", key_usage='ENCRYPT_DECRYPT')
    conn.create_key(policy="my policy", description="my key2", key_usage='ENCRYPT_DECRYPT')

    keys = conn.list_keys()
    keys['Keys'].should.have.length_of(2)
