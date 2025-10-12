import boto3

from moto import mock_aws
from tests import DEFAULT_ACCOUNT_ID


@mock_aws
def test_provision_permission_set():
    ssoadmin = boto3.client("sso-admin", "us-east-1")

    instance_arn = ssoadmin.list_instances()["Instances"][0]["InstanceArn"]

    p_set_arn = ssoadmin.create_permission_set(InstanceArn=instance_arn, Name="pset1")[
        "PermissionSet"
    ]["PermissionSetArn"]

    status = ssoadmin.provision_permission_set(
        InstanceArn=instance_arn,
        PermissionSetArn=p_set_arn,
        TargetType="AWS_ACCOUNT",
    )["PermissionSetProvisioningStatus"]

    assert status["AccountId"] == DEFAULT_ACCOUNT_ID
    assert status["CreatedDate"]
    assert status["PermissionSetArn"] == p_set_arn
    assert status["Status"] == "SUCCEEDED"


@mock_aws
def test_list_permission_sets_provisioned_to_account():
    ssoadmin = boto3.client("sso-admin", "us-east-1")

    instance_arn = ssoadmin.list_instances()["Instances"][0]["InstanceArn"]

    p_set_arn = ssoadmin.create_permission_set(InstanceArn=instance_arn, Name="pset1")[
        "PermissionSet"
    ]["PermissionSetArn"]

    provisioned = ssoadmin.list_permission_sets_provisioned_to_account(
        AccountId=DEFAULT_ACCOUNT_ID, InstanceArn=instance_arn
    )["PermissionSets"]
    assert len(provisioned) == 0

    accounts = ssoadmin.list_accounts_for_provisioned_permission_set(
        InstanceArn=instance_arn, PermissionSetArn=p_set_arn
    )["AccountIds"]
    assert accounts == []

    ssoadmin.provision_permission_set(
        InstanceArn=instance_arn,
        PermissionSetArn=p_set_arn,
        TargetType="AWS_ACCOUNT",
    )

    provisioned = ssoadmin.list_permission_sets_provisioned_to_account(
        AccountId=DEFAULT_ACCOUNT_ID, InstanceArn=instance_arn
    )["PermissionSets"]
    assert provisioned == [p_set_arn]

    accounts = ssoadmin.list_accounts_for_provisioned_permission_set(
        InstanceArn=instance_arn, PermissionSetArn=p_set_arn
    )["AccountIds"]
    assert accounts == [DEFAULT_ACCOUNT_ID]
