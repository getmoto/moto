from datetime import datetime

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

REGION = "us-east-1"
CLUSTER_NAME = "my-cluster"
ROLE_ARN = f"arn:aws:iam::{ACCOUNT_ID}:role/my-role"
ROLE_WITH_PATH_ARN = f"arn:aws:iam::{ACCOUNT_ID}:role/development/apps/my-role"
USER_ARN = f"arn:aws:iam::{ACCOUNT_ID}:user/my-user"


def _create_cluster(client):
    client.create_cluster(
        name=CLUSTER_NAME,
        roleArn=f"arn:aws:iam::{ACCOUNT_ID}:role/eks-cluster-role",
        resourcesVpcConfig={"subnetIds": ["subnet-12345678"]},
    )


@pytest.fixture(name="client")
def fixture_client():
    with mock_aws():
        client = boto3.client("eks", region_name=REGION)
        _create_cluster(client)
        yield client


def test_create_access_entry(client):
    entry = client.create_access_entry(
        clusterName=CLUSTER_NAME,
        principalArn=ROLE_ARN,
        kubernetesGroups=["viewers"],
        tags={"team": "platform"},
    )["accessEntry"]

    assert entry["clusterName"] == CLUSTER_NAME
    assert entry["principalArn"] == ROLE_ARN
    assert entry["kubernetesGroups"] == ["viewers"]
    assert entry["type"] == "STANDARD"
    assert entry["tags"] == {"team": "platform"}
    assert entry["accessEntryArn"].startswith(
        f"arn:aws:eks:{REGION}:{ACCOUNT_ID}:access-entry/{CLUSTER_NAME}/role/{ACCOUNT_ID}/my-role/"
    )
    assert isinstance(entry["createdAt"], datetime)
    assert entry["modifiedAt"] == entry["createdAt"]


@pytest.mark.parametrize(
    "principal_arn,entry_type,expected_username",
    [
        (
            ROLE_ARN,
            "STANDARD",
            f"arn:aws:sts::{ACCOUNT_ID}:assumed-role/my-role/{{{{SessionName}}}}",
        ),
        # The path is removed from the generated username
        (
            ROLE_WITH_PATH_ARN,
            "STANDARD",
            f"arn:aws:sts::{ACCOUNT_ID}:assumed-role/my-role/{{{{SessionName}}}}",
        ),
        (USER_ARN, "STANDARD", USER_ARN),
        (ROLE_ARN, "EC2_LINUX", "system:node:{{EC2PrivateDNSName}}"),
        (ROLE_ARN, "EC2_WINDOWS", "system:node:{{EC2PrivateDNSName}}"),
        (ROLE_ARN, "FARGATE_LINUX", "system:node:{{SessionName}}"),
        (ROLE_ARN, "HYBRID_LINUX", "system:node:{{SessionName}}"),
    ],
)
def test_create_access_entry_generates_username(
    client, principal_arn, entry_type, expected_username
):
    entry = client.create_access_entry(
        clusterName=CLUSTER_NAME, principalArn=principal_arn, type=entry_type
    )["accessEntry"]

    assert entry["type"] == entry_type
    assert entry["username"] == expected_username


def test_create_access_entry_with_custom_username(client):
    entry = client.create_access_entry(
        clusterName=CLUSTER_NAME, principalArn=USER_ARN, username="my-user"
    )["accessEntry"]

    assert entry["username"] == "my-user"


@pytest.mark.parametrize("prefix", ["system:", "eks:", "aws:", "amazon:", "iam:"])
def test_create_access_entry_rejects_reserved_username(client, prefix):
    with pytest.raises(ClientError) as exc:
        client.create_access_entry(
            clusterName=CLUSTER_NAME,
            principalArn=USER_ARN,
            username=f"{prefix}my-user",
        )
    assert exc.value.response["Error"]["Code"] == "InvalidParameterException"


def test_create_access_entry_rejects_groups_for_non_standard_type(client):
    with pytest.raises(ClientError) as exc:
        client.create_access_entry(
            clusterName=CLUSTER_NAME,
            principalArn=ROLE_ARN,
            type="EC2_LINUX",
            kubernetesGroups=["viewers"],
        )
    assert exc.value.response["Error"]["Code"] == "InvalidParameterException"


def test_create_access_entry_twice(client):
    client.create_access_entry(clusterName=CLUSTER_NAME, principalArn=ROLE_ARN)

    with pytest.raises(ClientError) as exc:
        client.create_access_entry(clusterName=CLUSTER_NAME, principalArn=ROLE_ARN)
    assert exc.value.response["Error"]["Code"] == "ResourceInUseException"


def test_create_access_entry_unknown_cluster(client):
    with pytest.raises(ClientError) as exc:
        client.create_access_entry(clusterName="unknown", principalArn=ROLE_ARN)
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "No cluster found for name: unknown."


def test_describe_access_entry(client):
    created = client.create_access_entry(
        clusterName=CLUSTER_NAME, principalArn=ROLE_WITH_PATH_ARN
    )["accessEntry"]

    described = client.describe_access_entry(
        clusterName=CLUSTER_NAME, principalArn=ROLE_WITH_PATH_ARN
    )["accessEntry"]

    assert described == created


def test_describe_access_entry_unknown_principal(client):
    with pytest.raises(ClientError) as exc:
        client.describe_access_entry(clusterName=CLUSTER_NAME, principalArn=ROLE_ARN)
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"


def test_list_access_entries(client):
    assert client.list_access_entries(clusterName=CLUSTER_NAME)["accessEntries"] == []

    for arn in [USER_ARN, ROLE_ARN, ROLE_WITH_PATH_ARN]:
        client.create_access_entry(clusterName=CLUSTER_NAME, principalArn=arn)

    resp = client.list_access_entries(clusterName=CLUSTER_NAME)
    assert resp["accessEntries"] == sorted([USER_ARN, ROLE_ARN, ROLE_WITH_PATH_ARN])
    assert "nextToken" not in resp


def test_list_access_entries_pagination(client):
    arns = [f"arn:aws:iam::{ACCOUNT_ID}:role/role-{i}" for i in range(5)]
    for arn in arns:
        client.create_access_entry(clusterName=CLUSTER_NAME, principalArn=arn)

    page1 = client.list_access_entries(clusterName=CLUSTER_NAME, maxResults=3)
    assert page1["accessEntries"] == arns[:3]

    page2 = client.list_access_entries(
        clusterName=CLUSTER_NAME, maxResults=3, nextToken=page1["nextToken"]
    )
    assert page2["accessEntries"] == arns[3:]
    assert "nextToken" not in page2


def test_list_access_entries_unknown_cluster(client):
    with pytest.raises(ClientError) as exc:
        client.list_access_entries(clusterName="unknown")
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"


def test_update_access_entry(client):
    created = client.create_access_entry(
        clusterName=CLUSTER_NAME, principalArn=ROLE_ARN, kubernetesGroups=["viewers"]
    )["accessEntry"]

    updated = client.update_access_entry(
        clusterName=CLUSTER_NAME,
        principalArn=ROLE_ARN,
        kubernetesGroups=["editors", "viewers"],
        username="my-role:{{SessionName}}",
    )["accessEntry"]

    assert updated["kubernetesGroups"] == ["editors", "viewers"]
    assert updated["username"] == "my-role:{{SessionName}}"
    assert updated["accessEntryArn"] == created["accessEntryArn"]
    assert updated["createdAt"] == created["createdAt"]
    assert updated["modifiedAt"] >= created["modifiedAt"]

    described = client.describe_access_entry(
        clusterName=CLUSTER_NAME, principalArn=ROLE_ARN
    )["accessEntry"]
    assert described == updated


def test_update_access_entry_rejects_groups_for_non_standard_type(client):
    client.create_access_entry(
        clusterName=CLUSTER_NAME, principalArn=ROLE_ARN, type="EC2_LINUX"
    )

    with pytest.raises(ClientError) as exc:
        client.update_access_entry(
            clusterName=CLUSTER_NAME, principalArn=ROLE_ARN, kubernetesGroups=["x"]
        )
    assert exc.value.response["Error"]["Code"] == "InvalidParameterException"


def test_update_access_entry_unknown_principal(client):
    with pytest.raises(ClientError) as exc:
        client.update_access_entry(
            clusterName=CLUSTER_NAME, principalArn=ROLE_ARN, kubernetesGroups=["x"]
        )
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"


def test_delete_access_entry(client):
    client.create_access_entry(clusterName=CLUSTER_NAME, principalArn=ROLE_ARN)
    client.create_access_entry(clusterName=CLUSTER_NAME, principalArn=USER_ARN)

    client.delete_access_entry(clusterName=CLUSTER_NAME, principalArn=ROLE_ARN)

    entries = client.list_access_entries(clusterName=CLUSTER_NAME)["accessEntries"]
    assert entries == [USER_ARN]
    with pytest.raises(ClientError) as exc:
        client.describe_access_entry(clusterName=CLUSTER_NAME, principalArn=ROLE_ARN)
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"


def test_delete_access_entry_unknown_principal(client):
    with pytest.raises(ClientError) as exc:
        client.delete_access_entry(clusterName=CLUSTER_NAME, principalArn=ROLE_ARN)
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"
