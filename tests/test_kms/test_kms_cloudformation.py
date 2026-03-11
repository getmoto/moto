import json
from uuid import uuid4

import boto3

from moto import mock_aws

CF_KMS_ALIAS_TEMPLATE = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Description": "The AWS CloudFormation template for this Serverless application",
    "Resources": {
        "MyFirstAlias": {
            "Type": "AWS::KMS::Alias",
            "Properties": {"AliasName": "", "TargetKeyId": ""},
        }
    },
}


@mock_aws
def test_alias_create_and_delete():
    cf = boto3.client("cloudformation", region_name="us-east-1")
    kms_client = boto3.client("kms", region_name="us-east-1")

    alias_name = "alias/my_first_alias"
    stack_name = f"Stack{str(uuid4())[0:6]}"
    kms_key_id1 = kms_client.create_key(Policy="my policy")["KeyMetadata"]["KeyId"]
    kms_key_id2 = kms_client.create_key(Policy="my policy")["KeyMetadata"]["KeyId"]

    template = CF_KMS_ALIAS_TEMPLATE.copy()
    template["Resources"]["MyFirstAlias"]["Properties"]["TargetKeyId"] = kms_key_id1
    template["Resources"]["MyFirstAlias"]["Properties"]["AliasName"] = alias_name

    # CREATE
    cf.create_stack(StackName=stack_name, TemplateBody=json.dumps(template))
    resources = cf.describe_stack_resources(StackName=stack_name)["StackResources"]
    assert [r["PhysicalResourceId"] for r in resources][0] == alias_name

    # VERIFY
    aliases = kms_client.list_aliases(KeyId=kms_key_id1)["Aliases"]
    assert [al["AliasName"] for al in aliases] == [alias_name]

    assert not kms_client.list_aliases(KeyId=kms_key_id2)["Aliases"]

    # UPDATE
    template["Resources"]["MyFirstAlias"]["Properties"]["TargetKeyId"] = kms_key_id2
    cf.update_stack(StackName=stack_name, TemplateBody=json.dumps(template))

    # VERIFY
    assert not kms_client.list_aliases(KeyId=kms_key_id1)["Aliases"]

    aliases = kms_client.list_aliases(KeyId=kms_key_id2)["Aliases"]
    assert [al["AliasName"] for al in aliases] == [alias_name]

    # DELETE
    cf.delete_stack(StackName=stack_name)

    # VERIFY
    assert not kms_client.list_aliases(KeyId=kms_key_id1)["Aliases"]
    assert not kms_client.list_aliases(KeyId=kms_key_id2)["Aliases"]
