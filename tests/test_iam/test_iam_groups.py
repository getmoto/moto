from __future__ import unicode_literals

from datetime import datetime

import boto
import boto3
import sure  # noqa

import pytest
from boto.exception import BotoServerError
from botocore.exceptions import ClientError
from moto import mock_iam, mock_iam_deprecated
from moto.core import ACCOUNT_ID

MOCK_POLICY = """
{
  "Version": "2012-10-17",
  "Statement":
    {
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::example_bucket"
    }
}
"""


@mock_iam_deprecated()
def test_create_group():
    conn = boto.connect_iam()
    conn.create_group("my-group")
    with pytest.raises(BotoServerError):
        conn.create_group("my-group")


@mock_iam_deprecated()
def test_get_group():
    conn = boto.connect_iam()
    conn.create_group("my-group")
    conn.get_group("my-group")
    with pytest.raises(BotoServerError):
        conn.get_group("not-group")


@mock_iam()
def test_get_group_current():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_group(GroupName="my-group")
    result = conn.get_group(GroupName="my-group")

    assert result["Group"]["Path"] == "/"
    assert result["Group"]["GroupName"] == "my-group"
    assert isinstance(result["Group"]["CreateDate"], datetime)
    assert result["Group"]["GroupId"]
    assert result["Group"]["Arn"] == "arn:aws:iam::{}:group/my-group".format(ACCOUNT_ID)
    assert not result["Users"]

    # Make a group with a different path:
    other_group = conn.create_group(GroupName="my-other-group", Path="some/location")
    assert other_group["Group"]["Path"] == "some/location"
    assert other_group["Group"][
        "Arn"
    ] == "arn:aws:iam::{}:group/some/location/my-other-group".format(ACCOUNT_ID)


@mock_iam_deprecated()
def test_get_all_groups():
    conn = boto.connect_iam()
    conn.create_group("my-group1")
    conn.create_group("my-group2")
    groups = conn.get_all_groups()["list_groups_response"]["list_groups_result"][
        "groups"
    ]
    groups.should.have.length_of(2)


@mock_iam_deprecated()
def test_add_user_to_group():
    conn = boto.connect_iam()
    with pytest.raises(BotoServerError):
        conn.add_user_to_group("my-group", "my-user")
    conn.create_group("my-group")
    with pytest.raises(BotoServerError):
        conn.add_user_to_group("my-group", "my-user")
    conn.create_user("my-user")
    conn.add_user_to_group("my-group", "my-user")


@mock_iam_deprecated()
def test_remove_user_from_group():
    conn = boto.connect_iam()
    with pytest.raises(BotoServerError):
        conn.remove_user_from_group("my-group", "my-user")
    conn.create_group("my-group")
    conn.create_user("my-user")
    with pytest.raises(BotoServerError):
        conn.remove_user_from_group("my-group", "my-user")
    conn.add_user_to_group("my-group", "my-user")
    conn.remove_user_from_group("my-group", "my-user")


@mock_iam_deprecated()
def test_get_groups_for_user():
    conn = boto.connect_iam()
    conn.create_group("my-group1")
    conn.create_group("my-group2")
    conn.create_group("other-group")
    conn.create_user("my-user")
    conn.add_user_to_group("my-group1", "my-user")
    conn.add_user_to_group("my-group2", "my-user")

    groups = conn.get_groups_for_user("my-user")["list_groups_for_user_response"][
        "list_groups_for_user_result"
    ]["groups"]
    groups.should.have.length_of(2)


@mock_iam_deprecated()
def test_put_group_policy():
    conn = boto.connect_iam()
    conn.create_group("my-group")
    conn.put_group_policy("my-group", "my-policy", MOCK_POLICY)


@mock_iam
def test_attach_group_policies():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_group(GroupName="my-group")
    conn.list_attached_group_policies(GroupName="my-group")[
        "AttachedPolicies"
    ].should.be.empty
    policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonElasticMapReduceforEC2Role"
    conn.list_attached_group_policies(GroupName="my-group")[
        "AttachedPolicies"
    ].should.be.empty
    conn.attach_group_policy(GroupName="my-group", PolicyArn=policy_arn)
    conn.list_attached_group_policies(GroupName="my-group")[
        "AttachedPolicies"
    ].should.equal(
        [{"PolicyName": "AmazonElasticMapReduceforEC2Role", "PolicyArn": policy_arn}]
    )

    conn.detach_group_policy(GroupName="my-group", PolicyArn=policy_arn)
    conn.list_attached_group_policies(GroupName="my-group")[
        "AttachedPolicies"
    ].should.be.empty


@mock_iam_deprecated()
def test_get_group_policy():
    conn = boto.connect_iam()
    conn.create_group("my-group")
    with pytest.raises(BotoServerError):
        conn.get_group_policy("my-group", "my-policy")

    conn.put_group_policy("my-group", "my-policy", MOCK_POLICY)
    conn.get_group_policy("my-group", "my-policy")


@mock_iam_deprecated()
def test_get_all_group_policies():
    conn = boto.connect_iam()
    conn.create_group("my-group")
    policies = conn.get_all_group_policies("my-group")["list_group_policies_response"][
        "list_group_policies_result"
    ]["policy_names"]
    assert policies == []
    conn.put_group_policy("my-group", "my-policy", MOCK_POLICY)
    policies = conn.get_all_group_policies("my-group")["list_group_policies_response"][
        "list_group_policies_result"
    ]["policy_names"]
    assert policies == ["my-policy"]


@mock_iam()
def test_list_group_policies():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_group(GroupName="my-group")
    conn.list_group_policies(GroupName="my-group")["PolicyNames"].should.be.empty
    conn.put_group_policy(
        GroupName="my-group", PolicyName="my-policy", PolicyDocument=MOCK_POLICY
    )
    conn.list_group_policies(GroupName="my-group")["PolicyNames"].should.equal(
        ["my-policy"]
    )


@mock_iam
def test_delete_group():
    conn = boto3.client("iam", region_name="us-east-1")
    conn.create_group(GroupName="my-group")
    groups = conn.list_groups()
    assert groups["Groups"][0]["GroupName"] == "my-group"
    assert len(groups["Groups"]) == 1
    conn.delete_group(GroupName="my-group")
    conn.list_groups()["Groups"].should.be.empty


@mock_iam
def test_delete_unknown_group():
    conn = boto3.client("iam", region_name="us-east-1")
    with pytest.raises(ClientError) as err:
        conn.delete_group(GroupName="unknown-group")
    err.value.response["Error"]["Code"].should.equal("NoSuchEntity")
    err.value.response["Error"]["Message"].should.equal(
        "The group with name unknown-group cannot be found."
    )
