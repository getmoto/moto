import boto3
from botocore.exceptions import ClientError
import pytest

from moto import mock_s3


@mock_s3
def test_s3_storage_class_standard():
    s3_client = boto3.client("s3", region_name="us-east-1")
    s3_client.create_bucket(Bucket="Bucket")

    # add an object to the bucket with standard storage

    s3_client.put_object(Bucket="Bucket", Key="my_key", Body="my_value")

    list_of_objects = s3_client.list_objects(Bucket="Bucket")

    assert list_of_objects["Contents"][0]["StorageClass"] == "STANDARD"


@mock_s3
def test_s3_storage_class_infrequent_access():
    s3_client = boto3.client("s3")
    s3_client.create_bucket(
        Bucket="Bucket", CreateBucketConfiguration={"LocationConstraint": "us-west-2"}
    )

    # add an object to the bucket with standard storage

    s3_client.put_object(
        Bucket="Bucket",
        Key="my_key_infrequent",
        Body="my_value_infrequent",
        StorageClass="STANDARD_IA",
    )

    objs = s3_client.list_objects(Bucket="Bucket")

    assert objs["Contents"][0]["StorageClass"] == "STANDARD_IA"


@mock_s3
def test_s3_storage_class_intelligent_tiering():
    s3_client = boto3.client("s3")

    s3_client.create_bucket(
        Bucket="Bucket", CreateBucketConfiguration={"LocationConstraint": "us-east-2"}
    )
    s3_client.put_object(
        Bucket="Bucket",
        Key="my_key_infrequent",
        Body="my_value_infrequent",
        StorageClass="INTELLIGENT_TIERING",
    )

    objects = s3_client.list_objects(Bucket="Bucket")

    assert objects["Contents"][0]["StorageClass"] == "INTELLIGENT_TIERING"


@mock_s3
def test_s3_storage_class_copy():
    s3_client = boto3.client("s3", region_name="us-east-1")
    s3_client.create_bucket(Bucket="Bucket")
    s3_client.put_object(
        Bucket="Bucket", Key="First_Object", Body="Body", StorageClass="STANDARD"
    )

    s3_client.create_bucket(Bucket="Bucket2")
    # second object is originally of storage class REDUCED_REDUNDANCY
    s3_client.put_object(Bucket="Bucket2", Key="Second_Object", Body="Body2")

    s3_client.copy_object(
        CopySource={"Bucket": "Bucket", "Key": "First_Object"},
        Bucket="Bucket2",
        Key="Second_Object",
        StorageClass="ONEZONE_IA",
    )

    list_of_copied_objects = s3_client.list_objects(Bucket="Bucket2")

    # checks that a copied object can be properly copied
    assert list_of_copied_objects["Contents"][0]["StorageClass"] == "ONEZONE_IA"


@mock_s3
def test_s3_invalid_copied_storage_class():
    s3_client = boto3.client("s3", region_name="us-east-1")
    s3_client.create_bucket(Bucket="Bucket")
    s3_client.put_object(
        Bucket="Bucket", Key="First_Object", Body="Body", StorageClass="STANDARD"
    )

    s3_client.create_bucket(Bucket="Bucket2")
    s3_client.put_object(
        Bucket="Bucket2",
        Key="Second_Object",
        Body="Body2",
        StorageClass="REDUCED_REDUNDANCY",
    )

    # Try to copy an object with an invalid storage class
    with pytest.raises(ClientError) as err:
        s3_client.copy_object(
            CopySource={"Bucket": "Bucket", "Key": "First_Object"},
            Bucket="Bucket2",
            Key="Second_Object",
            StorageClass="STANDARD2",
        )

    err_value = err.value
    assert err_value.response["Error"]["Code"] == "InvalidStorageClass"
    assert err_value.response["Error"]["Message"] == (
        "The storage class you specified is not valid"
    )


@mock_s3
def test_s3_invalid_storage_class():
    s3_client = boto3.client("s3")
    s3_client.create_bucket(
        Bucket="Bucket", CreateBucketConfiguration={"LocationConstraint": "us-west-1"}
    )

    # Try to add an object with an invalid storage class
    with pytest.raises(ClientError) as err:
        s3_client.put_object(
            Bucket="Bucket", Key="First_Object", Body="Body", StorageClass="STANDARDD"
        )

    err_value = err.value
    assert err_value.response["Error"]["Code"] == "InvalidStorageClass"
    assert err_value.response["Error"]["Message"] == (
        "The storage class you specified is not valid"
    )


@mock_s3
def test_s3_default_storage_class():
    s3_client = boto3.client("s3")
    s3_client.create_bucket(
        Bucket="Bucket", CreateBucketConfiguration={"LocationConstraint": "us-west-1"}
    )

    s3_client.put_object(Bucket="Bucket", Key="First_Object", Body="Body")

    list_of_objects = s3_client.list_objects(Bucket="Bucket")

    # tests that the default storage class is still STANDARD
    assert list_of_objects["Contents"][0]["StorageClass"] == "STANDARD"


@mock_s3
def test_s3_copy_object_error_for_glacier_storage_class_not_restored():
    s3_client = boto3.client("s3")
    s3_client.create_bucket(
        Bucket="Bucket", CreateBucketConfiguration={"LocationConstraint": "us-west-1"}
    )

    s3_client.put_object(
        Bucket="Bucket", Key="First_Object", Body="Body", StorageClass="GLACIER"
    )

    with pytest.raises(ClientError) as exc:
        s3_client.copy_object(
            CopySource={"Bucket": "Bucket", "Key": "First_Object"},
            Bucket="Bucket",
            Key="Second_Object",
        )

    assert exc.value.response["Error"]["Code"] == "ObjectNotInActiveTierError"


@mock_s3
def test_s3_copy_object_error_for_deep_archive_storage_class_not_restored():
    s3_client = boto3.client("s3")
    s3_client.create_bucket(
        Bucket="Bucket", CreateBucketConfiguration={"LocationConstraint": "us-west-1"}
    )

    s3_client.put_object(
        Bucket="Bucket", Key="First_Object", Body="Body", StorageClass="DEEP_ARCHIVE"
    )

    with pytest.raises(ClientError) as exc:
        s3_client.copy_object(
            CopySource={"Bucket": "Bucket", "Key": "First_Object"},
            Bucket="Bucket",
            Key="Second_Object",
        )

    assert exc.value.response["Error"]["Code"] == "ObjectNotInActiveTierError"


@mock_s3
def test_s3_copy_object_for_glacier_storage_class_restored():
    s3_client = boto3.client("s3", region_name="us-east-1")
    s3_client.create_bucket(Bucket="Bucket")

    s3_client.put_object(
        Bucket="Bucket", Key="First_Object", Body="Body", StorageClass="GLACIER"
    )

    s3_client.create_bucket(Bucket="Bucket2")
    s3_client.restore_object(
        Bucket="Bucket", Key="First_Object", RestoreRequest={"Days": 123}
    )

    s3_client.copy_object(
        CopySource={"Bucket": "Bucket", "Key": "First_Object"},
        Bucket="Bucket2",
        Key="Second_Object",
    )

    list_of_copied_objects = s3_client.list_objects(Bucket="Bucket2")
    # checks that copy of restored Glacier object has STANDARD storage class
    assert list_of_copied_objects["Contents"][0]["StorageClass"] == "STANDARD"
    # checks that metadata of copy has no Restore property
    assert not hasattr(
        s3_client.head_object(Bucket="Bucket2", Key="Second_Object"), "Restore"
    )


@mock_s3
def test_s3_copy_object_for_deep_archive_storage_class_restored():
    s3_client = boto3.client("s3", region_name="us-east-1")
    s3_client.create_bucket(Bucket="Bucket")

    s3_client.put_object(
        Bucket="Bucket", Key="First_Object", Body="Body", StorageClass="DEEP_ARCHIVE"
    )

    with pytest.raises(ClientError) as exc:
        s3_client.get_object(Bucket="Bucket", Key="First_Object")
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidObjectState"
    assert err["Message"] == (
        "The operation is not valid for the object's storage class"
    )
    assert err["StorageClass"] == "DEEP_ARCHIVE"

    s3_client.create_bucket(Bucket="Bucket2")
    s3_client.restore_object(
        Bucket="Bucket", Key="First_Object", RestoreRequest={"Days": 123}
    )
    s3_client.get_object(Bucket="Bucket", Key="First_Object")

    s3_client.copy_object(
        CopySource={"Bucket": "Bucket", "Key": "First_Object"},
        Bucket="Bucket2",
        Key="Second_Object",
    )

    list_of_copied_objects = s3_client.list_objects(Bucket="Bucket2")
    # checks that copy of restored Glacier object has STANDARD storage class
    assert list_of_copied_objects["Contents"][0]["StorageClass"] == "STANDARD"
    # checks that metadata of copy has no Restore property
    assert not hasattr(
        s3_client.head_object(Bucket="Bucket2", Key="Second_Object"), "Restore"
    )


@mock_s3
def test_s3_get_object_from_glacier():
    s3_client = boto3.client("s3", region_name="us-east-1")
    bucket_name = "tests3getobjectfromglacier"
    s3_client.create_bucket(Bucket=bucket_name)

    s3_client.put_object(
        Bucket=bucket_name, Key="test.txt", Body="contents", StorageClass="GLACIER"
    )
    with pytest.raises(ClientError) as exc:
        s3_client.get_object(Bucket=bucket_name, Key="test.txt")
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidObjectState"
    assert err["Message"] == (
        "The operation is not valid for the object's storage class"
    )
    assert err["StorageClass"] == "GLACIER"
