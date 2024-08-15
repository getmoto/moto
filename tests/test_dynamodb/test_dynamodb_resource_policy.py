import json
from time import sleep

import boto3
import pytest
from botocore.exceptions import ClientError

from tests import allow_aws_request
from tests.test_dynamodb import dynamodb_aws_verified


def get_policy_doc(action):
    sts = boto3.client("sts", "us-east-1")
    account_id = sts.get_caller_identity()["Account"]

    policy_doc = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Principal": {"AWS": account_id},
                "Effect": "Allow",
                "Action": [action],
                "Resource": "*",
            }
        ],
    }
    return json.dumps(policy_doc)


@dynamodb_aws_verified()
@pytest.mark.aws_verified
def test_put_resource_policy(table_name=None):
    ddb = boto3.client("dynamodb", "us-east-1")

    table_arn = ddb.describe_table(TableName=table_name)["Table"]["TableArn"]
    revision_id = put_resource_policy(ddb, table_arn)

    policy = ddb.get_resource_policy(ResourceArn=table_arn)

    assert policy["RevisionId"] == revision_id
    assert "dynamodb:*" in json.loads(policy["Policy"])["Statement"][0]["Action"]


@dynamodb_aws_verified()
@pytest.mark.aws_verified
def test_put_resource_policy_multiple_times(table_name=None):
    ddb = boto3.client("dynamodb", "us-east-1")

    table_arn = ddb.describe_table(TableName=table_name)["Table"]["TableArn"]
    revision_id1 = put_resource_policy(ddb, table_arn)

    # Putting the same resource policy is a NO-OP
    revision_id2 = put_resource_policy(ddb, table_arn)
    assert revision_id1 == revision_id2

    # Only a different policy resorts in a different revision
    revision_id3 = put_resource_policy(ddb, table_arn, action="dynamodb:PutItem")
    assert revision_id3 != revision_id2
    # Because revision ID's are timestamps, they are comparable
    assert revision_id3 > revision_id2


@dynamodb_aws_verified()
@pytest.mark.aws_verified
def test_put_resource_policy_against_current_revision(table_name=None):
    ddb = boto3.client("dynamodb", "us-east-1")

    table_arn = ddb.describe_table(TableName=table_name)["Table"]["TableArn"]
    revision_id1 = put_resource_policy(ddb, table_arn)

    revision_id2 = put_resource_policy(
        ddb, table_arn, action="dynamodb:GetItem", revision_id=revision_id1
    )

    policy = ddb.get_resource_policy(ResourceArn=table_arn)

    assert policy["RevisionId"] == revision_id2
    assert "dynamodb:GetItem" in json.loads(policy["Policy"])["Statement"][0]["Action"]


@dynamodb_aws_verified()
@pytest.mark.aws_verified
def test_put_resource_policy_against_previous_revision(table_name=None):
    ddb = boto3.client("dynamodb", "us-east-1")

    table_arn = ddb.describe_table(TableName=table_name)["Table"]["TableArn"]
    revision_id1 = put_resource_policy(ddb, table_arn)

    revision_id2 = put_resource_policy(
        ddb, table_arn, action="dynamodb:PutItem", revision_id=revision_id1
    )

    with pytest.raises(ClientError) as exc:
        put_resource_policy(
            ddb, table_arn, action="dynamodb:GetItem", revision_id=revision_id1
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "PolicyNotFoundException"
    assert (
        err["Message"]
        == f"Resource-based policy not found for the provided ResourceArn: Requested update for policy with revision id {revision_id1}, but the policy associated to target table {table_name} has revision id {revision_id2}."
    )

    assert ddb.get_resource_policy(ResourceArn=table_arn)["RevisionId"] == revision_id2


@dynamodb_aws_verified()
@pytest.mark.aws_verified
def test_put_resource_policy_against_norevision(table_name=None):
    ddb = boto3.client("dynamodb", "us-east-1")

    table_arn = ddb.describe_table(TableName=table_name)["Table"]["TableArn"]
    revision_id = put_resource_policy(ddb, table_arn, revision_id="NO_POLICY")

    policy = ddb.get_resource_policy(ResourceArn=table_arn)

    assert policy["RevisionId"] == revision_id


@dynamodb_aws_verified()
@pytest.mark.aws_verified
def test_put_resource_policy_against_norevision_when_revision_exists(table_name=None):
    ddb = boto3.client("dynamodb", "us-east-1")

    table_arn = ddb.describe_table(TableName=table_name)["Table"]["TableArn"]
    revision_id = put_resource_policy(ddb, table_arn)

    with pytest.raises(ClientError) as exc:
        put_resource_policy(ddb, table_arn, revision_id="NO_POLICY")
    err = exc.value.response["Error"]
    assert err["Code"] == "PolicyNotFoundException"
    assert (
        err["Message"]
        == f"Resource-based policy not found for the provided ResourceArn: Requested policy update expecting none to be present for table {table_name}, but a policy exists with revision id {revision_id}."
    )

    assert ddb.get_resource_policy(ResourceArn=table_arn)["RevisionId"] == revision_id


@dynamodb_aws_verified()
@pytest.mark.aws_verified
def test_get_resource_policy_from_resource_without(table_name=None):
    ddb = boto3.client("dynamodb", "us-east-1")

    table_arn = ddb.describe_table(TableName=table_name)["Table"]["TableArn"]
    with pytest.raises(ClientError) as exc:
        ddb.get_resource_policy(ResourceArn=table_arn)
    err = exc.value.response["Error"]
    assert err["Code"] == "PolicyNotFoundException"
    assert (
        err["Message"]
        == f"Resource-based policy not found for the provided ResourceArn: {table_arn}"
    )


@dynamodb_aws_verified()
@pytest.mark.aws_verified
def test_put_resource_policy_unknown_resource(table_name=None):
    ddb = boto3.client("dynamodb", "us-east-1")

    table_arn = ddb.describe_table(TableName=table_name)["Table"]["TableArn"]
    with pytest.raises(ClientError) as exc:
        put_resource_policy(ddb, table_arn + "_")
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert (
        err["Message"]
        == f"Requested resource not found: Table: {table_name}_ not found"
    )


@dynamodb_aws_verified()
@pytest.mark.aws_verified
def test_get_resource_policy_from_unknown_resource(table_name=None):
    ddb = boto3.client("dynamodb", "us-east-1")

    table_arn = ddb.describe_table(TableName=table_name)["Table"]["TableArn"]
    with pytest.raises(ClientError) as exc:
        ddb.get_resource_policy(ResourceArn=table_arn + "unknown")
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert (
        err["Message"]
        == f"Requested resource not found: Table: {table_name}unknown not found"
    )


@dynamodb_aws_verified()
@pytest.mark.aws_verified
def test_delete_resource_policy_from_unknown_resource(table_name=None):
    ddb = boto3.client("dynamodb", "us-east-1")

    table_arn = ddb.describe_table(TableName=table_name)["Table"]["TableArn"]
    with pytest.raises(ClientError) as exc:
        ddb.delete_resource_policy(ResourceArn=table_arn + "unknown")
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert (
        err["Message"]
        == f"Requested resource not found: Table: {table_name}unknown not found"
    )


@dynamodb_aws_verified()
@pytest.mark.aws_verified
def test_delete_resource_policy_from_unknown_revision(table_name=None):
    ddb = boto3.client("dynamodb", "us-east-1")

    table_arn = ddb.describe_table(TableName=table_name)["Table"]["TableArn"]
    revision = put_resource_policy(ddb, table_arn)

    with pytest.raises(ClientError) as exc:
        ddb.delete_resource_policy(ResourceArn=table_arn, ExpectedRevisionId="unknown")
    err = exc.value.response["Error"]
    assert err["Code"] == "PolicyNotFoundException"
    assert (
        err["Message"]
        == f"Resource-based policy not found for the provided ResourceArn: Requested update for policy with revision id unknown, but the policy associated to target table {table_name} has revision id {revision}."
    )


@dynamodb_aws_verified()
@pytest.mark.aws_verified
def test_delete_resource_policy_from_former_revision(table_name=None):
    ddb = boto3.client("dynamodb", "us-east-1")

    table_arn = ddb.describe_table(TableName=table_name)["Table"]["TableArn"]
    old_revision_id = put_resource_policy(ddb, table_arn)

    new_revision_id = put_resource_policy(ddb, table_arn, action="dynamodb:PutItem")

    with pytest.raises(ClientError) as exc:
        ddb.delete_resource_policy(
            ResourceArn=table_arn, ExpectedRevisionId=old_revision_id
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "PolicyNotFoundException"
    assert (
        err["Message"]
        == f"Resource-based policy not found for the provided ResourceArn: Requested update for policy with revision id {old_revision_id}, but the policy associated to target table {table_name} has revision id {new_revision_id}."
    )


@dynamodb_aws_verified()
@pytest.mark.aws_verified
def test_delete_resource_policy(table_name=None):
    ddb = boto3.client("dynamodb", "us-east-1")

    table_arn = ddb.describe_table(TableName=table_name)["Table"]["TableArn"]
    put_resource_policy(ddb, table_arn)

    ddb.delete_resource_policy(ResourceArn=table_arn)
    if allow_aws_request():
        # Wait for deletion to finish
        sleep(15)

    with pytest.raises(ClientError) as exc:
        ddb.get_resource_policy(ResourceArn=table_arn)
    assert exc.value.response["Error"]["Code"] == "PolicyNotFoundException"


@dynamodb_aws_verified()
@pytest.mark.aws_verified
def test_delete_resource_policy_with_revision(table_name=None):
    ddb = boto3.client("dynamodb", "us-east-1")

    table_arn = ddb.describe_table(TableName=table_name)["Table"]["TableArn"]
    old_revision_id = put_resource_policy(ddb, table_arn)

    ddb.delete_resource_policy(
        ResourceArn=table_arn, ExpectedRevisionId=old_revision_id
    )
    if allow_aws_request():
        # Wait for deletion to finish
        sleep(15)

    with pytest.raises(ClientError) as exc:
        ddb.get_resource_policy(ResourceArn=table_arn)
    assert exc.value.response["Error"]["Code"] == "PolicyNotFoundException"


def put_resource_policy(ddb, table_arn, action="dynamodb:*", revision_id=None):
    kwargs = {}
    if revision_id:
        kwargs["ExpectedRevisionId"] = revision_id
    policy_doc = get_policy_doc(action)
    revision_id = ddb.put_resource_policy(
        ResourceArn=table_arn, Policy=policy_doc, **kwargs
    )["RevisionId"]
    # Put Resource Policy is an async action
    # Periodically poll to see when the policy is ready
    for x in range(20):
        try:
            policy = ddb.get_resource_policy(ResourceArn=table_arn)
            assert policy["RevisionId"] == revision_id
            if allow_aws_request():
                # Policy is supposedly ready-  but may still complain that a ResourcePolicy update is in progress
                # Hopefully AWS is ready afterwards
                sleep(1)
            return revision_id
        except (ClientError, AssertionError):
            # Policy is not ready yet
            sleep(1)
    assert False, f"Revision {revision_id} wasn't ready in 20 seconds"
