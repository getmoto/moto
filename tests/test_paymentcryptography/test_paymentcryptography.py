"""Unit tests for paymentcryptography-supported APIs."""

from datetime import datetime

import boto3

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


# @mock_aws
# def test_create_key_with_replica_regions():
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
#         ReplicationRegions=[
#             "us-west-2",
#             "eu-west-1",
#         ]
#     )["Key"]

#     assert key["MultiRegionKeyType"] == "PRIMARY"
#     assert key["PrimaryRegion"] == "us-east-1"
#     assert key["UsingDefaultReplicationRegions"] is False
#     assert key["ReplicationStatus"] == {
#         "us-west-2": {"Status": "SYNCHRONIZED"},
#         "eu-west-1": {"Status": "SYNCHRONIZED"},
#     }


# @mock_aws
# def test_get_key():
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

#     retrieved_key = client.get_key(KeyArn=key_arn)["Key"]

#     assert retrieved_key["KeyArn"] == key_arn
#     assert key["KeyAttributes"] == KEY_ATTRIBUTES_1
#     assert key["Exportable"] is True
#     assert key["Enabled"] is True
#     assert key["KeyCheckValue"] is not None
#     assert key["KeyCheckValueAlgorithm"] is not None
#     assert key["KeyState"] == "CREATE_COMPLETE"
#     assert key["KeyOrigin"] == "AWS_PAYMENT_CRYPTOGRAPHY"
#     assert key["DeriveKeyUsage"] == "TR31_P0_PIN_ENCRYPTION_KEY"
#     assert isinstance(key["CreateTimestamp"], datetime)


# @mock_aws
# def test_delete_key():
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

#     # Delete the key
#     client.delete_key(KeyArn=key_arn)

#     # Check that the key no longer exists
#     with pytest.raises(ClientError) as exc:
#         client.get_key(KeyArn=key_arn)
#     err = exc.value.response["Error"]
#     assert err["Code"] == "ResourceNotFoundException"


# @mock_aws
# def test_get_key_replica():
#     primary_client = boto3.client("payment-cryptography", region_name="us-east-1")
#     replica_client = boto3.client("payment-cryptography", region_name="us-west-2")
#     secondary_client = boto3.client("payment-cryptography", region_name="eu-west-1")

#     primary_arn = primary_client.create_key(
#         KeyAttributes=KEY_ATTRIBUTES_1,
#         Exportable=True,
#         Enabled = True,
#         Tags = [
#             {"Key": "Environment", "Value": "Test"},
#         ],
#         DeriveKeyUsage="TR31_P0_PIN_ENCRYPTION_KEY",
#         MultiRegionKeyType="PRIMARY",
#         ReplicationRegions=[
#             "us-west-2",
#             "eu-west-1",
#         ]
#     )["Key"]["KeyArn"]

#     primary_key = primary_client.get_key(KeyArn=primary_arn)["Key"]

#     # The replica shares the primary's key id, only the region differs.
#     key_id = primary_arn.split(":key/")[1]
#     replica_arn = f"arn:aws:payment-cryptography:us-west-2:1234567890:key/{key_id}"
#     replica_key = replica_client.get_key(KeyArn=replica_arn)["Key"]
#     secondary_arn = f"arn:aws:payment-cryptography:eu-west-1:1234567890:key/{key_id}"
#     secondary_key = secondary_client.get_key(KeyArn=secondary_arn)["Key"]


#     assert primary_key["MultiRegionKeyType"] == "PRIMARY"
#     assert primary_key["PrimaryRegion"] == "us-east-1"
#     assert primary_key["UsingDefaultReplicationRegions"] is True
#     assert primary_key["ReplicationStatus"] == {
#         "us-west-2": {"Status": "SYNCHRONIZED"},
#         "eu-west-1": {"Status": "SYNCHRONIZED"},
#     }
#     assert replica_key["MultiRegionKeyType"] == "REPLICA"
#     assert replica_key["PrimaryRegion"] == "us-east-1"
#     # Check that replica does not have the keys for UsingDefaultReplicationRegions and ReplicationStatus
#     assert "UsingDefaultReplicationRegions" not in replica_key
#     assert "ReplicationStatus" not in replica_key
#     assert secondary_key["MultiRegionKeyType"] == "REPLICA"
#     assert secondary_key["PrimaryRegion"] == "us-east-1"
#     # Check that secondary replica does not have the keys for UsingDefaultReplicationRegions and ReplicationStatus
#     assert "UsingDefaultReplicationRegions" not in secondary_key
#     assert "ReplicationStatus" not in secondary_key


# @mock_aws
# def test_list_keys():
#     primary_client = boto3.client("payment-cryptography", region_name="us-east-1")
#     secondary_client = boto3.client("payment-cryptography", region_name="us-west-2")

#     # Create multiple keys
#     for _ in range(5):
#         primary_client.create_key(
#             KeyAttributes=KEY_ATTRIBUTES_1,
#             Exportable=True,
#             Enabled = True,
#             Tags = [
#                 {"Key": "Environment", "Value": "Test"},
#             ],
#             DeriveKeyUsage="TR31_P0_PIN_ENCRYPTION_KEY",
#             MultiRegionKeyType="PRIMARY",
#         )

#     keys_list = primary_client.list_keys()["Keys"]
#     assert len(keys_list) == 5
#     assert keys_list[0]["KeyArn"].startswith("arn:aws:payment-cryptography:us-east-1:1234567890:key/")
#     assert keys_list[0]["KeyState"] == "CREATE_COMPLETE"

#     # Create keys with replicas
#     for _ in range(2):
#         primary_client.create_key(
#             KeyAttributes=KEY_ATTRIBUTES_1,
#             Exportable=True,
#             Enabled = True,
#             Tags = [
#                 {"Key": "Environment", "Value": "Test"},
#             ],
#             DeriveKeyUsage="TR31_P0_PIN_ENCRYPTION_KEY",
#             MultiRegionKeyType="PRIMARY",
#             ReplicationRegions=[
#                 "us-west-2",
#                 "eu-west-1",
#             ]
#         )

#     keys_list_primary = primary_client.list_keys()["Keys"]
#     keys_list_secondary = secondary_client.list_keys()["Keys"]
#     assert len(keys_list_primary) == 7  # 5 + 2
#     assert len(keys_list_secondary) == 2  # Only the replicas created in us-west-2
#     assert keys_list_primary[5]["MultiRegionKeyType"] == "PRIMARY"
#     assert keys_list_secondary[0]["MultiRegionKeyType"] == "REPLICA"


# @mock_aws
# def test_add_key_replication_regions():
#     primary_client = boto3.client("payment-cryptography", region_name="us-east-1")

#     key = primary_client.create_key(
#         KeyAttributes=KEY_ATTRIBUTES_1,
#         Exportable=True,
#         Enabled = True,
#         Tags = [
#             {"Key": "Environment", "Value": "Test"},
#         ],
#         DeriveKeyUsage="TR31_P0_PIN_ENCRYPTION_KEY",
#     )["Key"]

#     key_arn = key["KeyArn"]
#     key_id = key_arn.split(":key/")[1]

#     # Add replication regions to the key
#     primary_client.add_key_replication_regions(
#         KeyArn=key_arn,
#         ReplicationRegions=[
#             "us-west-2",
#             "eu-west-1",
#         ]
#     )

#     # Retrieve the key and check the replication status
#     primary_key = primary_client.get_key(KeyArn=key_arn)["Key"]
#     assert primary_key["MultiRegionKeyType"] == "PRIMARY"
#     assert primary_key["PrimaryRegion"] == "us-east-1"
#     assert primary_key["UsingDefaultReplicationRegions"] is False
#     assert primary_key["ReplicationStatus"] == {
#         "us-west-2": {"Status": "SYNCHRONIZED"},
#         "eu-west-1": {"Status": "SYNCHRONIZED"},
#     }

#     replica_client = boto3.client("payment-cryptography", region_name="us-west-2")
#     replica_key = replica_client.get_key(KeyArn=f"arn:aws:payment-cryptography:us-west-2:1234567890:key/{key_id}")["Key"]
#     assert replica_key["MultiRegionKeyType"] == "REPLICA"
#     assert replica_key["PrimaryRegion"] == "us-east-1"

#     replica_client_eu = boto3.client("payment-cryptography", region_name="eu-west-1")
#     replica_key_eu = replica_client_eu.get_key(KeyArn=f"arn:aws:payment-cryptography:eu-west-1:1234567890:key/{key_id}")["Key"]
#     assert replica_key_eu["MultiRegionKeyType"] == "REPLICA"
#     assert replica_key_eu["PrimaryRegion"] == "us-east-1"


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
# def test_tag_and_untag_key():
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

#     # Tag the key with additional tags
#     client.tag_resource(
#         ResourceArn=key_arn,
#         Tags=[
#             {"Key": "foo", "Value": "1"},
#             {"Key": "bar", "Value": "2"},
#         ]
#     )

#     # Retrieve the key and check the tags with list_tags_for_resource
#     retrieved_key = client.list_tags_for_resource(ResourceArn=key_arn)["Tags"]
#     assert len(retrieved_key) == 3  # Original tag + 2 new tags
#     assert {"Key": "Environment", "Value": "Test"} in retrieved_key
#     assert {"Key": "foo", "Value": "1"} in retrieved_key
#     assert {"Key": "bar", "Value": "2"} in retrieved_key

#     # Untag the key
#     client.untag_resource(
#         ResourceArn=key_arn,
#         TagKeys=["foo", "bar"]
#     )

#     # Retrieve the key and check the tags again
#     retrieved_key_after_untag = client.list_tags_for_resource(ResourceArn=key_arn)["Tags"]
#     assert len(retrieved_key_after_untag) == 1  # Only the original tag should remain
#     assert {"Key": "Environment", "Value": "Test"} in retrieved_key_after_untag


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


# @mock_aws
# def test_list_keys():
#     client = boto3.client("payment-cryptography", region_name="eu-west-1")
#     resp = client.list_keys()

#     raise Exception("NotYetImplemented")


# @mock_aws
# def test_list_tags_for_resource():
#     client = boto3.client("payment-cryptography", region_name="us-east-2")
#     resp = client.list_tags_for_resource()

#     raise Exception("NotYetImplemented")


# @mock_aws
# def test_tag_resource():
#     client = boto3.client("payment-cryptography", region_name="ap-southeast-1")
#     resp = client.tag_resource()

#     raise Exception("NotYetImplemented")
