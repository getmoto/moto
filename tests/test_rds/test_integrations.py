"""RDS tests covering integrations with other service backends."""

import json
import uuid

import boto3
import pytest
from botocore import waiter, xform_name
from botocore.exceptions import ClientError

from tests import aws_verified

from . import DEFAULT_REGION


@aws_verified
@pytest.mark.aws_verified
def test_db_cluster_managed_master_user_password_lifecycle():
    # Clients
    kms = boto3.client("kms", region_name=DEFAULT_REGION)
    rds = boto3.client("rds", region_name=DEFAULT_REGION)
    secretsmanager = boto3.client("secretsmanager", region_name=DEFAULT_REGION)

    # Waiters
    db_cluster_modifications_complete = get_custom_waiter(
        "db_cluster_modifications_complete", rds
    )
    db_cluster_available = rds.get_waiter("db_cluster_available")
    db_cluster_deleted = rds.get_waiter("db_cluster_deleted")
    master_user_secret_available = get_custom_waiter(
        "db_cluster_master_user_secret_available", rds
    )
    master_user_secret_deleted = get_custom_waiter("secret_deleted", secretsmanager)

    # KMS keys
    resp = kms.describe_key(KeyId="alias/aws/secretsmanager")
    default_kms_key_arn = resp["KeyMetadata"]["Arn"]
    resp = kms.create_key(KeyUsage="ENCRYPT_DECRYPT", KeySpec="SYMMETRIC_DEFAULT")
    custom_kms_key_arn = resp["KeyMetadata"]["Arn"]
    custom_kms_key_id = resp["KeyMetadata"]["KeyId"]

    # Create DBCluster with managed master user password
    db_cluster_identifier = "test-" + str(uuid.uuid4())
    resp = rds.create_db_cluster(
        DBClusterIdentifier=db_cluster_identifier,
        Engine="aurora-postgresql",
        MasterUsername="root",
        ManageMasterUserPassword=True,
    )
    db_cluster = resp["DBCluster"]
    master_user_secret = db_cluster["MasterUserSecret"]
    assert master_user_secret["KmsKeyId"] == default_kms_key_arn
    assert master_user_secret["SecretStatus"] == "creating"
    # Check the secret in SecretsManager
    secret_arn = master_user_secret["SecretArn"]
    master_user_secret_available.wait(DBClusterIdentifier=db_cluster_identifier)
    secret = secretsmanager.describe_secret(SecretId=secret_arn)
    assert str(secret["Name"]).startswith("rds!cluster")
    assert secret["OwningService"] == "rds"
    # Check that RDS sees the secret as active
    db_cluster_available.wait(DBClusterIdentifier=db_cluster_identifier)
    resp = rds.describe_db_clusters(DBClusterIdentifier=db_cluster_identifier)
    db_cluster = resp["DBClusters"][0]
    master_user_secret = db_cluster["MasterUserSecret"]
    assert master_user_secret["SecretStatus"] == "active"
    # Check that managed secret has correct structure
    resp = secretsmanager.get_secret_value(SecretId=secret_arn)
    secret = json.loads(resp["SecretString"])
    assert "username" in secret
    assert "password" in secret

    # Disable password management
    resp = rds.modify_db_cluster(
        DBClusterIdentifier=db_cluster_identifier,
        ManageMasterUserPassword=False,
        MasterUserPassword="Non-Managed-Pa55word!",
        ApplyImmediately=True,
    )
    db_cluster = resp["DBCluster"]
    # TODO: This passes on AWS but is not implemented yet in moto
    # assert "MasterUserPassword" in db_cluster["PendingModifiedValues"]
    db_cluster_modifications_complete.wait(DBClusterIdentifier=db_cluster_identifier)
    resp = rds.describe_db_clusters(DBClusterIdentifier=db_cluster_identifier)
    db_cluster = resp["DBClusters"][0]
    assert "MasterUserSecret" not in db_cluster
    # Secret should be deleted
    master_user_secret_deleted.wait(SecretId=secret_arn)
    with pytest.raises(ClientError) as exc:
        secretsmanager.describe_secret(SecretId=secret_arn)
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"

    # Re-enable password management, this time with a custom KMS key
    resp = rds.modify_db_cluster(
        DBClusterIdentifier=db_cluster_identifier,
        ManageMasterUserPassword=True,
        MasterUserSecretKmsKeyId=custom_kms_key_arn,
        ApplyImmediately=True,
    )
    db_cluster = resp["DBCluster"]
    # TODO: This passes on AWS but is not implemented yet in moto
    # assert "MasterUserPassword" in db_cluster["PendingModifiedValues"]
    master_user_secret = db_cluster["MasterUserSecret"]
    assert master_user_secret["KmsKeyId"] == custom_kms_key_arn
    assert master_user_secret["SecretStatus"] == "creating"
    # Check the secret in SecretsManager
    secret_arn = master_user_secret["SecretArn"]
    master_user_secret_available.wait(DBClusterIdentifier=db_cluster_identifier)
    secret = secretsmanager.describe_secret(SecretId=secret_arn)
    assert str(secret["Name"]).startswith("rds!cluster")
    assert secret["OwningService"] == "rds"
    # Check that RDS sees the secret as active
    db_cluster_modifications_complete.wait(DBClusterIdentifier=db_cluster_identifier)
    resp = rds.describe_db_clusters(DBClusterIdentifier=db_cluster_identifier)
    db_cluster = resp["DBClusters"][0]
    master_user_secret = db_cluster["MasterUserSecret"]
    assert master_user_secret["SecretStatus"] == "active"

    # Rotate managed password
    resp = rds.modify_db_cluster(
        DBClusterIdentifier=db_cluster_identifier,
        RotateMasterUserPassword=True,
        ApplyImmediately=True,
    )
    db_cluster = resp["DBCluster"]
    master_user_secret = db_cluster["MasterUserSecret"]
    assert master_user_secret["SecretStatus"] == "rotating"
    # Check that RDS sees the secret as active after rotation
    master_user_secret_available.wait(DBClusterIdentifier=db_cluster_identifier)
    resp = rds.describe_db_clusters(DBClusterIdentifier=db_cluster_identifier)
    db_cluster = resp["DBClusters"][0]
    master_user_secret = db_cluster["MasterUserSecret"]
    assert master_user_secret["SecretStatus"] == "active"

    # Delete the cluster
    resp = rds.delete_db_cluster(
        DBClusterIdentifier=db_cluster_identifier,
        SkipFinalSnapshot=True,
        DeleteAutomatedBackups=True,
    )
    db_cluster = resp["DBCluster"]
    assert "MasterUserSecret" in db_cluster
    # Deleting the cluster should delete the secret
    db_cluster_deleted.wait(DBClusterIdentifier=db_cluster_identifier)
    master_user_secret_deleted.wait(SecretId=secret_arn)
    with pytest.raises(ClientError) as exc:
        secretsmanager.describe_secret(SecretId=secret_arn)
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"
    # Delete the custom KMS key we created
    kms.schedule_key_deletion(KeyId=custom_kms_key_id, PendingWindowInDays=7)


@aws_verified
@pytest.mark.aws_verified
def test_db_instance_managed_master_user_password_lifecycle():
    # Clients
    kms = boto3.client("kms", region_name=DEFAULT_REGION)
    rds = boto3.client("rds", region_name=DEFAULT_REGION)
    secretsmanager = boto3.client("secretsmanager", region_name=DEFAULT_REGION)

    # Waiters
    db_instance_modifications_complete = get_custom_waiter(
        "db_instance_modifications_complete", rds
    )
    db_instance_available = rds.get_waiter("db_instance_available")
    db_instance_deleted = rds.get_waiter("db_instance_deleted")
    master_user_secret_available = get_custom_waiter(
        "db_instance_master_user_secret_available", rds
    )
    master_user_secret_deleted = get_custom_waiter("secret_deleted", secretsmanager)

    # KMS keys
    resp = kms.describe_key(KeyId="alias/aws/secretsmanager")
    default_kms_key_arn = resp["KeyMetadata"]["Arn"]
    resp = kms.create_key(KeyUsage="ENCRYPT_DECRYPT", KeySpec="SYMMETRIC_DEFAULT")
    custom_kms_key_arn = resp["KeyMetadata"]["Arn"]
    custom_kms_key_id = resp["KeyMetadata"]["KeyId"]

    # Create DBInstance with managed master user password
    db_instance_identifier = "test-" + str(uuid.uuid4())
    resp = rds.create_db_instance(
        AllocatedStorage=200,
        DBInstanceIdentifier=db_instance_identifier,
        DBInstanceClass="db.m7g.large",
        Engine="postgres",
        MasterUsername="root",
        ManageMasterUserPassword=True,
    )
    db_instance = resp["DBInstance"]
    master_user_secret = db_instance["MasterUserSecret"]
    assert master_user_secret["KmsKeyId"] == default_kms_key_arn
    assert master_user_secret["SecretStatus"] == "creating"
    # Check the secret in SecretsManager
    secret_arn = master_user_secret["SecretArn"]
    master_user_secret_available.wait(DBInstanceIdentifier=db_instance_identifier)
    secret = secretsmanager.describe_secret(SecretId=secret_arn)
    assert str(secret["Name"]).startswith("rds!db")
    assert secret["OwningService"] == "rds"
    # Check that RDS sees the secret as active
    db_instance_available.wait(DBInstanceIdentifier=db_instance_identifier)
    resp = rds.describe_db_instances(DBInstanceIdentifier=db_instance_identifier)
    db_instance = resp["DBInstances"][0]
    master_user_secret = db_instance["MasterUserSecret"]
    assert master_user_secret["SecretStatus"] == "active"
    # Check that managed secret has correct structure
    resp = secretsmanager.get_secret_value(SecretId=secret_arn)
    secret = json.loads(resp["SecretString"])
    assert "username" in secret
    assert "password" in secret

    # Disable password management
    resp = rds.modify_db_instance(
        DBInstanceIdentifier=db_instance_identifier,
        ManageMasterUserPassword=False,
        MasterUserPassword="Non-Managed-Pa55word!",
        ApplyImmediately=True,
    )
    db_instance = resp["DBInstance"]
    # TODO: This passes on AWS but is not implemented yet in moto
    # assert "MasterUserPassword" in db_cluster["PendingModifiedValues"]
    db_instance_modifications_complete.wait(DBInstanceIdentifier=db_instance_identifier)
    resp = rds.describe_db_instances(DBInstanceIdentifier=db_instance_identifier)
    db_instance = resp["DBInstances"][0]
    assert "MasterUserSecret" not in db_instance
    # Secret should be deleted
    master_user_secret_deleted.wait(SecretId=secret_arn)
    with pytest.raises(ClientError) as exc:
        secretsmanager.describe_secret(SecretId=secret_arn)
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"

    # Re-enable password management, this time with a custom KMS key
    resp = rds.modify_db_instance(
        DBInstanceIdentifier=db_instance_identifier,
        ManageMasterUserPassword=True,
        MasterUserSecretKmsKeyId=custom_kms_key_arn,
        ApplyImmediately=True,
    )
    db_instance = resp["DBInstance"]
    # TODO: This passes on AWS but not implemented yet in moto
    # assert "MasterUserPassword" in db_cluster["PendingModifiedValues"]
    master_user_secret = db_instance["MasterUserSecret"]
    assert master_user_secret["KmsKeyId"] == custom_kms_key_arn
    assert master_user_secret["SecretStatus"] == "creating"
    # Check the secret in SecretsManager
    secret_arn = master_user_secret["SecretArn"]
    master_user_secret_available.wait(DBInstanceIdentifier=db_instance_identifier)
    secret = secretsmanager.describe_secret(SecretId=secret_arn)
    assert str(secret["Name"]).startswith("rds!db")
    assert secret["OwningService"] == "rds"
    # Check that RDS sees the secret as active
    db_instance_modifications_complete.wait(DBInstanceIdentifier=db_instance_identifier)
    resp = rds.describe_db_instances(DBInstanceIdentifier=db_instance_identifier)
    db_instance = resp["DBInstances"][0]
    master_user_secret = db_instance["MasterUserSecret"]
    assert master_user_secret["SecretStatus"] == "active"

    # Rotate managed password
    resp = rds.modify_db_instance(
        DBInstanceIdentifier=db_instance_identifier,
        RotateMasterUserPassword=True,
        ApplyImmediately=True,
    )
    db_instance = resp["DBInstance"]
    master_user_secret = db_instance["MasterUserSecret"]
    assert master_user_secret["SecretStatus"] == "rotating"
    # Check that RDS sees the secret as active after rotation
    master_user_secret_available.wait(DBInstanceIdentifier=db_instance_identifier)
    resp = rds.describe_db_instances(DBInstanceIdentifier=db_instance_identifier)
    db_instance = resp["DBInstances"][0]
    master_user_secret = db_instance["MasterUserSecret"]
    assert master_user_secret["SecretStatus"] == "active"

    # Delete the instance
    resp = rds.delete_db_instance(
        DBInstanceIdentifier=db_instance_identifier,
        SkipFinalSnapshot=True,
        DeleteAutomatedBackups=True,
    )
    db_instance = resp["DBInstance"]
    assert "MasterUserSecret" in db_instance
    # Deleting the instance should delete the secret
    db_instance_deleted.wait(DBInstanceIdentifier=db_instance_identifier)
    master_user_secret_deleted.wait(SecretId=secret_arn)
    with pytest.raises(ClientError) as exc:
        secretsmanager.describe_secret(SecretId=secret_arn)
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"
    # Delete the custom KMS key we created
    kms.schedule_key_deletion(KeyId=custom_kms_key_id, PendingWindowInDays=7)


def get_custom_waiter(waiter_name, client):
    """Some useful waiters that are not present in botocore."""
    config = {
        "version": 2,
        "waiters": {
            "DBClusterModificationsComplete": {
                "delay": 15,
                "operation": "DescribeDBClusters",
                "maxAttempts": 60,
                "acceptors": [
                    {
                        "state": "success",
                        "matcher": "path",
                        "argument": "contains(keys(DBClusters[0]), 'PendingModifiedValues') && length(DBClusters[0].PendingModifiedValues) == `0`",
                        "expected": True,
                    },
                    {
                        "state": "success",
                        "matcher": "path",
                        "argument": "contains(keys(DBClusters[0]), 'PendingModifiedValues')",
                        "expected": False,
                    },
                ],
            },
            "DBClusterMasterUserSecretAvailable": {
                "delay": 15,
                "operation": "DescribeDBClusters",
                "maxAttempts": 60,
                "acceptors": [
                    {
                        "expected": "active",
                        "matcher": "pathAll",
                        "state": "success",
                        "argument": "DBClusters[].MasterUserSecret.SecretStatus",
                    },
                ],
            },
            "DBInstanceModificationsComplete": {
                "delay": 15,
                "operation": "DescribeDBInstances",
                "maxAttempts": 60,
                "acceptors": [
                    {
                        "state": "success",
                        "matcher": "path",
                        "argument": "contains(keys(DBInstances[0]), 'PendingModifiedValues') && length(DBInstances[0].PendingModifiedValues) == `0`",
                        "expected": True,
                    },
                    {
                        "state": "success",
                        "matcher": "path",
                        "argument": "contains(keys(DBInstances[0]), 'PendingModifiedValues')",
                        "expected": False,
                    },
                ],
            },
            "DBInstanceMasterUserSecretAvailable": {
                "delay": 15,
                "operation": "DescribeDBInstances",
                "maxAttempts": 60,
                "acceptors": [
                    {
                        "expected": "active",
                        "matcher": "pathAll",
                        "state": "success",
                        "argument": "DBInstances[].MasterUserSecret.SecretStatus",
                    },
                ],
            },
            "SecretDeleted": {
                "delay": 15,
                "operation": "DescribeSecret",
                "maxAttempts": 60,
                "acceptors": [
                    {
                        "expected": "ResourceNotFoundException",
                        "matcher": "error",
                        "state": "success",
                    },
                ],
            },
        },
    }
    model = waiter.WaiterModel(config)
    mapping = {}
    for name in model.waiter_names:
        mapping[xform_name(name)] = name
    return waiter.create_waiter_with_client(mapping[waiter_name], model, client)
