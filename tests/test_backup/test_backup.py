"""Unit tests for backup-supported APIs."""

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws


@mock_aws
def test_create_backup_plan():
    client = boto3.client("backup", region_name="eu-west-1")
    response = client.create_backup_vault(
        BackupVaultName="backupvault-foobar",
    )
    resp = client.create_backup_plan(
        BackupPlan={
            "BackupPlanName": "backupplan-foobar",
            "Rules": [
                {
                    "RuleName": "foobar",
                    "TargetBackupVaultName": response["BackupVaultName"],
                },
            ],
        },
    )
    assert "BackupPlanId" in resp
    assert "BackupPlanArn" in resp
    assert "CreationDate" in resp
    assert "VersionId" in resp


@mock_aws
def test_create_backup_plan_already_exists():
    client = boto3.client("backup", region_name="eu-west-1")
    backup_plan_name = "backup_plan_foobar"
    rules = [
        {
            "RuleName": "foobar",
            "TargetBackupVaultName": "backup-vault-foobar",
        },
    ]
    client.create_backup_plan(
        BackupPlan={"BackupPlanName": backup_plan_name, "Rules": rules}
    )

    with pytest.raises(ClientError) as exc:
        client.create_backup_plan(
            BackupPlan={"BackupPlanName": backup_plan_name, "Rules": rules}
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "AlreadyExistsException"


@mock_aws
def test_get_backup_plan():
    client = boto3.client("backup", region_name="eu-west-1")
    response = client.create_backup_vault(
        BackupVaultName="backupvault-foobar",
    )
    plan = client.create_backup_plan(
        BackupPlan={
            "BackupPlanName": "backupplan-foobar",
            "Rules": [
                {
                    "RuleName": "foobar",
                    "TargetBackupVaultName": response["BackupVaultName"],
                },
            ],
        },
    )
    resp = client.get_backup_plan(
        BackupPlanId=plan["BackupPlanId"], VersionId=plan["VersionId"]
    )
    assert "BackupPlan" in resp


@mock_aws
def test_get_backup_plan_invalid_id():
    client = boto3.client("backup", region_name="eu-west-1")

    with pytest.raises(ClientError) as exc:
        client.get_backup_plan(BackupPlanId="foobar")
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"


@mock_aws
def test_get_backup_plan_invalid_version_id():
    client = boto3.client("backup", region_name="eu-west-1")

    plan = client.create_backup_plan(
        BackupPlan={
            "BackupPlanName": "backupplan-foobar",
            "Rules": [
                {
                    "RuleName": "foobar",
                    "TargetBackupVaultName": "Backup-vault-foobar",
                },
            ],
        },
    )
    with pytest.raises(ClientError) as exc:
        client.get_backup_plan(BackupPlanId=plan["BackupPlanId"], VersionId="foobar")
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"


@mock_aws
def test_get_backup_plan_with_multiple_rules():
    client = boto3.client("backup", region_name="eu-west-1")
    plan = client.create_backup_plan(
        BackupPlan={
            "BackupPlanName": "backupplan-foobar",
            "Rules": [
                {
                    "RuleName": "rule1",
                    "TargetBackupVaultName": "backupvault-foobar",
                    "ScheduleExpression": "cron(0 1 ? * * *)",
                    "StartWindowMinutes": 60,
                    "CompletionWindowMinutes": 120,
                },
                {
                    "RuleName": "rule2",
                    "TargetBackupVaultName": "backupvault-foobar",
                },
            ],
        },
    )
    resp = client.get_backup_plan(BackupPlanId=plan["BackupPlanId"])
    for rule in resp["BackupPlan"]["Rules"]:
        assert "ScheduleExpression" in rule
        assert "StartWindowMinutes" in rule
        assert "CompletionWindowMinutes" in rule
        assert "RuleId" in rule


@mock_aws
def test_delete_backup_plan():
    client = boto3.client("backup", region_name="eu-west-1")
    response = client.create_backup_vault(
        BackupVaultName="backupvault-foobar",
    )
    plan = client.create_backup_plan(
        BackupPlan={
            "BackupPlanName": "backupplan-foobar",
            "Rules": [
                {
                    "RuleName": "foobar",
                    "TargetBackupVaultName": response["BackupVaultName"],
                },
            ],
        },
    )

    resp = client.delete_backup_plan(BackupPlanId=plan["BackupPlanId"])
    assert "BackupPlanId" in resp
    assert "BackupPlanArn" in resp
    assert "DeletionDate" in resp
    assert "VersionId" in resp

    resp = client.get_backup_plan(
        BackupPlanId=plan["BackupPlanId"], VersionId=plan["VersionId"]
    )
    assert "DeletionDate" in resp


@mock_aws
def test_delete_backup_plan_invalid_id():
    client = boto3.client("backup", region_name="eu-west-1")

    with pytest.raises(ClientError) as exc:
        client.delete_backup_plan(BackupPlanId="foobar")
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"


@mock_aws
def test_list_backup_plans():
    client = boto3.client("backup", region_name="eu-west-1")
    for i in range(1, 3):
        client.create_backup_plan(
            BackupPlan={
                "BackupPlanName": f"backup-plan-{i}",
                "Rules": [
                    {
                        "RuleName": "foobar",
                        "TargetBackupVaultName": "backupvault-foobar",
                    },
                ],
            },
        )
    resp = client.list_backup_plans()
    backup_plans = resp["BackupPlansList"]
    assert backup_plans[0]["BackupPlanName"] == "backup-plan-1"
    assert backup_plans[1]["BackupPlanName"] == "backup-plan-2"
    assert len(backup_plans) == 2
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200


@mock_aws
def test_list_backup_plans_without_include_deleted():
    client = boto3.client("backup", region_name="eu-west-1")

    for i in range(1, 3):
        client.create_backup_plan(
            BackupPlan={
                "BackupPlanName": f"backup-plan-{i}",
                "Rules": [
                    {
                        "RuleName": "foobar",
                        "TargetBackupVaultName": "backupvault-foobar",
                    },
                ],
            },
        )
    resp = client.list_backup_plans()
    client.delete_backup_plan(BackupPlanId=resp["BackupPlansList"][0]["BackupPlanId"])
    resp_list = client.list_backup_plans()
    backup_plans = resp_list["BackupPlansList"]
    assert backup_plans[0]["BackupPlanName"] == "backup-plan-2"
    assert len(backup_plans) == 1


@mock_aws
def test_list_backup_plans_with_include_deleted():
    client = boto3.client("backup", region_name="eu-west-1")
    for i in range(1, 3):
        client.create_backup_plan(
            BackupPlan={
                "BackupPlanName": f"backup-plan-{i}",
                "Rules": [
                    {
                        "RuleName": "foobar",
                        "TargetBackupVaultName": "backupvault-foobar",
                    },
                ],
            },
        )
    resp = client.list_backup_plans()
    client.delete_backup_plan(BackupPlanId=resp["BackupPlansList"][0]["BackupPlanId"])
    resp_list = client.list_backup_plans(IncludeDeleted=True)
    backup_plans = resp_list["BackupPlansList"]
    assert backup_plans[0]["BackupPlanName"] == "backup-plan-1"
    assert backup_plans[1]["BackupPlanName"] == "backup-plan-2"
    assert len(backup_plans) == 2


@mock_aws
def test_create_backup_vault():
    client = boto3.client("backup", region_name="eu-west-1")
    resp = client.create_backup_vault(
        BackupVaultName="backupvault-foobar",
        BackupVaultTags={
            "foo": "bar",
        },
    )
    assert "BackupVaultName" in resp
    assert "BackupVaultArn" in resp
    assert "CreationDate" in resp


@mock_aws
def test_create_backup_vault_already_exists():
    client = boto3.client("backup", region_name="eu-west-1")
    backup_vault_name = "backup_vault_foobar"
    client.create_backup_vault(BackupVaultName=backup_vault_name)

    with pytest.raises(ClientError) as exc:
        client.create_backup_vault(BackupVaultName=backup_vault_name)
    err = exc.value.response["Error"]
    assert err["Code"] == "AlreadyExistsException"


@mock_aws
def test_list_backup_vaults():
    client = boto3.client("backup", region_name="eu-west-1")
    for i in range(1, 3):
        client.create_backup_vault(
            BackupVaultName=f"backup-vault-{i}",
        )
    resp = client.list_backup_vaults()
    backup_plans = resp["BackupVaultList"]
    assert backup_plans[0]["BackupVaultName"] == "backup-vault-1"
    assert backup_plans[1]["BackupVaultName"] == "backup-vault-2"
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200


@mock_aws
def test_list_tags_vault():
    client = boto3.client("backup", region_name="eu-west-1")
    vault = client.create_backup_vault(
        BackupVaultName="backupvault-foobar",
        BackupVaultTags={
            "key1": "value1",
            "key2": "value2",
        },
    )
    resp = client.list_tags(ResourceArn=vault["BackupVaultArn"])
    assert resp["Tags"] == {"key1": "value1", "key2": "value2"}


@mock_aws
def test_list_tags_plan():
    client = boto3.client("backup", region_name="eu-west-1")
    response = client.create_backup_vault(
        BackupVaultName="backupvault-foobar",
    )
    plan = client.create_backup_plan(
        BackupPlan={
            "BackupPlanName": "backupplan-foobar",
            "Rules": [
                {
                    "RuleName": "foobar",
                    "TargetBackupVaultName": response["BackupVaultName"],
                },
            ],
        },
        BackupPlanTags={
            "key1": "value1",
            "key2": "value2",
        },
    )
    resp = client.list_tags(ResourceArn=plan["BackupPlanArn"])
    assert resp["Tags"] == {"key1": "value1", "key2": "value2"}


@mock_aws
def test_tag_resource():
    client = boto3.client("backup", region_name="eu-west-1")
    vault = client.create_backup_vault(
        BackupVaultName="backupvault-foobar",
        BackupVaultTags={
            "key1": "value1",
        },
    )
    resource_arn = vault["BackupVaultArn"]
    client.tag_resource(
        ResourceArn=resource_arn, Tags={"key2": "value2", "key3": "value3"}
    )
    resp = client.list_tags(ResourceArn=resource_arn)
    assert resp["Tags"] == {"key1": "value1", "key2": "value2", "key3": "value3"}


@mock_aws
def test_untag_resource():
    client = boto3.client("backup", region_name="eu-west-1")
    vault = client.create_backup_vault(
        BackupVaultName="backupvault-foobar",
        BackupVaultTags={
            "key1": "value1",
        },
    )
    resource_arn = vault["BackupVaultArn"]
    client.tag_resource(
        ResourceArn=resource_arn, Tags={"key2": "value2", "key3": "value3"}
    )
    resp = client.untag_resource(ResourceArn=resource_arn, TagKeyList=["key2"])
    resp = client.list_tags(ResourceArn=resource_arn)
    assert resp["Tags"] == {"key1": "value1", "key3": "value3"}
