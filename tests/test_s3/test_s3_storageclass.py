from __future__ import unicode_literals

import boto
import boto3
from boto.exception import S3CreateError, S3ResponseError
from boto.s3.lifecycle import Lifecycle, Transition, Expiration, Rule

import sure  # noqa
from botocore.exceptions import ClientError
from datetime import datetime
from nose.tools import assert_raises

from moto import mock_s3_deprecated, mock_s3


@mock_s3
def test_s3_storage_class_standard():
	s3 = boto3.client("s3")
	s3.create_bucket(Bucket="Bucket")

	# add an object to the bucket with standard storage

	s3.put_object(Bucket="Bucket", Key="my_key", Body="my_value")

	list_of_objects = s3.list_objects(Bucket="Bucket")

	list_objects['Contents'][0]["StorageClass"].should.equal("STANDARD")


@mock_s3
def test_s3_storage_class_infrequent_access():
	s3 = boto3.client("s3")
	s3.create_bucket(Bucket="Bucket")

	# add an object to the bucket with standard storage

	s3.put_object(Bucket="Bucket", Key="my_key_infrequent", Body="my_value_infrequent", StorageClass="STANDARD_IA")

	D = s3.list_objects(Bucket="Bucket")

	(D['Contents'][0]["StorageClass"]).should.equal("STANDARD_IA")

@mock_s3
def test_s3_storage_class_copy():
	s3 = boto3.client("s3")
	s3.create_bucket(Bucket="Bucket")
	s3.put_object(Bucket="Bucket", Key="First_Object", Body="Body", StorageClass="ONEZONE_IA")

	s3.create_bucket(Bucket="Bucket2")
	s3.put_object(Bucket="Bucket2", Key="Second_Object", Body="Body2", StorageClass="STANDARD")

	s3.copy_object(CopySource = {"Bucket": "Bucket", "Key": "First_Object"}, Bucket="Bucket2", Key="Second_Object")

	list_of_copied_objects = client.list_objects(Bucket="Bucket2")

	list_of_copied_objects["Contents"][0]["StorageClass"].should.equal("ONEZONE_IA")

@mock_s3
def test_s3_invalid_storage_class():
	s3 = boto3.client("s3")
	s3.create_bucket(Bucket="Bucket")

	# Try to add an object with an invalid storage class
	with assert_raises(ClientError) as err:
		s3.put_object(Bucket="Bucket", Key="First_Object", Body="Body", StorageClass="STANDARDD")

	e = err.exception
	e.response["Error"]["Code"].should.equal("InvalidStorageClass")
	e.response["Error"]["Message"].should.equal("The storage class you specified is not valid")

	


