"""Unit tests for backup-supported APIs."""
import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_backup

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html

@mock_backup
def test_create_backup_plan():
    client = boto3.client("backup", region_name="eu-west-1")
    response = client.create_backup_vault(
            BackupVaultName='backupvault-foobar',
        )
    resp = client.create_backup_plan(
                BackupPlan={
                    'BackupPlanName': 'backupplan-foobar',
                    'Rules': [
                        {
                            'RuleName': 'foobar',
                            'TargetBackupVaultName': response['BackupVaultName'],
                        },
                    ],
                },
            )
    assert "BackupPlanId" in resp
    assert "BackupPlanArn" in resp
    assert "CreationDate" in resp
    assert "VersionId" in resp


@mock_backup
def test_create_backup_vault():
    client = boto3.client("backup", region_name="eu-west-1")
    resp = client.create_backup_vault(
            BackupVaultName='backupvault-foobar',
            BackupVaultTags={
                'foo': 'bar',
            },
        )
    assert "BackupVaultName" in resp
    assert "BackupVaultArn" in resp
    assert "CreationDate" in resp

@mock_backup
def test_get_backup_plan():
    client = boto3.client("backup", region_name="eu-west-1")
    response = client.create_backup_vault(
            BackupVaultName='backupvault-foobar',
        )
    plan = client.create_backup_plan(
                BackupPlan={
                    'BackupPlanName': 'backupplan-foobar',
                    'Rules': [
                        {
                            'RuleName': 'foobar',
                            'TargetBackupVaultName': response['BackupVaultName'],
                        },
                    ],
                },
            )
    resp = client.get_backup_plan(
        BackupPlanId=plan['BackupPlanId'],
        VersionId=plan['VersionId']
    )
    assert "BackupPlan" in resp


@mock_backup
def test_delete_backup_plan():
    client = boto3.client("backup", region_name="eu-west-1")
    response = client.create_backup_vault(
            BackupVaultName='backupvault-foobar',
        )
    plan = client.create_backup_plan(
                BackupPlan={
                    'BackupPlanName': 'backupplan-foobar',
                    'Rules': [
                        {
                            'RuleName': 'foobar',
                            'TargetBackupVaultName': response['BackupVaultName'],
                        },
                    ],
                },
            )
    resp = client.delete_backup_plan(
        BackupPlanId=plan['BackupPlanId']
    )
    assert "BackupPlanId" in resp
    assert "BackupPlanArn" in resp
    assert "DeletionDate" in resp
    assert "VersionId" in resp

    with pytest.raises(ClientError) as exc:
        client.get_backup_plan(BackupPlanId=plan['BackupPlanId'])
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"



@mock_backup
def test_list_backup_plans():
    client = boto3.client("backup", region_name="eu-west-1")
    response = client.create_backup_vault(
            BackupVaultName='backupvault-foobar',
        )
    for i in range(1,3):
        client.create_backup_plan(
            BackupPlan={
                'BackupPlanName': f'backup-plan-{i}',
                'Rules': [
                    {
                        'RuleName': 'foobar',
                        'TargetBackupVaultName': response['BackupVaultName'],
                    },
                ],
            },
        )
    resp = client.list_backup_plans()
    backup_plans = resp["BackupPlansList"]
    assert backup_plans[0]["BackupPlanName"] == "backup-plan-1"
    assert backup_plans[1]["BackupPlanName"] == "backup-plan-2"
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200


@mock_backup
def test_list_backup_vaults():
    client = boto3.client("backup", region_name="eu-west-1")
    for i in range(1,3):
        client.create_backup_vault(
            BackupVaultName=f'backup-vault-{i}',
        )
    resp = client.list_backup_vaults()
    backup_plans = resp["BackupVaultList"]
    assert backup_plans[0]["BackupVaultName"] == "backup-vault-1"
    assert backup_plans[1]["BackupVaultName"] == "backup-vault-2"
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

@mock_backup
def test_list_tags_vault():
    client = boto3.client("backup", region_name="eu-west-1")
    vault = client.create_backup_vault(
            BackupVaultName='backupvault-foobar',
            BackupVaultTags={
                'key1': 'value1',
                'key2': 'value2',
            },
        )
    resp = client.list_tags(ResourceArn=vault["BackupVaultArn"])
    assert resp["Tags"] == {"key1": "value1", "key2": "value2"}

@mock_backup
def test_list_tags_plan():
    client = boto3.client("backup", region_name="eu-west-1")
    response = client.create_backup_vault(
        BackupVaultName='backupvault-foobar',
    )
    plan = client.create_backup_plan(
            BackupPlan={
                'BackupPlanName': 'backupplan-foobar',
                'Rules': [
                    {
                        'RuleName': 'foobar',
                        'TargetBackupVaultName': response['BackupVaultName'],
                    },
                ],
            },
            BackupPlanTags={
                'key1': 'value1',
                'key2': 'value2',
            },
        )
    resp = client.list_tags(ResourceArn=plan["BackupPlanArn"])
    assert resp["Tags"] == {"key1": "value1", "key2": "value2"}

@mock_backup
def test_tag_resource():
    client = boto3.client("backup", region_name="eu-west-1")
    vault = client.create_backup_vault(
            BackupVaultName='backupvault-foobar',
            BackupVaultTags={
                'key1': 'value1',
            },
        )
    resource_arn = vault["BackupVaultArn"]
    client.tag_resource(
            ResourceArn=resource_arn, Tags={"key2": "value2", "key3": "value3"}
        )
    resp = client.list_tags(ResourceArn=resource_arn)
    assert resp["Tags"] == {"key1": "value1", "key2": "value2", "key3": "value3"}

@mock_backup
def test_untag_resource():
    client = boto3.client("backup", region_name="eu-west-1")
    vault = client.create_backup_vault(
            BackupVaultName='backupvault-foobar',
            BackupVaultTags={
                'key1': 'value1',
            },
        )
    resource_arn = vault["BackupVaultArn"]
    client.tag_resource(
            ResourceArn=resource_arn, Tags={"key2": "value2", "key3": "value3"}
        )
    resp = client.untag_resource(ResourceArn=resource_arn,TagKeyList=["key2"])
    resp = client.list_tags(ResourceArn=resource_arn)
    assert resp["Tags"] == {"key1": "value1", "key3": "value3"}
