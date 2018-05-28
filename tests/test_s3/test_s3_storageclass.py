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


@mock_s3
def test_s3_storage_class_standard():
	client = boto3.client("s3")
	client.create_bucket(Bucket="Bucket")

	# add an object to the bucket with standard storage

	client.put_object(Bucket="Bucket", Key="my_key", Value="my_value")

	D = client.list_objects(Bucket="mybucket")

	(D['Contents'][0]["StorageClass"]).should.equal("STANDARD")

@mock_s3
def test_s3_storage_class_infrequent_access():
	client = boto3.client("s3")
	client.create_bucket(Bucket="Bucket")

	# add an object to the bucket with standard storage

	client.put_object(Bucket="Bucket", Key="my_key_infrequent", Value="my_value_infrequent", StorageClass="STANDARD_IA")

	D = client.list_objects(Bucket="mybucket")

	(D['Contents'][0]["StorageClass"]).should.equal("STANDARD_IA")