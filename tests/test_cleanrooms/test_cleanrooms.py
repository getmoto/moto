"""Unit tests for cleanrooms-supported APIs."""

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

REGION = "us-east-2"
UNKNOWN_ID = "00000000-0000-0000-0000-000000000000"


def create_collaboration(client, name="test-collaboration", **kwargs):
    params = {
        "name": name,
        "description": "A test collaboration",
        "creatorDisplayName": "Creator",
        "creatorMemberAbilities": ["CAN_QUERY", "CAN_RECEIVE_RESULTS"],
        "queryLogStatus": "ENABLED",
        "members": [
            {
                "accountId": "111111111111",
                "memberAbilities": ["CAN_QUERY"],
                "displayName": "Invited Member",
            }
        ],
        **kwargs,
    }
    return client.create_collaboration(**params)["collaboration"]


def create_configured_table(client, name="test-table", **kwargs):
    params = {
        "name": name,
        "description": "A test configured table",
        "tableReference": {
            "glue": {"tableName": "test-table", "databaseName": "test-db"}
        },
        "allowedColumns": ["column1", "column2"],
        "analysisMethod": "DIRECT_QUERY",
        **kwargs,
    }
    return client.create_configured_table(**params)["configuredTable"]


@mock_aws
def test_create_collaboration():
    client = boto3.client("cleanrooms", region_name=REGION)
    collaboration = create_collaboration(client)

    assert (
        collaboration["arn"]
        == f"arn:aws:cleanrooms:{REGION}:{ACCOUNT_ID}:collaboration/{collaboration['id']}"
    )
    assert collaboration["name"] == "test-collaboration"
    assert collaboration["description"] == "A test collaboration"
    assert collaboration["creatorAccountId"] == ACCOUNT_ID
    assert collaboration["creatorDisplayName"] == "Creator"
    assert collaboration["memberStatus"] == "INVITED"
    assert collaboration["queryLogStatus"] == "ENABLED"
    assert "createTime" in collaboration
    assert "updateTime" in collaboration


@mock_aws
def test_get_collaboration():
    client = boto3.client("cleanrooms", region_name=REGION)
    created = create_collaboration(client)

    collaboration = client.get_collaboration(collaborationIdentifier=created["id"])[
        "collaboration"
    ]

    assert collaboration["id"] == created["id"]
    assert collaboration["arn"] == created["arn"]
    assert collaboration["name"] == "test-collaboration"


@mock_aws
def test_get_collaboration_unknown():
    client = boto3.client("cleanrooms", region_name=REGION)

    with pytest.raises(ClientError) as exc:
        client.get_collaboration(collaborationIdentifier=UNKNOWN_ID)
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == f"Could not find collaboration with id {UNKNOWN_ID}"


@mock_aws
def test_list_collaborations():
    client = boto3.client("cleanrooms", region_name=REGION)
    create_collaboration(client, name="collaboration-1")
    create_collaboration(client, name="collaboration-2")

    collaborations = client.list_collaborations()["collaborationList"]

    assert len(collaborations) == 2
    assert {c["name"] for c in collaborations} == {
        "collaboration-1",
        "collaboration-2",
    }
    for summary in collaborations:
        assert "id" in summary
        assert "arn" in summary
        assert "creatorAccountId" in summary
        assert "updateTime" in summary
        assert "description" not in summary


@mock_aws
def test_list_collaborations_pagination():
    client = boto3.client("cleanrooms", region_name=REGION)
    for idx in range(3):
        create_collaboration(client, name=f"collaboration-{idx}")

    page1 = client.list_collaborations(maxResults=2)
    assert len(page1["collaborationList"]) == 2
    assert "nextToken" in page1

    page2 = client.list_collaborations(maxResults=2, nextToken=page1["nextToken"])
    assert len(page2["collaborationList"]) == 1
    assert "nextToken" not in page2


@mock_aws
def test_update_collaboration():
    client = boto3.client("cleanrooms", region_name=REGION)
    created = create_collaboration(client)

    updated = client.update_collaboration(
        collaborationIdentifier=created["id"],
        name="updated-name",
        description="updated description",
    )["collaboration"]

    assert updated["name"] == "updated-name"
    assert updated["description"] == "updated description"
    assert updated["updateTime"] >= updated["createTime"]


@mock_aws
def test_delete_collaboration():
    client = boto3.client("cleanrooms", region_name=REGION)
    created = create_collaboration(client)

    client.delete_collaboration(collaborationIdentifier=created["id"])

    assert client.list_collaborations()["collaborationList"] == []
    with pytest.raises(ClientError) as exc:
        client.delete_collaboration(collaborationIdentifier=created["id"])
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_list_members():
    client = boto3.client("cleanrooms", region_name=REGION)
    created = create_collaboration(client)

    members = client.list_members(collaborationIdentifier=created["id"])[
        "memberSummaries"
    ]

    assert len(members) == 2
    creator = next(m for m in members if m["accountId"] == ACCOUNT_ID)
    assert creator["status"] == "INVITED"
    assert creator["displayName"] == "Creator"
    assert creator["abilities"] == ["CAN_QUERY", "CAN_RECEIVE_RESULTS"]
    invited = next(m for m in members if m["accountId"] == "111111111111")
    assert invited["status"] == "INVITED"
    assert invited["displayName"] == "Invited Member"
    assert invited["abilities"] == ["CAN_QUERY"]


@mock_aws
def test_create_membership():
    client = boto3.client("cleanrooms", region_name=REGION)
    created = create_collaboration(client)

    membership = client.create_membership(
        collaborationIdentifier=created["id"], queryLogStatus="DISABLED"
    )["membership"]

    assert (
        membership["arn"]
        == f"arn:aws:cleanrooms:{REGION}:{ACCOUNT_ID}:membership/{membership['id']}"
    )
    assert membership["collaborationId"] == created["id"]
    assert membership["collaborationArn"] == created["arn"]
    assert membership["collaborationName"] == "test-collaboration"
    assert membership["collaborationCreatorAccountId"] == ACCOUNT_ID
    assert membership["status"] == "ACTIVE"
    assert membership["memberAbilities"] == ["CAN_QUERY", "CAN_RECEIVE_RESULTS"]
    assert membership["queryLogStatus"] == "DISABLED"
    assert membership["paymentConfiguration"] == {
        "queryCompute": {"isResponsible": True}
    }

    # The creator becomes an active member of the collaboration
    collaboration = client.get_collaboration(collaborationIdentifier=created["id"])[
        "collaboration"
    ]
    assert collaboration["memberStatus"] == "ACTIVE"
    assert collaboration["membershipId"] == membership["id"]
    assert collaboration["membershipArn"] == membership["arn"]


@mock_aws
def test_create_membership_unknown_collaboration():
    client = boto3.client("cleanrooms", region_name=REGION)

    with pytest.raises(ClientError) as exc:
        client.create_membership(
            collaborationIdentifier=UNKNOWN_ID, queryLogStatus="ENABLED"
        )
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_get_membership():
    client = boto3.client("cleanrooms", region_name=REGION)
    collaboration = create_collaboration(client)
    created = client.create_membership(
        collaborationIdentifier=collaboration["id"], queryLogStatus="ENABLED"
    )["membership"]

    membership = client.get_membership(membershipIdentifier=created["id"])["membership"]

    assert membership["id"] == created["id"]
    assert membership["collaborationId"] == collaboration["id"]

    with pytest.raises(ClientError) as exc:
        client.get_membership(membershipIdentifier=UNKNOWN_ID)
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_list_memberships():
    client = boto3.client("cleanrooms", region_name=REGION)
    for idx in range(2):
        collaboration = create_collaboration(client, name=f"collaboration-{idx}")
        client.create_membership(
            collaborationIdentifier=collaboration["id"], queryLogStatus="ENABLED"
        )

    memberships = client.list_memberships()["membershipSummaries"]

    assert len(memberships) == 2
    assert {m["collaborationName"] for m in memberships} == {
        "collaboration-0",
        "collaboration-1",
    }
    for summary in memberships:
        assert "id" in summary
        assert "arn" in summary
        assert "updateTime" in summary
        assert summary["status"] == "ACTIVE"


@mock_aws
def test_update_membership():
    client = boto3.client("cleanrooms", region_name=REGION)
    collaboration = create_collaboration(client)
    created = client.create_membership(
        collaborationIdentifier=collaboration["id"], queryLogStatus="ENABLED"
    )["membership"]

    updated = client.update_membership(
        membershipIdentifier=created["id"], queryLogStatus="DISABLED"
    )["membership"]

    assert updated["queryLogStatus"] == "DISABLED"
    assert updated["updateTime"] >= updated["createTime"]


@mock_aws
def test_delete_membership():
    client = boto3.client("cleanrooms", region_name=REGION)
    collaboration = create_collaboration(client)
    created = client.create_membership(
        collaborationIdentifier=collaboration["id"], queryLogStatus="ENABLED"
    )["membership"]

    client.delete_membership(membershipIdentifier=created["id"])

    assert client.list_memberships()["membershipSummaries"] == []
    updated_collaboration = client.get_collaboration(
        collaborationIdentifier=collaboration["id"]
    )["collaboration"]
    assert updated_collaboration["memberStatus"] == "LEFT"
    assert "membershipId" not in updated_collaboration


@mock_aws
def test_create_configured_table():
    client = boto3.client("cleanrooms", region_name=REGION)
    configured_table = create_configured_table(client)

    assert (
        configured_table["arn"]
        == f"arn:aws:cleanrooms:{REGION}:{ACCOUNT_ID}:configuredtable/{configured_table['id']}"
    )
    assert configured_table["name"] == "test-table"
    assert configured_table["description"] == "A test configured table"
    assert configured_table["tableReference"] == {
        "glue": {"tableName": "test-table", "databaseName": "test-db"}
    }
    assert configured_table["allowedColumns"] == ["column1", "column2"]
    assert configured_table["analysisMethod"] == "DIRECT_QUERY"
    assert configured_table["analysisRuleTypes"] == []


@mock_aws
def test_get_configured_table():
    client = boto3.client("cleanrooms", region_name=REGION)
    created = create_configured_table(client)

    configured_table = client.get_configured_table(
        configuredTableIdentifier=created["id"]
    )["configuredTable"]

    assert configured_table["id"] == created["id"]
    assert configured_table["name"] == "test-table"

    with pytest.raises(ClientError) as exc:
        client.get_configured_table(configuredTableIdentifier=UNKNOWN_ID)
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_list_configured_tables():
    client = boto3.client("cleanrooms", region_name=REGION)
    create_configured_table(client, name="table-1")
    create_configured_table(client, name="table-2")

    configured_tables = client.list_configured_tables()["configuredTableSummaries"]

    assert len(configured_tables) == 2
    assert {t["name"] for t in configured_tables} == {"table-1", "table-2"}
    for summary in configured_tables:
        assert "id" in summary
        assert "arn" in summary
        assert "updateTime" in summary
        assert "tableReference" not in summary


@mock_aws
def test_update_configured_table():
    client = boto3.client("cleanrooms", region_name=REGION)
    created = create_configured_table(client)

    updated = client.update_configured_table(
        configuredTableIdentifier=created["id"],
        name="updated-table",
        description="updated description",
    )["configuredTable"]

    assert updated["name"] == "updated-table"
    assert updated["description"] == "updated description"
    assert updated["updateTime"] >= updated["createTime"]


@mock_aws
def test_delete_configured_table():
    client = boto3.client("cleanrooms", region_name=REGION)
    created = create_configured_table(client)

    client.delete_configured_table(configuredTableIdentifier=created["id"])

    assert client.list_configured_tables()["configuredTableSummaries"] == []
    with pytest.raises(ClientError) as exc:
        client.delete_configured_table(configuredTableIdentifier=created["id"])
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_tags_on_create():
    client = boto3.client("cleanrooms", region_name=REGION)
    collaboration = create_collaboration(client, tags={"env": "test"})
    configured_table = create_configured_table(client, tags={"team": "data"})
    membership = client.create_membership(
        collaborationIdentifier=collaboration["id"],
        queryLogStatus="ENABLED",
        tags={"owner": "me"},
    )["membership"]

    assert client.list_tags_for_resource(resourceArn=collaboration["arn"])["tags"] == {
        "env": "test"
    }
    assert client.list_tags_for_resource(resourceArn=configured_table["arn"])[
        "tags"
    ] == {"team": "data"}
    assert client.list_tags_for_resource(resourceArn=membership["arn"])["tags"] == {
        "owner": "me"
    }


@mock_aws
def test_tag_and_untag_resource():
    client = boto3.client("cleanrooms", region_name=REGION)
    collaboration = create_collaboration(client)

    client.tag_resource(
        resourceArn=collaboration["arn"], tags={"env": "test", "team": "data"}
    )
    assert client.list_tags_for_resource(resourceArn=collaboration["arn"])["tags"] == {
        "env": "test",
        "team": "data",
    }

    client.untag_resource(resourceArn=collaboration["arn"], tagKeys=["env"])
    assert client.list_tags_for_resource(resourceArn=collaboration["arn"])["tags"] == {
        "team": "data"
    }


@mock_aws
def test_collaborations_are_region_specific():
    client_use2 = boto3.client("cleanrooms", region_name=REGION)
    client_euw1 = boto3.client("cleanrooms", region_name="eu-west-1")
    create_collaboration(client_use2)

    collaboration = create_collaboration(client_euw1, name="eu-collaboration")

    assert collaboration["arn"].startswith(f"arn:aws:cleanrooms:eu-west-1:{ACCOUNT_ID}")
    assert len(client_euw1.list_collaborations()["collaborationList"]) == 1
