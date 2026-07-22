"""Unit tests for paymentcryptography-supported APIs."""

from datetime import datetime

import boto3
from botocore.exceptions import ClientError
import json
import pytest

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

KEY_ATTRIBUTES_1 = {
    "KeyUsage": "TR31_P0_PIN_ENCRYPTION_KEY",
    "KeyClass": "SYMMETRIC",
    "KeyAlgorithm": "TDES_3KEY",
    "KeyModesOfUse": {
        "Encrypt": True,
        "Decrypt": True,
        "Wrap": True,
        "Unwrap": True,
        "Generate": True,
        "Sign": True,
        "Verify": True,
        "DeriveKey": True,
        "NoRestrictions": False,
    },
}

def _sample_policy(key_arn):
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AllowCrossAccountKeyUsage",
                "Effect": "Allow",
                "Principal": {
                    "AWS": "arn:aws:iam:123456789012:role/PaymentProcessingRole"
                },
                "Action": [
                    "payment-cryptography:GetKey",
                    "payment-cryptography:EncryptData",
                    "payment-cryptography:DecryptData",
                ],
                "Resource": key_arn,
            }
        ]
    }
    return json.dumps(policy)

@mock_aws
def test_create_key():
    client = boto3.client("payment-cryptography", region_name="us-east-1")

    key = client.create_key(
        KeyAttributes=KEY_ATTRIBUTES_1,
        Exportable=True,
        Enabled=True,
        Tags=[
            {"Key": "Environment", "Value": "Test"},
        ],
        DeriveKeyUsage="TR31_P0_PIN_ENCRYPTION_KEY",
    )["Key"]

    assert key["KeyArn"].startswith(
        f"arn:aws:payment-cryptography:us-east-1:{ACCOUNT_ID}:key/"
    )
    assert key["KeyAttributes"] == KEY_ATTRIBUTES_1
    assert key["Exportable"] is True
    assert key["Enabled"] is True
    assert key["KeyCheckValue"] is not None
    assert key["KeyCheckValueAlgorithm"] is not None
    assert key["KeyState"] == "CREATE_COMPLETE"
    assert key["KeyOrigin"] == "AWS_PAYMENT_CRYPTOGRAPHY"
    assert key["DeriveKeyUsage"] == "TR31_P0_PIN_ENCRYPTION_KEY"
    assert isinstance(key["CreateTimestamp"], datetime)


@mock_aws
def test_create_key_with_replica_regions():
    client = boto3.client("payment-cryptography", region_name="us-east-1")

    key = client.create_key(
        KeyAttributes=KEY_ATTRIBUTES_1,
        Exportable=True,
        Enabled = True,
        Tags = [
            {"Key": "Environment", "Value": "Test"},
        ],
        DeriveKeyUsage="TR31_P0_PIN_ENCRYPTION_KEY",
        ReplicationRegions=[
            "us-west-2",
            "eu-west-1",
        ]
    )["Key"]

    assert key["MultiRegionKeyType"] == "PRIMARY"
    assert key["PrimaryRegion"] == "us-east-1"
    assert key["UsingDefaultReplicationRegions"] is False
    assert key["ReplicationStatus"] == {
        "us-west-2": {"Status": "SYNCHRONIZED"},
        "eu-west-1": {"Status": "SYNCHRONIZED"},
    }


@mock_aws
def test_get_key():
    client = boto3.client("payment-cryptography", region_name="us-east-1")

    key = client.create_key(
        KeyAttributes=KEY_ATTRIBUTES_1,
        Exportable=True,
        Enabled = True,
        Tags = [
            {"Key": "Environment", "Value": "Test"},
        ],
        DeriveKeyUsage="TR31_P0_PIN_ENCRYPTION_KEY"
    )["Key"]

    key_arn = key["KeyArn"]
    retrieved_key = client.get_key(KeyIdentifier=key_arn)["Key"]
    # retrieved_key = retrieved_json.get("Key")

    assert retrieved_key["KeyArn"] == key_arn
    assert retrieved_key["KeyAttributes"] == KEY_ATTRIBUTES_1
    assert retrieved_key["Exportable"] is True
    assert retrieved_key["Enabled"] is True
    assert retrieved_key["KeyCheckValue"] is not None
    assert retrieved_key["KeyCheckValueAlgorithm"] is not None
    assert retrieved_key["KeyState"] == "CREATE_COMPLETE"
    assert retrieved_key["KeyOrigin"] == "AWS_PAYMENT_CRYPTOGRAPHY"
    assert retrieved_key["DeriveKeyUsage"] == "TR31_P0_PIN_ENCRYPTION_KEY"
    assert isinstance(key["CreateTimestamp"], datetime)


# @mock_aws
# def test_enable_default_key_replication_regions():
#     client = boto3.client("payment-cryptography", region_name="us-east-1")

#     # Enable default replication regions
#     key_replication_regions = client.enable_default_key_replication_regions(
#         ReplicationRegions=[
#             "ap-southeast-1",
#         ]
#     )

#     # Include default and newly added replication region
#     assert key_replication_regions["EnabledReplicationRegions"] == [
#         "us-west-2",
#         "eu-west-1",
#         "ap-southeast-1",
#     ]


# @mock_aws
# def test_get_default_key_replication_regions():
#     client = boto3.client("payment-cryptography", region_name="us-east-1")

#     default_regions = client.get_default_key_replication_regions()["EnabledReplicationRegions"]
#     assert "us-west-2" in default_regions
#     assert "eu-west-1" in default_regions


# @mock_aws
# def test_disable_default_key_replication_regions():
#     client = boto3.client("payment-cryptography", region_name="us-east-1")

#     # Disable default replication regions
#     key_replication_regions = client.disable_default_key_replication_regions(
#         ReplicationRegions=[
#             "us-west-2",
#         ]
#     )

#     # Check that the specified region is removed from the enabled replication regions
#     assert "us-west-2" not in key_replication_regions["EnabledReplicationRegions"]


# @mock_aws
# def test_create_alias():
#     client = boto3.client("payment-cryptography", region_name="us-east-1")

#     key = client.create_key(
#         KeyAttributes=KEY_ATTRIBUTES_1,
#         Exportable=True,
#         Enabled = True,
#         Tags = [
#             {"Key": "Environment", "Value": "Test"},
#         ],
#         DeriveKeyUsage="TR31_P0_PIN_ENCRYPTION_KEY",
#         MultiRegionKeyType="PRIMARY",
#     )["Key"]

#     key_arn = key["KeyArn"]

#     # Create an alias for the key
#     alias_name = "alias/my-key-alias"
#     client.create_alias(
#         AliasName=alias_name,
#         KeyArn=key_arn
#     )

#     # Retrieve the alias and check its properties
#     alias = client.list_aliases()["Aliases"]
#     assert alias["AliasName"] == alias_name
#     assert alias["KeyArn"] == key_arn


# @mock_aws
# def test_get_alias():
#     client = boto3.client("payment-cryptography", region_name="us-east-1")

#     key = client.create_key(
#         KeyAttributes=KEY_ATTRIBUTES_1,
#         Exportable=True,
#         Enabled = True,
#         Tags = [
#             {"Key": "Environment", "Value": "Test"},
#         ],
#         DeriveKeyUsage="TR31_P0_PIN_ENCRYPTION_KEY",
#         MultiRegionKeyType="PRIMARY",
#     )["Key"]

#     key_arn = key["KeyArn"]

#     # Create an alias for the key
#     alias_name = "alias/my-key-alias"
#     client.create_alias(
#         AliasName=alias_name,
#         KeyArn=key_arn
#     )

#     retrieved_alias = client.get_alias(AliasName=alias_name)
#     assert retrieved_alias["AliasName"] == alias_name
#     assert retrieved_alias["KeyArn"] == key_arn


# @mock_aws
# def test_update_alias():
#     client = boto3.client("payment-cryptography", region_name="us-east-1")

#     key = client.create_key(
#         KeyAttributes=KEY_ATTRIBUTES_1,
#         Exportable=True,
#         Enabled = True,
#         Tags = [
#             {"Key": "Environment", "Value": "Test"},
#         ],
#         DeriveKeyUsage="TR31_P0_PIN_ENCRYPTION_KEY",
#         MultiRegionKeyType="PRIMARY",
#     )["Key"]

#     # Create an alias for the key
#     alias_name = "alias/my-key-alias"
#     client.create_alias(
#         AliasName=alias_name,
#         KeyArn=key["KeyArn"]
#     )

#     # Check alias for the key
#     retrieved_alias = client.get_alias(AliasName=alias_name)
#     assert retrieved_alias["AliasName"] == alias_name

#     # Update the alias
#     new_alias_name = "alias/my-updated-key-alias"

#     client.update_alias(
#         AliasName=new_alias_name,
#         KeyArn=key["KeyArn"],
#     )

#     # Check key for the updated alias
#     updated_alias = client.get_alias(AliasName=new_alias_name)
#     assert updated_alias["AliasName"] == new_alias_name


# @mock_aws
# def test_delete_alias():
#     client = boto3.client("payment-cryptography", region_name="us-east-1")

#     key = client.create_key(
#         KeyAttributes=KEY_ATTRIBUTES_1,
#         Exportable=True,
#         Enabled = True,
#         Tags = [
#             {"Key": "Environment", "Value": "Test"},
#         ],
#         DeriveKeyUsage="TR31_P0_PIN_ENCRYPTION_KEY",
#         MultiRegionKeyType="PRIMARY",
#     )["Key"]

#     key_arn = key["KeyArn"]

#     # Create an alias for the key
#     alias_name = "alias/my-key-alias"
#     client.create_alias(
#         AliasName=alias_name,
#         KeyArn=key_arn
#     )

#     # Delete the alias
#     client.delete_alias(AliasName=alias_name)

#     # Check that the alias no longer exists
#     aliases_list = client.list_aliases()["Aliases"]
#     assert all(alias["AliasName"] != alias_name for alias in aliases_list)


# @mock_aws
# def test_list_aliases():
#     client = boto3.client("payment-cryptography", region_name="us-east-1")

#     key1 = client.create_key(
#         KeyAttributes=KEY_ATTRIBUTES_1,
#         Exportable=True,
#         Enabled = True,
#         Tags = [
#             {"Key": "Environment", "Value": "Test"},
#         ],
#         DeriveKeyUsage="TR31_P0_PIN_ENCRYPTION_KEY",
#         MultiRegionKeyType="PRIMARY",
#     )["Key"]

#     key2 = client.create_key(
#         KeyAttributes=KEY_ATTRIBUTES_1,
#         Exportable=True,
#         Enabled = True,
#         Tags = [
#             {"Key": "Environment", "Value": "Test"},
#         ],
#         DeriveKeyUsage="TR31_P0_PIN_ENCRYPTION_KEY",
#         MultiRegionKeyType="PRIMARY",
#     )["Key"]

#     # Create aliases for the keys
#     alias_name1 = "alias/my-key-alias-1"
#     alias_name2 = "alias/my-key-alias-2"
#     client.create_alias(
#         AliasName=alias_name1,
#         KeyArn=key1["KeyArn"]
#     )
#     client.create_alias(
#         AliasName=alias_name2,
#         KeyArn=key2["KeyArn"]
#     )

#     aliases_list = client.list_aliases()["Aliases"]
#     assert len(aliases_list) == 2
#     assert any(alias["AliasName"] == alias_name1 for alias in aliases_list)
#     assert any(alias["AliasName"] == alias_name2 for alias in aliases_list)


# @mock_aws
# def test_put_resource_policy():
#     client = boto3.client("payment-cryptography", region_name="us-east-1")

#     key = client.create_key(
#         KeyAttributes=KEY_ATTRIBUTES_1,
#         Exportable=True,
#         Enabled = True,
#         Tags = [
#             {"Key": "Environment", "Value": "Test"},
#         ],
#         DeriveKeyUsage="TR31_P0_PIN_ENCRYPTION_KEY",
#         MultiRegionKeyType="PRIMARY",
#     )["Key"]

#     key_arn = key["KeyArn"]

#     # Put a resource policy for the key
#     policy = {
#         "Version": "2012-10-17",
#         "Statement": [
#             {
#                 "Effect": "Allow",
#                 "Principal": {"AWS": "*"},
#                 "Action": "paymentcryptography:GetKey",
#                 "Resource": key_arn,
#             }
#         ],
#     }
#     client.put_resource_policy(
#         ResourceArn=key_arn,
#         Policy=json.dumps(policy)
#     )

#     # Retrieve the resource policy and check its content
#     retrieved_policy = client.get_resource_policy(ResourceArn=key_arn)["Policy"]
#     assert json.loads(retrieved_policy) == policy


# @mock_aws
# def test_delete_resource_policy():
#     client = boto3.client("payment-cryptography", region_name="us-east-1")

#     key = client.create_key(
#         KeyAttributes=KEY_ATTRIBUTES_1,
#         Exportable=True,
#         Enabled = True,
#         Tags = [
#             {"Key": "Environment", "Value": "Test"},
#         ],
#         DeriveKeyUsage="TR31_P0_PIN_ENCRYPTION_KEY",
#         MultiRegionKeyType="PRIMARY",
#     )["Key"]

#     key_arn = key["KeyArn"]

#     # Put a resource policy for the key
#     policy = {
#         "Version": "2012-10-17",
#         "Statement": [
#             {
#                 "Effect": "Allow",
#                 "Principal": {"AWS": "*"},
#                 "Action": "paymentcryptography:GetKey",
#                 "Resource": key_arn,
#             }
#         ],
#     }
#     client.put_resource_policy(
#         ResourceArn=key_arn,
#         Policy=json.dumps(policy)
#     )

#     # Delete the resource policy
#     client.delete_resource_policy(ResourceArn=key_arn)

#     # Check that the resource policy no longer exists
#     with pytest.raises(ClientError) as exc:
#         client.get_resource_policy(ResourceArn=key_arn)
#     err = exc.value.response["Error"]
#     assert err["Code"] == "ResourceNotFoundException"


# @mock_aws
# def test_start_key_usage():
#     client = boto3.client("payment-cryptography", region_name="us-east-1")

#     # Initially disabled
#     key = client.create_key(
#         KeyAttributes=KEY_ATTRIBUTES_1,
#         Exportable=True,
#         Enabled = False,
#         Tags = [
#             {"Key": "Environment", "Value": "Test"},
#         ],
#         DeriveKeyUsage="TR31_P0_PIN_ENCRYPTION_KEY",
#         MultiRegionKeyType="PRIMARY",
#     )["Key"]

#     key_arn = key["KeyArn"]

#     # Start key usage
#     client.start_key_usage(KeyArn=key_arn)

#     # Retrieve the key and check its state
#     updated_key = client.get_key(KeyArn=key_arn)["Key"]
#     assert updated_key["KeyState"] == "ENABLED"

# @mock_aws
# def test_stop_key_usage():
#     client = boto3.client("payment-cryptography", region_name="us-east-1")

#     # Initially enabled
#     key = client.create_key(
#         KeyAttributes=KEY_ATTRIBUTES_1,
#         Exportable=True,
#         Enabled = True,
#         Tags = [
#             {"Key": "Environment", "Value": "Test"},
#         ],
#         DeriveKeyUsage="TR31_P0_PIN_ENCRYPTION_KEY",
#         MultiRegionKeyType="PRIMARY",
#     )["Key"]

#     key_arn = key["KeyArn"]

#     # Stop key usage
#     client.stop_key_usage(KeyArn=key_arn)

#     # Retrieve the key and check its state
#     updated_key = client.get_key(KeyArn=key_arn)["Key"]
#     assert updated_key["KeyState"] == "DISABLED"


@mock_aws
def test_list_keys_single_region():
    client = boto3.client("payment-cryptography", region_name="us-east-1")

    client.create_key(
        KeyAttributes=KEY_ATTRIBUTES_1,
        Exportable=True,
        Enabled=True,
        Tags=[
            {"Key": "Environment", "Value": "Test"},
        ],
        DeriveKeyUsage="TR31_P0_PIN_ENCRYPTION_KEY",
    )

    list_key_resp = client.list_keys()["Keys"]
    key = list_key_resp[0]

    assert len(list_key_resp) == 1
    assert key["KeyArn"].startswith(
        f"arn:aws:payment-cryptography:us-east-1:{ACCOUNT_ID}:key/"
    )
    assert key["KeyAttributes"] == KEY_ATTRIBUTES_1
    assert key["Exportable"] is True
    assert key["Enabled"] is True
    assert key["KeyCheckValue"] is not None
    assert key["KeyState"] == "CREATE_COMPLETE"

@mock_aws
def test_list_tags_for_resource():
    client = boto3.client("payment-cryptography", region_name="us-east-1")

    key = client.create_key(
        KeyAttributes=KEY_ATTRIBUTES_1,
        Exportable=True,
        Enabled=True,
        Tags=[
            {"Key": "Environment", "Value": "Test"},
        ],
        DeriveKeyUsage="TR31_P0_PIN_ENCRYPTION_KEY",
    )["Key"]

    list_tags_resp = client.list_tags_for_resource(ResourceArn=key["KeyArn"])
    assert list_tags_resp['Tags'] == [
            {"Key": "Environment", "Value": "Test"},
        ]

@mock_aws
def test_tag_resource():
    client = boto3.client("payment-cryptography", region_name="us-east-1")

    key = client.create_key(
        KeyAttributes=KEY_ATTRIBUTES_1,
        Exportable=True,
        Enabled = True,
        Tags = [
            {"Key": "Environment", "Value": "Test"},
        ],
        DeriveKeyUsage="TR31_P0_PIN_ENCRYPTION_KEY"
    )["Key"]

    key_arn = key["KeyArn"]

    # Tag the key with additional tags
    client.tag_resource(
        ResourceArn=key_arn,
        Tags=[
            {"Key": "foo", "Value": "1"},
            {"Key": "bar", "Value": "2"},
        ]
    )

    # Retrieve the key and check the tags with list_tags_for_resource
    retrieved_key = client.list_tags_for_resource(ResourceArn=key_arn)["Tags"]
    assert len(retrieved_key) == 3  # Original tag + 2 new tags
    assert {"Key": "Environment", "Value": "Test"} in retrieved_key
    assert {"Key": "foo", "Value": "1"} in retrieved_key
    assert {"Key": "bar", "Value": "2"} in retrieved_key




@mock_aws
def test_untag_resource():
    client = boto3.client("payment-cryptography", region_name="ap-southeast-1")

    key = client.create_key(
        KeyAttributes=KEY_ATTRIBUTES_1,
        Exportable=True,
        Enabled = True,
        Tags = [
            {"Key": "Environment", "Value": "Test"},
            {"Key": "foo", "Value": "1"},
            {"Key": "bar", "Value": "2"}
        ],
        DeriveKeyUsage="TR31_P0_PIN_ENCRYPTION_KEY"
    )["Key"]

    key_arn = key["KeyArn"]

    # Untag the key
    client.untag_resource(
        ResourceArn=key_arn,
        TagKeys=["foo", "bar"]
    )

    # Retrieve the key and check the tags
    retrieved_key_after_untag = client.list_tags_for_resource(ResourceArn=key_arn)["Tags"]
    assert len(retrieved_key_after_untag) == 1
    assert {"Key": "Environment", "Value": "Test"} in retrieved_key_after_untag


@mock_aws
def test_delete_key():
    client = boto3.client("payment-cryptography", region_name="us-east-1")

    key = client.create_key(
        KeyAttributes=KEY_ATTRIBUTES_1,
        Exportable=True,
        Enabled=True,
        Tags=[
            {"Key": "Environment", "Value": "Test"},
        ],
        DeriveKeyUsage="TR31_P0_PIN_ENCRYPTION_KEY"
    )["Key"]

    key_arn = key["KeyArn"]

    # Delete the key
    deleted = client.delete_key(KeyIdentifier=key_arn)["Key"]
    assert deleted["KeyState"] == "DELETE_PENDING"
    assert deleted["Enabled"] is False
    assert isinstance(deleted["DeletePendingTimestamp"], datetime)

    retrieved = client.get_key(KeyIdentifier=key_arn)["Key"]
    assert retrieved["KeyState"] == "DELETE_PENDING"
    assert retrieved["Enabled"] is False


@mock_aws
def test_delete_key_not_found():
    client = boto3.client("payment-cryptography", region_name="us-east-1")

    missing_arn = f"arn:aws:payment-cryptography:us-east-1:{ACCOUNT_ID}:key/doesnotexist123"
    with pytest.raises(ClientError) as exc:
        client.delete_key(KeyIdentifier=missing_arn)
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_put_resource_policy():
    client = boto3.client("payment-cryptography", region_name="us-east-1")

    key = client.create_key(
        KeyAttributes=KEY_ATTRIBUTES_1,
        Exportable=True,
        Enabled=True,
        Tags=[
            {"Key": "Environment", "Value": "Test"},
        ],
        DeriveKeyUsage="TR31_P0_PIN_ENCRYPTION_KEY",
    )["Key"]

    key_arn = key["KeyArn"]

    put_resp = client.put_resource_policy(ResourceArn=key_arn, Policy=_sample_policy(key_arn))

    assert put_resp["ResourceArn"] == key_arn
    assert json.loads(put_resp["Policy"]) == json.loads(_sample_policy(key_arn))

    get_resp = client.get_resource_policy(ResourceArn=key_arn)
    assert get_resp["ResourceArn"] == key_arn
    assert json.loads(get_resp["Policy"]) == json.loads(_sample_policy(key_arn))


@mock_aws
def test_put_resource_policy_key_not_found():
    client = boto3.client("payment-cryptography", region_name="us-east-1")
    missing_arn = f"arn:aws:payment-cryptography:us-east-1:{ACCOUNT_ID}:key/doesnotexist123"

    with pytest.raises(ClientError) as exc:
        client.put_resource_policy(ResourceArn=missing_arn, Policy="{}")
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_get_resource_policy_when_none_set():
    client = boto3.client("payment-cryptography", region_name="us-east-1")

    key = client.create_key(
        KeyAttributes=KEY_ATTRIBUTES_1,
        Exportable=True,
        Enabled=True,
        Tags=[
            {"Key": "Environment", "Value": "Test"},
        ],
        DeriveKeyUsage="TR31_P0_PIN_ENCRYPTION_KEY",
    )["Key"]

    key_arn = key["KeyArn"]

    # The key exists but has no attached policy. Return an empty response
    get_resp = client.get_resource_policy(ResourceArn=key_arn)
    assert get_resp["ResourceArn"] == key_arn
    assert json.loads(get_resp["Policy"]) == {}

@mock_aws
def test_get_resource_policy_key_not_found():
    client = boto3.client("payment-cryptography", region_name="us-east-1")
    missing_arn = f"arn:aws:payment-cryptography:us-east-1:{ACCOUNT_ID}:key/doesnotexist123"

    with pytest.raises(ClientError) as exc:
        client.get_resource_policy(ResourceArn=missing_arn)
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_delete_resource_policy():
    client = boto3.client("payment-cryptography", region_name="us-east-1")

    key = client.create_key(
        KeyAttributes=KEY_ATTRIBUTES_1,
        Exportable=True,
        Enabled=True,
        Tags=[
            {"Key": "Environment", "Value": "Test"},
        ],
        DeriveKeyUsage="TR31_P0_PIN_ENCRYPTION_KEY",
    )["Key"]

    key_arn = key["KeyArn"]

    client.put_resource_policy(ResourceArn=key_arn, Policy=_sample_policy(key_arn))

    client.delete_resource_policy(ResourceArn=key_arn)
    get_resp = client.get_resource_policy(ResourceArn=key_arn)
    assert get_resp["ResourceArn"] == key_arn
    assert json.loads(get_resp["Policy"]) == {}


@mock_aws
def test_add_key_replication_regions():
    primary_client = boto3.client("payment-cryptography", region_name="us-east-1")

    key = primary_client.create_key(
        KeyAttributes=KEY_ATTRIBUTES_1,
        Exportable=True,
        Enabled = True,
        Tags = [
            {"Key": "Environment", "Value": "Test"},
        ],
        DeriveKeyUsage="TR31_P0_PIN_ENCRYPTION_KEY",
    )["Key"]

    key_arn = key["KeyArn"]
    key_id = key_arn.split(":key/")[1]

    # Add replication regions to the key
    primary_key = primary_client.add_key_replication_regions(
        KeyIdentifier=key_arn,
        ReplicationRegions=[
            "us-west-2",
            "eu-west-1",
        ]
    )["Key"]

    assert primary_key["MultiRegionKeyType"] == "PRIMARY"
    assert primary_key["PrimaryRegion"] == "us-east-1"
    assert primary_key["UsingDefaultReplicationRegions"] is False
    assert primary_key["ReplicationStatus"] == {
        "us-west-2": {"Status": "SYNCHRONIZED"},
        "eu-west-1": {"Status": "SYNCHRONIZED"},
    }

    replica_client = boto3.client("payment-cryptography", region_name="us-west-2")
    replica_arn = f"arn:aws:payment-cryptography:us-west-2:{ACCOUNT_ID}:key/{key_id}"
    replica_key = replica_client.get_key(KeyIdentifier=replica_arn)["Key"]
    assert replica_key["MultiRegionKeyType"] == "REPLICA"
    assert replica_key["PrimaryRegion"] == "us-east-1"

    replica_client_eu = boto3.client("payment-cryptography", region_name="eu-west-1")
    replica_arn_eu = f"arn:aws:payment-cryptography:eu-west-1:{ACCOUNT_ID}:key/{key_id}"
    replica_key_eu = replica_client_eu.get_key(KeyIdentifier=replica_arn_eu)["Key"]
    assert replica_key_eu["MultiRegionKeyType"] == "REPLICA"
    assert replica_key_eu["PrimaryRegion"] == "us-east-1"
