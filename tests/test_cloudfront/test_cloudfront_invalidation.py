import boto3
import pytest
from botocore.errorfactory import ClientError

from moto import mock_aws

from . import cloudfront_test_scaffolding as scaffold


@mock_aws
def test_create_invalidation_with_single_path():
    client = boto3.client("cloudfront", region_name="us-west-1")
    config = scaffold.example_distribution_config("ref")
    resp = client.create_distribution(DistributionConfig=config)
    dist_id = resp["Distribution"]["Id"]

    resp = client.create_invalidation(
        DistributionId=dist_id,
        InvalidationBatch={
            "Paths": {"Quantity": 1, "Items": ["/path1"]},
            "CallerReference": "ref2",
        },
    )

    assert "Location" in resp
    assert "Invalidation" in resp

    assert "Id" in resp["Invalidation"]
    assert resp["Invalidation"]["Status"] == "COMPLETED"
    assert "CreateTime" in resp["Invalidation"]
    assert resp["Invalidation"]["InvalidationBatch"] == {
        "Paths": {"Quantity": 1, "Items": ["/path1"]},
        "CallerReference": "ref2",
    }


@mock_aws
def test_create_invalidation_with_multiple_paths():
    client = boto3.client("cloudfront", region_name="us-west-1")
    config = scaffold.example_distribution_config("ref")
    resp = client.create_distribution(DistributionConfig=config)
    dist_id = resp["Distribution"]["Id"]

    resp = client.create_invalidation(
        DistributionId=dist_id,
        InvalidationBatch={
            "Paths": {"Quantity": 2, "Items": ["/path1", "/path2"]},
            "CallerReference": "ref2",
        },
    )

    assert "Location" in resp
    assert "Invalidation" in resp

    assert "Id" in resp["Invalidation"]
    assert resp["Invalidation"]["Status"] == "COMPLETED"
    assert "CreateTime" in resp["Invalidation"]
    assert resp["Invalidation"]["InvalidationBatch"] == {
        "Paths": {"Quantity": 2, "Items": ["/path1", "/path2"]},
        "CallerReference": "ref2",
    }


@mock_aws
def test_list_invalidations():
    client = boto3.client("cloudfront", region_name="us-west-1")
    config = scaffold.example_distribution_config("ref")
    resp = client.create_distribution(DistributionConfig=config)
    dist_id = resp["Distribution"]["Id"]
    resp = client.create_invalidation(
        DistributionId=dist_id,
        InvalidationBatch={
            "Paths": {"Quantity": 2, "Items": ["/path1", "/path2"]},
            "CallerReference": "ref2",
        },
    )
    invalidation_id = resp["Invalidation"]["Id"]

    resp = client.list_invalidations(DistributionId=dist_id)

    assert "NextMarker" not in resp["InvalidationList"]
    assert resp["InvalidationList"]["MaxItems"] == 100
    assert resp["InvalidationList"]["IsTruncated"] is False
    assert resp["InvalidationList"]["Quantity"] == 1
    assert len(resp["InvalidationList"]["Items"]) == 1
    assert resp["InvalidationList"]["Items"][0]["Id"] == invalidation_id
    assert "CreateTime" in resp["InvalidationList"]["Items"][0]
    assert resp["InvalidationList"]["Items"][0]["Status"] == "COMPLETED"


@mock_aws
def test_list_invalidations__no_entries():
    client = boto3.client("cloudfront", region_name="us-west-1")

    resp = client.list_invalidations(DistributionId="SPAM")

    assert "NextMarker" not in resp["InvalidationList"]
    assert resp["InvalidationList"]["MaxItems"] == 100
    assert resp["InvalidationList"]["IsTruncated"] is False
    assert resp["InvalidationList"]["Quantity"] == 0
    assert "Items" not in resp["InvalidationList"]


@mock_aws
def test_get_invalidation():
    client = boto3.client("cloudfront", region_name="us-west-1")
    config = scaffold.example_distribution_config("ref")
    resp = client.create_distribution(DistributionConfig=config)
    dist_id = resp["Distribution"]["Id"]

    createResp = client.create_invalidation(
        DistributionId=dist_id,
        InvalidationBatch={
            "Paths": {"Quantity": 1, "Items": ["/path1"]},
            "CallerReference": "ref2",
        },
    )
    existed = createResp["Invalidation"]
    resp = client.get_invalidation(DistributionId=dist_id, Id=existed["Id"])
    assert "Invalidation" in resp
    returned = resp["Invalidation"]
    assert returned["Id"] == existed["Id"]
    assert returned["Status"] == existed["Status"]
    assert returned["CreateTime"] == existed["CreateTime"]
    assert returned["InvalidationBatch"] == existed["InvalidationBatch"]


@mock_aws
def test_get_invalidation_dist_not_found():
    client = boto3.client("cloudfront", region_name="us-west-1")

    with pytest.raises(ClientError) as error:
        client.get_invalidation(DistributionId="notfound", Id="notfound")
    assert "NoSuchDistribution" in error.__str__()


@mock_aws
def test_get_invalidation_id_not_found():
    client = boto3.client("cloudfront", region_name="us-west-1")
    config = scaffold.example_distribution_config("ref")
    resp = client.create_distribution(DistributionConfig=config)
    dist_id = resp["Distribution"]["Id"]

    with pytest.raises(ClientError) as error:
        client.get_invalidation(DistributionId=dist_id, Id="notfound")
    assert "NoSuchDistribution" not in str(error)
    assert "NoSuchInvalidation" in str(error)
