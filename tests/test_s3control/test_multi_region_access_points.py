import json
import re

import boto3
import pytest
from botocore.client import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID


@mock_aws
def test_create_multi_region_access_point():
    client = boto3.client("s3control", region_name="us-east-1")
    s3_client = boto3.client("s3", region_name="us-east-1")
    s3_west = boto3.client("s3", region_name="us-west-2")

    # Create buckets in different regions
    bucket1 = "test-bucket-us-east-1"
    bucket2 = "test-bucket-us-west-2"
    s3_client.create_bucket(Bucket=bucket1)
    s3_west.create_bucket(
        Bucket=bucket2, CreateBucketConfiguration={"LocationConstraint": "us-west-2"}
    )

    # Create multi-region access point
    response = client.create_multi_region_access_point(
        AccountId=ACCOUNT_ID,
        ClientToken="test-token-1",
        Details={
            "Name": "my-mrap",
            "PublicAccessBlock": {
                "BlockPublicAcls": True,
                "IgnorePublicAcls": True,
                "BlockPublicPolicy": False,
                "RestrictPublicBuckets": False,
            },
            "Regions": [{"Bucket": bucket1}, {"Bucket": bucket2}],
        },
    )

    assert "RequestTokenARN" in response
    # FIXED: Match against us-east-1 because client is in us-east-1
    assert re.match(
        r"arn:aws:s3:us-east-1:\d+:async-request/mrap/createmultiregionaccesspoint/[a-z0-9]+",
        response["RequestTokenARN"],
    )


@mock_aws
def test_create_multi_region_access_point_duplicate_name():
    client = boto3.client("s3control", region_name="us-east-1")
    s3_client = boto3.client("s3", region_name="us-east-1")

    bucket = "test-bucket"
    s3_client.create_bucket(Bucket=bucket)

    # Create first MRAP
    client.create_multi_region_access_point(
        AccountId=ACCOUNT_ID,
        ClientToken="test-token-1",
        Details={"Name": "duplicate-mrap", "Regions": [{"Bucket": bucket}]},
    )

    # Try to create second MRAP with same name
    with pytest.raises(ClientError) as exc:
        client.create_multi_region_access_point(
            AccountId=ACCOUNT_ID,
            ClientToken="test-token-2",
            Details={"Name": "duplicate-mrap", "Regions": [{"Bucket": bucket}]},
        )

    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidRequest"
    assert "already exists" in err["Message"]


@mock_aws
def test_describe_multi_region_access_point_operation():
    client = boto3.client("s3control", region_name="us-east-1")
    s3_client = boto3.client("s3", region_name="us-east-1")

    bucket = "test-bucket"
    s3_client.create_bucket(Bucket=bucket)

    # Create MRAP
    create_response = client.create_multi_region_access_point(
        AccountId=ACCOUNT_ID,
        ClientToken="test-token",
        Details={"Name": "test-mrap", "Regions": [{"Bucket": bucket}]},
    )

    request_token = create_response["RequestTokenARN"]

    # Describe the operation
    response = client.describe_multi_region_access_point_operation(
        AccountId=ACCOUNT_ID, RequestTokenARN=request_token
    )

    assert response["AsyncOperation"]["RequestTokenARN"] == request_token
    assert response["AsyncOperation"]["RequestStatus"] == "SUCCEEDED"
    assert "CreationTime" in response["AsyncOperation"]
    assert response["AsyncOperation"]["Operation"] == "CreateMultiRegionAccessPoint"
    # The MRAP name is in RequestParameters, not ResponseDetails
    assert (
        response["AsyncOperation"]["RequestParameters"][
            "CreateMultiRegionAccessPointRequest"
        ]["Name"]
        == "test-mrap"
    )
    # ResponseDetails contains per-region status
    regions = response["AsyncOperation"]["ResponseDetails"][
        "MultiRegionAccessPointDetails"
    ]["Regions"]
    assert len(regions) == 1
    assert regions[0]["RequestStatus"] == "SUCCEEDED"


@mock_aws
def test_describe_multi_region_access_point_operation_not_found():
    client = boto3.client("s3control", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        client.describe_multi_region_access_point_operation(
            AccountId=ACCOUNT_ID,
            RequestTokenARN="arn:aws:s3:us-east-1:123456789012:async-request/mrap/invalid/token",
        )

    err = exc.value.response["Error"]
    assert err["Code"] == "NoSuchAsyncRequest"


@mock_aws
def test_get_multi_region_access_point():
    client = boto3.client("s3control", region_name="us-east-1")
    s3_client = boto3.client("s3", region_name="us-east-1")

    bucket = "test-bucket"
    s3_client.create_bucket(Bucket=bucket)

    # Create MRAP
    client.create_multi_region_access_point(
        AccountId=ACCOUNT_ID,
        ClientToken="test-token",
        Details={
            "Name": "test-mrap-get",
            "PublicAccessBlock": {
                "BlockPublicAcls": False,
                "IgnorePublicAcls": False,
                "BlockPublicPolicy": True,
                "RestrictPublicBuckets": True,
            },
            "Regions": [{"Bucket": bucket}],
        },
    )

    # Get MRAP details
    response = client.get_multi_region_access_point(
        AccountId=ACCOUNT_ID, Name="test-mrap-get"
    )

    assert response["AccessPoint"]["Name"] == "test-mrap-get"
    assert "Alias" in response["AccessPoint"]
    assert "CreatedAt" in response["AccessPoint"]
    assert response["AccessPoint"]["Status"] == "READY"
    assert response["AccessPoint"]["PublicAccessBlock"] == {
        "BlockPublicAcls": False,
        "IgnorePublicAcls": False,
        "BlockPublicPolicy": True,
        "RestrictPublicBuckets": True,
    }
    # We expect us-east-1 since that's where we created the bucket
    assert response["AccessPoint"]["Regions"][0]["Region"] == "us-east-1"


@mock_aws
def test_get_multi_region_access_point_not_found():
    client = boto3.client("s3control", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        client.get_multi_region_access_point(
            AccountId=ACCOUNT_ID, Name="non-existent-mrap"
        )

    err = exc.value.response["Error"]
    assert err["Code"] == "NoSuchMultiRegionAccessPoint"
    assert "does not exist" in err["Message"]


@mock_aws
def test_list_multi_region_access_points():
    client = boto3.client("s3control", region_name="us-east-1")
    s3_client = boto3.client("s3", region_name="us-east-1")

    # Initially empty
    response = client.list_multi_region_access_points(AccountId=ACCOUNT_ID)
    assert response["AccessPoints"] == []

    # Create multiple MRAPs
    for i in range(3):
        bucket = f"test-bucket-{i}"
        s3_client.create_bucket(Bucket=bucket)

        client.create_multi_region_access_point(
            AccountId=ACCOUNT_ID,
            ClientToken=f"test-token-{i}",
            Details={"Name": f"mrap-{i}", "Regions": [{"Bucket": bucket}]},
        )

    # List all MRAPs
    response = client.list_multi_region_access_points(AccountId=ACCOUNT_ID)

    assert len(response["AccessPoints"]) == 3
    mrap_names = {ap["Name"] for ap in response["AccessPoints"]}
    assert mrap_names == {"mrap-0", "mrap-1", "mrap-2"}

    for ap in response["AccessPoints"]:
        assert "Alias" in ap
        assert "CreatedAt" in ap
        assert ap["Status"] == "READY"


@mock_aws
def test_list_multi_region_access_points_pagination():
    client = boto3.client("s3control", region_name="us-east-1")
    s3_client = boto3.client("s3", region_name="us-east-1")

    # Create 5 MRAPs
    for i in range(5):
        bucket = f"test-bucket-{i}"
        s3_client.create_bucket(Bucket=bucket)

        client.create_multi_region_access_point(
            AccountId=ACCOUNT_ID,
            ClientToken=f"test-token-{i}",
            Details={"Name": f"mrap-{i}", "Regions": [{"Bucket": bucket}]},
        )

    # List with pagination
    response = client.list_multi_region_access_points(
        AccountId=ACCOUNT_ID, MaxResults=3
    )

    assert len(response["AccessPoints"]) == 3
    assert "NextToken" in response

    # Get next page
    response2 = client.list_multi_region_access_points(
        AccountId=ACCOUNT_ID, NextToken=response["NextToken"]
    )

    assert len(response2["AccessPoints"]) == 2
    assert "NextToken" not in response2


@mock_aws
def test_put_multi_region_access_point_policy():
    client = boto3.client("s3control", region_name="us-east-1")
    s3_client = boto3.client("s3", region_name="us-east-1")

    bucket = "test-bucket"
    s3_client.create_bucket(Bucket=bucket)

    # Create MRAP
    client.create_multi_region_access_point(
        AccountId=ACCOUNT_ID,
        ClientToken="test-token",
        Details={"Name": "mrap-with-policy", "Regions": [{"Bucket": bucket}]},
    )

    # Define a policy
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"AWS": "*"},
                "Action": ["s3:GetObject"],
                "Resource": f"arn:aws:s3::{ACCOUNT_ID}:accesspoint/mrap-with-policy/object/*",
            }
        ],
    }

    # Put the policy
    response = client.put_multi_region_access_point_policy(
        AccountId=ACCOUNT_ID,
        ClientToken="test-token-policy",
        Details={"Name": "mrap-with-policy", "Policy": json.dumps(policy)},
    )

    assert "RequestTokenARN" in response
    assert "putmultiregionaccesspointpolicy" in response["RequestTokenARN"]


@mock_aws
def test_get_multi_region_access_point_policy():
    client = boto3.client("s3control", region_name="us-east-1")
    s3_client = boto3.client("s3", region_name="us-east-1")

    bucket = "test-bucket"
    s3_client.create_bucket(Bucket=bucket)

    # Create MRAP
    client.create_multi_region_access_point(
        AccountId=ACCOUNT_ID,
        ClientToken="test-token",
        Details={"Name": "mrap-policy-test", "Regions": [{"Bucket": bucket}]},
    )

    # Set a policy
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"AWS": "*"},
                "Action": ["s3:GetObject"],
                "Resource": f"arn:aws:s3::{ACCOUNT_ID}:accesspoint/mrap-policy-test/object/*",
            }
        ],
    }

    client.put_multi_region_access_point_policy(
        AccountId=ACCOUNT_ID,
        ClientToken="test-token-policy",
        Details={"Name": "mrap-policy-test", "Policy": json.dumps(policy)},
    )

    # Get the policy
    response = client.get_multi_region_access_point_policy(
        AccountId=ACCOUNT_ID, Name="mrap-policy-test"
    )

    assert "Policy" in response
    assert "Established" in response["Policy"]
    retrieved_policy = json.loads(response["Policy"]["Established"]["Policy"])
    assert retrieved_policy == policy


@mock_aws
def test_get_multi_region_access_point_policy_not_found():
    client = boto3.client("s3control", region_name="us-east-1")
    s3_client = boto3.client("s3", region_name="us-east-1")

    bucket = "test-bucket"
    s3_client.create_bucket(Bucket=bucket)

    # Create MRAP without policy
    client.create_multi_region_access_point(
        AccountId=ACCOUNT_ID,
        ClientToken="test-token",
        Details={"Name": "mrap-no-policy", "Regions": [{"Bucket": bucket}]},
    )

    # Try to get non-existent policy
    with pytest.raises(ClientError) as exc:
        client.get_multi_region_access_point_policy(
            AccountId=ACCOUNT_ID, Name="mrap-no-policy"
        )

    err = exc.value.response["Error"]
    assert err["Code"] == "NoSuchMultiRegionAccessPointPolicy"


@mock_aws
def test_get_multi_region_access_point_policy_status():
    client = boto3.client("s3control", region_name="us-east-1")
    s3_client = boto3.client("s3", region_name="us-east-1")

    bucket = "test-bucket"
    s3_client.create_bucket(Bucket=bucket)

    # Create MRAP and set policy
    client.create_multi_region_access_point(
        AccountId=ACCOUNT_ID,
        ClientToken="test-token",
        Details={"Name": "mrap-status-test", "Regions": [{"Bucket": bucket}]},
    )

    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"AWS": "*"},
                "Action": ["s3:GetObject"],
                "Resource": f"arn:aws:s3::{ACCOUNT_ID}:accesspoint/mrap-status-test/object/*",
            }
        ],
    }

    client.put_multi_region_access_point_policy(
        AccountId=ACCOUNT_ID,
        ClientToken="test-token-policy",
        Details={"Name": "mrap-status-test", "Policy": json.dumps(policy)},
    )

    # Get policy status
    response = client.get_multi_region_access_point_policy_status(
        AccountId=ACCOUNT_ID, Name="mrap-status-test"
    )

    assert "Established" in response
    # Established contains IsPublic directly (botocore maps PolicyStatus to Established)
    assert response["Established"]["IsPublic"] is True


@mock_aws
def test_delete_multi_region_access_point():
    client = boto3.client("s3control", region_name="us-east-1")
    s3_client = boto3.client("s3", region_name="us-east-1")

    bucket = "test-bucket"
    s3_client.create_bucket(Bucket=bucket)

    # Create MRAP
    client.create_multi_region_access_point(
        AccountId=ACCOUNT_ID,
        ClientToken="test-token",
        Details={"Name": "mrap-to-delete", "Regions": [{"Bucket": bucket}]},
    )

    # Verify it exists
    response = client.get_multi_region_access_point(
        AccountId=ACCOUNT_ID, Name="mrap-to-delete"
    )
    assert response["AccessPoint"]["Name"] == "mrap-to-delete"

    # Delete MRAP
    delete_response = client.delete_multi_region_access_point(
        AccountId=ACCOUNT_ID,
        ClientToken="test-token-delete",
        Details={"Name": "mrap-to-delete"},
    )

    assert "RequestTokenARN" in delete_response
    assert "deletemultiregionaccesspoint" in delete_response["RequestTokenARN"]

    # Verify it's deleted
    with pytest.raises(ClientError) as exc:
        client.get_multi_region_access_point(
            AccountId=ACCOUNT_ID, Name="mrap-to-delete"
        )

    err = exc.value.response["Error"]
    assert err["Code"] == "NoSuchMultiRegionAccessPoint"


@mock_aws
def test_delete_multi_region_access_point_not_found():
    client = boto3.client("s3control", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        client.delete_multi_region_access_point(
            AccountId=ACCOUNT_ID,
            ClientToken="test-token",
            Details={"Name": "non-existent-mrap"},
        )

    err = exc.value.response["Error"]
    assert err["Code"] == "NoSuchMultiRegionAccessPoint"


@mock_aws
def test_multi_region_access_point_with_multiple_buckets():
    client = boto3.client("s3control", region_name="us-east-1")
    s3_client = boto3.client("s3", region_name="us-east-1")

    # Create buckets
    for i in range(3):
        s3_client.create_bucket(Bucket=f"bucket-{i}")

    regions = [{"Bucket": f"bucket-{i}"} for i in range(3)]

    client.create_multi_region_access_point(
        AccountId=ACCOUNT_ID,
        ClientToken="test-token",
        Details={"Name": "multi-bucket-mrap", "Regions": regions},
    )

    response = client.get_multi_region_access_point(
        AccountId=ACCOUNT_ID, Name="multi-bucket-mrap"
    )

    assert len(response["AccessPoint"]["Regions"]) == 3
