"""Unit tests for quicksight-supported APIs."""
import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import

from botocore.exceptions import ClientError
from moto import mock_quicksight
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_quicksight
def test_create_group():
    client = boto3.client("quicksight", region_name="us-west-2")
    resp = client.create_group(
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
        GroupName="mygroup",
        Description="my new fancy group",
    )

    resp.should.have.key("Group")

    resp["Group"].should.have.key("Arn").equals(
        f"arn:aws:quicksight:us-west-2:{ACCOUNT_ID}:group/default/mygroup"
    )
    resp["Group"].should.have.key("GroupName").equals("mygroup")
    resp["Group"].should.have.key("Description").equals("my new fancy group")
    resp["Group"].should.have.key("PrincipalId").equals(f"{ACCOUNT_ID}")


@mock_quicksight
def test_describe_group():
    client = boto3.client("quicksight", region_name="us-west-2")
    client.create_group(
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
        GroupName="mygroup",
        Description="my new fancy group",
    )

    resp = client.describe_group(
        GroupName="mygroup", AwsAccountId=ACCOUNT_ID, Namespace="default"
    )

    resp.should.have.key("Group")

    resp["Group"].should.have.key("Arn").equals(
        f"arn:aws:quicksight:us-west-2:{ACCOUNT_ID}:group/default/mygroup"
    )
    resp["Group"].should.have.key("GroupName").equals("mygroup")
    resp["Group"].should.have.key("Description").equals("my new fancy group")
    resp["Group"].should.have.key("PrincipalId").equals(f"{ACCOUNT_ID}")


@mock_quicksight
def test_update_group():
    client = boto3.client("quicksight", region_name="us-west-2")
    client.create_group(
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
        GroupName="mygroup",
        Description="desc1",
    )

    resp = client.update_group(
        GroupName="mygroup",
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
        Description="desc2",
    )
    resp.should.have.key("Group").should.have.key("Description").equals("desc2")

    resp = client.describe_group(
        GroupName="mygroup", AwsAccountId=ACCOUNT_ID, Namespace="default"
    )

    resp.should.have.key("Group")
    resp["Group"].should.have.key("Arn").equals(
        f"arn:aws:quicksight:us-west-2:{ACCOUNT_ID}:group/default/mygroup"
    )
    resp["Group"].should.have.key("GroupName").equals("mygroup")
    resp["Group"].should.have.key("Description").equals("desc2")
    resp["Group"].should.have.key("PrincipalId").equals(f"{ACCOUNT_ID}")


@mock_quicksight
def test_delete_group():
    client = boto3.client("quicksight", region_name="us-east-2")
    client.create_group(
        AwsAccountId=ACCOUNT_ID,
        Namespace="default",
        GroupName="mygroup",
        Description="my new fancy group",
    )

    client.delete_group(
        GroupName="mygroup", AwsAccountId=ACCOUNT_ID, Namespace="default"
    )

    with pytest.raises(ClientError) as exc:
        client.describe_group(
            GroupName="mygroup", AwsAccountId=ACCOUNT_ID, Namespace="default"
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")


@mock_quicksight
def test_list_groups__initial():
    client = boto3.client("quicksight", region_name="us-east-2")
    resp = client.list_groups(AwsAccountId=ACCOUNT_ID, Namespace="default")

    resp.should.have.key("GroupList").equals([])
    resp.should.have.key("Status").equals(200)


@mock_quicksight
def test_list_groups():
    client = boto3.client("quicksight", region_name="us-east-1")
    for i in range(4):
        client.create_group(
            AwsAccountId=ACCOUNT_ID, Namespace="default", GroupName=f"group{i}"
        )

    resp = client.list_groups(AwsAccountId=ACCOUNT_ID, Namespace="default")

    resp.should.have.key("GroupList").length_of(4)
    resp.should.have.key("Status").equals(200)

    resp["GroupList"].should.contain(
        {
            "Arn": f"arn:aws:quicksight:us-east-1:{ACCOUNT_ID}:group/default/group0",
            "GroupName": "group0",
            "PrincipalId": ACCOUNT_ID,
        }
    )

    resp["GroupList"].should.contain(
        {
            "Arn": f"arn:aws:quicksight:us-east-1:{ACCOUNT_ID}:group/default/group3",
            "GroupName": "group3",
            "PrincipalId": ACCOUNT_ID,
        }
    )
