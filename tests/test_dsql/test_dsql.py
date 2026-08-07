"""Unit tests for dsql-supported APIs."""

from datetime import datetime, timezone

import boto3
import pytest
from botocore.exceptions import ClientError
from freezegun import freeze_time

from moto import mock_aws, settings

TEST_REGION = "us-east-1"


@mock_aws
def test_create_cluster():
    client = boto3.client("dsql", region_name=TEST_REGION)
    with freeze_time("2024-12-22 12:34:00"):
        resp = client.create_cluster()

    identifier = resp["identifier"]
    assert identifier is not None
    assert resp["arn"] == f"arn:aws:dsql:us-east-1:123456789012:cluster/{identifier}"
    assert resp["deletionProtectionEnabled"] is True
    assert resp["status"] == "CREATING"
    assert resp["encryptionDetails"] == {
        "encryptionStatus": "ENABLED",
        "encryptionType": "AWS_OWNED_KMS_KEY",
    }
    if not settings.TEST_SERVER_MODE:
        assert resp["creationTime"] == datetime(
            2024, 12, 22, 12, 34, tzinfo=timezone.utc
        )


@mock_aws
def test_create_cluster_with_tags():
    client = boto3.client("dsql", region_name=TEST_REGION)
    tags = {"foo": "bar", "baz": "qux"}
    resp = client.create_cluster(tags=tags)
    cluster_arn = resp["arn"]
    resp = client.list_tags_for_resource(resourceArn=cluster_arn)
    assert resp["tags"] == tags


@mock_aws
def test_create_cluster_with_customer_managed_kms_key():
    client = boto3.client("dsql", region_name=TEST_REGION)
    key_arn = "arn:aws:kms:us-east-1:123456789012:key/example"

    cluster = client.create_cluster(kmsEncryptionKey=key_arn)

    assert cluster["encryptionDetails"] == {
        "encryptionStatus": "ENABLED",
        "encryptionType": "CUSTOMER_MANAGED_KMS_KEY",
        "kmsKeyArn": key_arn,
    }


@mock_aws
def test_delete_cluster():
    client = boto3.client("dsql", region_name=TEST_REGION)
    resp = client.create_cluster()
    identifier = resp["identifier"]
    client.update_cluster(identifier=identifier, deletionProtectionEnabled=False)
    resp = client.delete_cluster(identifier=identifier)
    assert resp["identifier"] == identifier
    assert resp["status"] == "DELETING"

    resp = client.get_cluster(identifier=identifier)
    assert resp["status"] == "DELETED"
    with pytest.raises(client.exceptions.ResourceNotFoundException):
        client.get_cluster(identifier=identifier)


@mock_aws
def test_delete_cluster_with_deletion_protection():
    client = boto3.client("dsql", region_name=TEST_REGION)
    identifier = client.create_cluster()["identifier"]
    with pytest.raises(client.exceptions.ConflictException):
        client.delete_cluster(identifier=identifier)


@mock_aws
def test_delete_non_existent_cluster():
    client = boto3.client("dsql", region_name=TEST_REGION)
    with pytest.raises(ClientError) as exc:
        client.delete_cluster(identifier="non-existent-cluster")
    resp = exc.value.response
    assert resp["Error"]["Code"] == "ResourceNotFoundException"
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 404
    assert resp["resourceId"] == "non-existent-cluster"
    assert resp["resourceType"] == "cluster"


@mock_aws
def test_get_invalid_cluster():
    client = boto3.client("dsql", region_name=TEST_REGION)

    try:
        client.get_cluster(identifier="invalid")
    except ClientError as err:
        assert err.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_get_cluster():
    client = boto3.client("dsql", region_name=TEST_REGION)
    with freeze_time("2024-12-22 12:34:00"):
        resp = client.create_cluster()

    identifier = resp["identifier"]

    get_resp = client.get_cluster(identifier=identifier)

    # TODO Add `witnessRegion` and `linkedClusterArns` when implement create-multi-region-clusters
    assert get_resp["identifier"] == identifier
    assert (
        get_resp["arn"] == f"arn:aws:dsql:us-east-1:123456789012:cluster/{identifier}"
    )
    assert get_resp["deletionProtectionEnabled"] is True
    assert get_resp["status"] == "ACTIVE"
    if not settings.TEST_SERVER_MODE:
        assert get_resp["creationTime"] == datetime(
            2024, 12, 22, 12, 34, tzinfo=timezone.utc
        )


@mock_aws
def test_get_vpc_endpoint_service_name():
    client = boto3.client("dsql", region_name=TEST_REGION)
    resp = client.create_cluster()
    identifier = resp["identifier"]
    endpoint = resp["endpoint"]
    resp = client.get_vpc_endpoint_service_name(identifier=identifier)
    assert resp["clusterVpcEndpoint"] == endpoint


@mock_aws()
def test_generate_tokens():
    client = boto3.client("dsql", TEST_REGION)

    hostname = "dsql.amazonaws.com"

    admin_url = client.generate_db_connect_admin_auth_token(Hostname=hostname)
    assert admin_url.startswith(hostname)
    assert "Action=DbConnectAdmin" in admin_url

    url = client.generate_db_connect_auth_token(Hostname=hostname)
    assert url.startswith(hostname)
    assert "Action=DbConnect" in url


@mock_aws
def test_list_clusters_with_pagination():
    client = boto3.client("dsql", region_name=TEST_REGION)
    identifiers = [client.create_cluster()["identifier"] for _ in range(3)]

    pages = list(
        client.get_paginator("list_clusters").paginate(PaginationConfig={"PageSize": 1})
    )

    assert [c["identifier"] for page in pages for c in page["clusters"]] == identifiers


@mock_aws
def test_update_cluster():
    client = boto3.client("dsql", region_name=TEST_REGION)
    identifier = client.create_cluster()["identifier"]

    client.update_cluster(
        identifier=identifier,
        deletionProtectionEnabled=False,
        kmsEncryptionKey="arn:aws:kms:us-east-1:123456789012:key/example",
        multiRegionProperties={"witnessRegion": "us-west-2"},
    )

    cluster = client.get_cluster(identifier=identifier)
    assert cluster["deletionProtectionEnabled"] is False
    assert cluster["multiRegionProperties"] == {"witnessRegion": "us-west-2"}
    assert cluster["encryptionDetails"] == {
        "encryptionStatus": "ENABLED",
        "encryptionType": "CUSTOMER_MANAGED_KMS_KEY",
        "kmsKeyArn": "arn:aws:kms:us-east-1:123456789012:key/example",
    }


@mock_aws
def test_tag_and_untag_cluster():
    client = boto3.client("dsql", region_name=TEST_REGION)
    cluster = client.create_cluster(tags={"existing": "tag"})

    client.tag_resource(resourceArn=cluster["arn"], tags={"new": "tag"})
    assert client.list_tags_for_resource(resourceArn=cluster["arn"])["tags"] == {
        "existing": "tag",
        "new": "tag",
    }

    client.untag_resource(resourceArn=cluster["arn"], tagKeys=["existing"])
    assert client.list_tags_for_resource(resourceArn=cluster["arn"])["tags"] == {
        "new": "tag"
    }


@mock_aws
def test_cluster_policy_lifecycle():
    client = boto3.client("dsql", region_name=TEST_REGION)
    identifier = client.create_cluster()["identifier"]
    policy = '{"Version":"2012-10-17","Statement":[]}'

    put_response = client.put_cluster_policy(identifier=identifier, policy=policy)
    get_response = client.get_cluster_policy(identifier=identifier)
    assert get_response == {
        "policy": policy,
        "policyVersion": put_response["policyVersion"],
        "ResponseMetadata": get_response["ResponseMetadata"],
    }

    delete_response = client.delete_cluster_policy(identifier=identifier)
    assert delete_response["policyVersion"] != put_response["policyVersion"]
    with pytest.raises(client.exceptions.ResourceNotFoundException):
        client.get_cluster_policy(identifier=identifier)


@mock_aws
def test_cluster_policy_expected_version():
    client = boto3.client("dsql", region_name=TEST_REGION)
    identifier = client.create_cluster()["identifier"]
    policy = '{"Version":"2012-10-17","Statement":[]}'
    response = client.put_cluster_policy(identifier=identifier, policy=policy)

    with pytest.raises(client.exceptions.ConflictException):
        client.put_cluster_policy(
            identifier=identifier,
            policy=policy,
            expectedPolicyVersion="outdated",
        )

    client.delete_cluster_policy(
        identifier=identifier,
        expectedPolicyVersion=response["policyVersion"],
    )


@mock_aws
def test_delete_missing_cluster_policy():
    client = boto3.client("dsql", region_name=TEST_REGION)
    identifier = client.create_cluster()["identifier"]

    with pytest.raises(client.exceptions.ResourceNotFoundException):
        client.delete_cluster_policy(identifier=identifier)


@mock_aws
def test_create_cluster_is_idempotent():
    client = boto3.client("dsql", region_name=TEST_REGION)
    token = "a" * 32
    first = client.create_cluster(clientToken=token)
    second = client.create_cluster(clientToken=token)
    assert second["identifier"] == first["identifier"]


@mock_aws
def test_create_cluster_idempotency_conflict():
    client = boto3.client("dsql", region_name=TEST_REGION)
    token = "a" * 32
    client.create_cluster(clientToken=token, deletionProtectionEnabled=True)

    with pytest.raises(client.exceptions.ConflictException):
        client.create_cluster(
            clientToken=token,
            deletionProtectionEnabled=False,
        )


@mock_aws
def test_list_clusters_rejects_invalid_pagination_token():
    client = boto3.client("dsql", region_name=TEST_REGION)
    client.create_cluster()

    with pytest.raises(client.exceptions.ValidationException) as exc:
        client.list_clusters(nextToken="invalid")

    assert exc.value.response["Error"]["Code"] == "ValidationException"
    assert exc.value.response["reason"] == "other"

    with pytest.raises(client.exceptions.ValidationException):
        client.list_clusters(nextToken="2")


def _create_stream(client, cluster_identifier, **kwargs):
    return client.create_stream(
        clusterIdentifier=cluster_identifier,
        targetDefinition={
            "kinesis": {
                "streamArn": "arn:aws:kinesis:us-east-1:123456789012:stream/changes",
                "roleArn": "arn:aws:iam::123456789012:role/dsql-stream",
            }
        },
        ordering="UNORDERED",
        format="JSON",
        **kwargs,
    )


@mock_aws
def test_stream_lifecycle():
    client = boto3.client("dsql", region_name=TEST_REGION)
    cluster_identifier = client.create_cluster()["identifier"]

    created = _create_stream(client, cluster_identifier, tags={"environment": "test"})
    stream_identifier = created["streamIdentifier"]
    assert created["status"] == "CREATING"

    stream = client.get_stream(
        clusterIdentifier=cluster_identifier,
        streamIdentifier=stream_identifier,
    )
    assert stream["status"] == "ACTIVE"
    assert stream["format"] == "JSON"
    assert stream["ordering"] == "UNORDERED"
    assert stream["targetDefinition"]["kinesis"]["roleArn"].endswith("role/dsql-stream")
    assert stream["tags"] == {"environment": "test"}

    deleted = client.delete_stream(
        clusterIdentifier=cluster_identifier,
        streamIdentifier=stream_identifier,
    )
    assert deleted["status"] == "DELETING"

    stream = client.get_stream(
        clusterIdentifier=cluster_identifier,
        streamIdentifier=stream_identifier,
    )
    assert stream["status"] == "DELETED"
    with pytest.raises(client.exceptions.ResourceNotFoundException):
        client.get_stream(
            clusterIdentifier=cluster_identifier,
            streamIdentifier=stream_identifier,
        )


@mock_aws
def test_create_stream_idempotency_conflict():
    client = boto3.client("dsql", region_name=TEST_REGION)
    cluster_identifier = client.create_cluster()["identifier"]
    token = "b" * 32
    _create_stream(client, cluster_identifier, clientToken=token)

    with pytest.raises(client.exceptions.ConflictException):
        _create_stream(
            client,
            cluster_identifier,
            clientToken=token,
            tags={"different": "parameters"},
        )


@mock_aws
def test_create_stream_is_idempotent():
    client = boto3.client("dsql", region_name=TEST_REGION)
    cluster_identifier = client.create_cluster()["identifier"]
    token = "b" * 32

    first = _create_stream(client, cluster_identifier, clientToken=token)
    second = _create_stream(client, cluster_identifier, clientToken=token)

    assert second["streamIdentifier"] == first["streamIdentifier"]


@mock_aws
def test_list_streams_with_pagination():
    client = boto3.client("dsql", region_name=TEST_REGION)
    cluster_identifier = client.create_cluster()["identifier"]
    stream_identifiers = [
        _create_stream(client, cluster_identifier)["streamIdentifier"] for _ in range(3)
    ]

    pages = list(
        client.get_paginator("list_streams").paginate(
            clusterIdentifier=cluster_identifier,
            PaginationConfig={"PageSize": 1},
        )
    )

    assert [
        s["streamIdentifier"] for page in pages for s in page["streams"]
    ] == stream_identifiers


@mock_aws
def test_tag_and_untag_stream():
    client = boto3.client("dsql", region_name=TEST_REGION)
    cluster_identifier = client.create_cluster()["identifier"]
    stream = _create_stream(client, cluster_identifier)

    client.tag_resource(resourceArn=stream["arn"], tags={"key": "value"})
    assert client.list_tags_for_resource(resourceArn=stream["arn"])["tags"] == {
        "key": "value"
    }
    client.untag_resource(resourceArn=stream["arn"], tagKeys=["key"])
    assert client.list_tags_for_resource(resourceArn=stream["arn"])["tags"] == {}


@mock_aws
def test_stream_operations_validate_resources():
    client = boto3.client("dsql", region_name=TEST_REGION)
    with pytest.raises(client.exceptions.ResourceNotFoundException):
        _create_stream(client, "0" * 26)

    cluster_identifier = client.create_cluster()["identifier"]
    with pytest.raises(client.exceptions.ResourceNotFoundException):
        client.get_stream(
            clusterIdentifier=cluster_identifier,
            streamIdentifier="0" * 26,
        )


@mock_aws
def test_resource_groups_tagging_api_returns_clusters_and_streams():
    dsql = boto3.client("dsql", region_name=TEST_REGION)
    tagging = boto3.client("resourcegroupstaggingapi", region_name=TEST_REGION)
    cluster = dsql.create_cluster(tags={"Name": "custodian-cluster"})
    stream = _create_stream(
        dsql,
        cluster["identifier"],
        tags={"Name": "custodian-stream"},
    )

    response = tagging.get_resources(ResourceARNList=[cluster["arn"], stream["arn"]])
    resources = {
        resource["ResourceARN"]: {tag["Key"]: tag["Value"] for tag in resource["Tags"]}
        for resource in response["ResourceTagMappingList"]
    }

    assert resources == {
        cluster["arn"]: {"Name": "custodian-cluster"},
        stream["arn"]: {"Name": "custodian-stream"},
    }

    tagging.tag_resources(
        ResourceARNList=[cluster["arn"]],
        Tags={"Environment": "test"},
    )
    assert dsql.list_tags_for_resource(resourceArn=cluster["arn"])["tags"] == {
        "Name": "custodian-cluster",
        "Environment": "test",
    }


@mock_aws
def test_custodian_style_enumerate_augment_filter_and_tag_flow():
    dsql = boto3.client("dsql", region_name=TEST_REGION)
    tagging = boto3.client("resourcegroupstaggingapi", region_name=TEST_REGION)
    cluster = dsql.create_cluster(tags={"Owner": "custodian"})

    summaries = dsql.list_clusters()["clusters"]
    resources = [
        dsql.get_cluster(identifier=summary["identifier"]) for summary in summaries
    ]
    tag_mappings = tagging.get_resources(
        ResourceARNList=[resource["arn"] for resource in resources]
    )["ResourceTagMappingList"]
    tags_by_arn = {
        mapping["ResourceARN"]: {tag["Key"]: tag["Value"] for tag in mapping["Tags"]}
        for mapping in tag_mappings
    }
    matched = [
        resource
        for resource in resources
        if tags_by_arn.get(resource["arn"], {}).get("Owner") == "custodian"
    ]
    assert [resource["identifier"] for resource in matched] == [cluster["identifier"]]

    dsql.tag_resource(resourceArn=matched[0]["arn"], tags={"Env": "test"})
    refreshed = tagging.get_resources(ResourceARNList=[matched[0]["arn"]])[
        "ResourceTagMappingList"
    ][0]
    assert {tag["Key"]: tag["Value"] for tag in refreshed["Tags"]} == {
        "Owner": "custodian",
        "Env": "test",
    }
