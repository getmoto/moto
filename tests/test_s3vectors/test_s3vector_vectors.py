"""Unit tests for s3vectors-supported APIs."""

from uuid import uuid4

import boto3
import pytest
from botocore.exceptions import ClientError

from tests.test_s3vectors import s3vectors_aws_verified

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


def _create_index(bucket_name, client, dimension: int = 1):
    index_name = str(uuid4())
    client.create_index(
        vectorBucketName=bucket_name,
        indexName=index_name,
        dataType="float32",
        dimension=dimension,
        distanceMetric="euclidean",
    )
    return index_name


@s3vectors_aws_verified()
@pytest.mark.aws_verified
def test_put_vectors_by_name(account_id, bucket_name=None):
    client = boto3.client("s3vectors", region_name="us-east-1")

    index_name = _create_index(bucket_name, client)

    client.put_vectors(
        vectorBucketName=bucket_name,
        indexName=index_name,
        vectors=[{"key": "my_first_vector", "data": {"float32": [1.0]}}],
    )

    vectors = client.get_vectors(
        vectorBucketName=bucket_name,
        indexName=index_name,
        keys=["my_first_vector"],
    )["vectors"]
    assert vectors == [{"key": "my_first_vector"}]

    # Get non-existing metadata
    vectors = client.get_vectors(
        vectorBucketName=bucket_name,
        indexName=index_name,
        keys=["my_first_vector"],
        returnMetadata=True,
    )["vectors"]
    assert vectors == [{"key": "my_first_vector", "metadata": {}}]


@s3vectors_aws_verified()
@pytest.mark.aws_verified
def test_put_vectors_by_arn(account_id, bucket_name=None):
    client = boto3.client("s3vectors", region_name="us-east-1")

    index_name = _create_index(bucket_name, client=client)
    index_arn = f"arn:aws:s3vectors:us-east-1:{account_id}:bucket/{bucket_name}/index/{index_name}"

    client.put_vectors(
        indexArn=index_arn,
        vectors=[
            {
                "key": "my_first_vector",
                "data": {"float32": [1.0]},
                "metadata": {"my": "metadata"},
            }
        ],
    )

    # Return plain vectors
    vectors = client.get_vectors(
        indexArn=index_arn,
        keys=["my_first_vector"],
    )["vectors"]
    assert vectors == [{"key": "my_first_vector"}]

    # Return Vector Metadata
    vectors = client.get_vectors(
        indexArn=index_arn,
        keys=["my_first_vector"],
        returnMetadata=True,
    )["vectors"]
    assert vectors == [{"key": "my_first_vector", "metadata": {"my": "metadata"}}]

    # Return Vector Data
    vectors = client.get_vectors(
        indexArn=index_arn,
        keys=["my_first_vector"],
        returnData=True,
    )["vectors"]
    assert vectors == [{"key": "my_first_vector", "data": {"float32": [1.0]}}]


@s3vectors_aws_verified()
@pytest.mark.aws_verified
def test_put_vectors_twice_on_same_key(account_id, bucket_name=None):
    client = boto3.client("s3vectors", region_name="us-east-1")

    index_name = _create_index(bucket_name, client=client)
    index_arn = f"arn:aws:s3vectors:us-east-1:{account_id}:bucket/{bucket_name}/index/{index_name}"

    client.put_vectors(
        indexArn=index_arn,
        vectors=[
            {
                "key": "vector1",
                "data": {"float32": [1.0]},
                "metadata": {"first": "metadata"},
            }
        ],
    )

    # Vector will be completely overwritten if we PUT to the same key
    client.put_vectors(
        indexArn=index_arn,
        vectors=[
            {
                "key": "vector1",
                "data": {"float32": [2.0]},
                "metadata": {"second": "metadata"},
            }
        ],
    )

    vectors = client.get_vectors(
        indexArn=index_arn,
        keys=["vector1"],
        returnMetadata=True,
        returnData=True,
    )["vectors"]
    assert vectors == [
        {
            "key": "vector1",
            "data": {"float32": [2.0]},
            "metadata": {"second": "metadata"},
        }
    ]


@s3vectors_aws_verified()
@pytest.mark.aws_verified
def test_put_vectors_with_large_dimension(account_id, bucket_name=None):
    client = boto3.client("s3vectors", region_name="us-east-1")

    dimension = 100
    index_name = _create_index(bucket_name, client=client, dimension=dimension)

    vector_data = [float(i) for i in range(dimension)]
    client.put_vectors(
        vectorBucketName=bucket_name,
        indexName=index_name,
        vectors=[{"key": "my_first_vector", "data": {"float32": vector_data}}],
    )

    vectors = client.get_vectors(
        vectorBucketName=bucket_name,
        indexName=index_name,
        keys=["my_first_vector"],
        returnData=True,
    )["vectors"]
    assert len(vectors) == 1
    assert vectors[0]["data"]["float32"] == vector_data


@s3vectors_aws_verified()
@pytest.mark.aws_verified
def test_put_vectors_with_wrong_dimension(account_id, bucket_name=None):
    client = boto3.client("s3vectors", region_name="us-east-1")

    index_name = _create_index(bucket_name, client=client, dimension=5)

    with pytest.raises(ClientError) as exc:
        client.put_vectors(
            vectorBucketName=bucket_name,
            indexName=index_name,
            vectors=[{"key": "my_first_vector", "data": {"float32": [1.0]}}],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "Invalid record for key 'my_first_vector': vector must have length 5, but has length 1"
    )


@s3vectors_aws_verified()
@pytest.mark.aws_verified
def test_get_vectors_by_name_and_arn(account_id, bucket_name=None):
    client = boto3.client("s3vectors", region_name="us-east-1")

    index_name = str(uuid4())
    index_arn = f"arn:aws:s3vectors:us-east-1:{account_id}:bucket/{bucket_name}/index/{index_name}"

    with pytest.raises(ClientError) as exc:
        client.get_vectors(
            vectorBucketName=bucket_name,
            indexArn=index_arn,
            indexName=index_name,
            keys=["my_first_vector"],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "Must specify either indexArn or both vectorBucketName and indexName"
    )


@s3vectors_aws_verified()
@pytest.mark.aws_verified
def test_get_vectors_from_unknown_index(account_id, bucket_name=None):
    client = boto3.client("s3vectors", region_name="us-east-1")

    index_name = str(uuid4())

    with pytest.raises(ClientError) as exc:
        client.get_vectors(
            vectorBucketName=bucket_name,
            indexName=index_name,
            keys=["my_first_vector"],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "NotFoundException"
    assert err["Message"] == "The specified index could not be found"


@s3vectors_aws_verified()
@pytest.mark.aws_verified
def test_get_vectors_from_unknown_index_arn(account_id, bucket_name=None):
    client = boto3.client("s3vectors", region_name="us-east-1")

    index_name = str(uuid4())
    index_arn = f"arn:aws:s3vectors:us-east-1:{account_id}:bucket/{bucket_name}/index/{index_name}"

    with pytest.raises(ClientError) as exc:
        client.get_vectors(
            indexArn=index_arn,
            keys=["my_first_vector"],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "NotFoundException"
    assert err["Message"] == "The specified index could not be found"


@s3vectors_aws_verified()
@pytest.mark.aws_verified
def test_put_vectors_by_name_and_arn(account_id, bucket_name=None):
    client = boto3.client("s3vectors", region_name="us-east-1")

    index_name = str(uuid4())
    index_arn = f"arn:aws:s3vectors:us-east-1:{account_id}:bucket/{bucket_name}/index/{index_name}"

    with pytest.raises(ClientError) as exc:
        client.put_vectors(
            vectorBucketName=bucket_name,
            indexArn=index_arn,
            indexName=index_name,
            vectors=[{"key": "my_first_vector", "data": {"float32": [1.0]}}],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "Must specify either indexArn or both vectorBucketName and indexName"
    )


@s3vectors_aws_verified()
@pytest.mark.aws_verified
def test_put_vectors_by_unknown_name(account_id, bucket_name=None):
    client = boto3.client("s3vectors", region_name="us-east-1")

    index_name = str(uuid4())

    with pytest.raises(ClientError) as exc:
        client.put_vectors(
            vectorBucketName=bucket_name,
            indexName=index_name,
            vectors=[{"key": "my_first_vector", "data": {"float32": [1.0]}}],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "NotFoundException"
    assert err["Message"] == "The specified index could not be found"


@s3vectors_aws_verified()
@pytest.mark.aws_verified
def test_put_vectors_by_unknown_arn(account_id, bucket_name=None):
    client = boto3.client("s3vectors", region_name="us-east-1")

    index_name = str(uuid4())
    index_arn = f"arn:aws:s3vectors:us-east-1:{account_id}:bucket/{bucket_name}/index/{index_name}"

    with pytest.raises(ClientError) as exc:
        client.put_vectors(
            indexArn=index_arn,
            vectors=[{"key": "my_first_vector", "data": {"float32": [1.0]}}],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "NotFoundException"
    assert err["Message"] == "The specified index could not be found"


@s3vectors_aws_verified()
@pytest.mark.aws_verified
def test_list_vectors_using_name(account_id, bucket_name=None):
    client = boto3.client("s3vectors", region_name="us-east-1")

    index_name = _create_index(bucket_name, client=client)
    key = "my_first_vector"

    vector_data = [1.0]
    client.put_vectors(
        vectorBucketName=bucket_name,
        indexName=index_name,
        vectors=[
            {"key": key, "data": {"float32": vector_data}, "metadata": {"m": "d"}}
        ],
    )

    vectors = client.list_vectors(vectorBucketName=bucket_name, indexName=index_name)[
        "vectors"
    ]
    assert vectors == [{"key": key}]

    # Return Vector Metadata
    vectors = client.list_vectors(
        vectorBucketName=bucket_name,
        indexName=index_name,
        returnMetadata=True,
    )["vectors"]
    assert vectors == [{"key": key, "metadata": {"m": "d"}}]

    # Return Vector Data
    vectors = client.list_vectors(
        vectorBucketName=bucket_name,
        indexName=index_name,
        returnData=True,
    )["vectors"]
    assert vectors == [{"key": key, "data": {"float32": vector_data}}]


@s3vectors_aws_verified()
@pytest.mark.aws_verified
def test_list_vectors_using_arn(account_id, bucket_name=None):
    client = boto3.client("s3vectors", region_name="us-east-1")

    index_name = _create_index(bucket_name, client=client)
    index_arn = f"arn:aws:s3vectors:us-east-1:{account_id}:bucket/{bucket_name}/index/{index_name}"
    key = "my_first_vector"

    vector_data = [1.0]
    client.put_vectors(
        vectorBucketName=bucket_name,
        indexName=index_name,
        vectors=[
            {"key": key, "data": {"float32": vector_data}, "metadata": {"m": "d"}}
        ],
    )

    vectors = client.list_vectors(indexArn=index_arn)["vectors"]
    assert vectors == [{"key": key}]


@s3vectors_aws_verified()
@pytest.mark.aws_verified
def test_list_vectors_using_name_and_arn(account_id, bucket_name=None):
    client = boto3.client("s3vectors", region_name="us-east-1")

    index_name = _create_index(bucket_name, client=client)
    index_arn = f"arn:aws:s3vectors:us-east-1:{account_id}:bucket/{bucket_name}/index/{index_name}"

    client.put_vectors(
        vectorBucketName=bucket_name,
        indexName=index_name,
        vectors=[{"key": "key", "data": {"float32": [1.0]}, "metadata": {"m": "d"}}],
    )

    with pytest.raises(ClientError) as exc:
        client.list_vectors(vectorBucketName=bucket_name, indexArn=index_arn)
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "Must specify either indexArn or both vectorBucketName and indexName"
    )


@s3vectors_aws_verified()
@pytest.mark.aws_verified
def test_delete_vectors_by_name(account_id, bucket_name=None):
    client = boto3.client("s3vectors", region_name="us-east-1")

    index_name = _create_index(bucket_name, client=client)
    index_arn = f"arn:aws:s3vectors:us-east-1:{account_id}:bucket/{bucket_name}/index/{index_name}"
    key1 = "vector1"
    key2 = "vector2"

    vector_data = [1.0]
    client.put_vectors(
        vectorBucketName=bucket_name,
        indexName=index_name,
        vectors=[
            {"key": key1, "data": {"float32": vector_data}},
            {"key": key2, "data": {"float32": vector_data}},
        ],
    )

    client.delete_vectors(
        vectorBucketName=bucket_name, indexName=index_name, keys=[key2]
    )

    vectors = client.list_vectors(indexArn=index_arn)["vectors"]
    assert vectors == [{"key": key1}]


@s3vectors_aws_verified()
@pytest.mark.aws_verified
def test_delete_vectors_by_arn(account_id, bucket_name=None):
    client = boto3.client("s3vectors", region_name="us-east-1")

    index_name = _create_index(bucket_name, client=client)
    index_arn = f"arn:aws:s3vectors:us-east-1:{account_id}:bucket/{bucket_name}/index/{index_name}"
    key1 = "vector1"
    key2 = "vector2"

    vector_data = [1.0]
    client.put_vectors(
        vectorBucketName=bucket_name,
        indexName=index_name,
        vectors=[
            {"key": key1, "data": {"float32": vector_data}},
            {"key": key2, "data": {"float32": vector_data}},
        ],
    )

    client.delete_vectors(indexArn=index_arn, keys=[key2])

    vectors = client.list_vectors(indexArn=index_arn)["vectors"]
    assert vectors == [{"key": key1}]


@s3vectors_aws_verified()
@pytest.mark.aws_verified
def test_delete_vectors_by_name_and_arn(account_id, bucket_name=None):
    client = boto3.client("s3vectors", region_name="us-east-1")

    index_name = _create_index(bucket_name, client=client)
    index_arn = f"arn:aws:s3vectors:us-east-1:{account_id}:bucket/{bucket_name}/index/{index_name}"
    key2 = "vector2"

    with pytest.raises(ClientError) as exc:
        client.delete_vectors(
            vectorBucketName=bucket_name,
            indexArn=index_arn,
            indexName=index_name,
            keys=[key2],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "Must specify either indexArn or both vectorBucketName and indexName"
    )


@s3vectors_aws_verified()
@pytest.mark.aws_verified
def test_delete_vectors__unknown_key(account_id, bucket_name=None):
    client = boto3.client("s3vectors", region_name="us-east-1")

    index_name = _create_index(bucket_name, client=client)
    index_arn = f"arn:aws:s3vectors:us-east-1:{account_id}:bucket/{bucket_name}/index/{index_name}"
    key2 = "vector2"

    client.delete_vectors(indexArn=index_arn, keys=[key2])
