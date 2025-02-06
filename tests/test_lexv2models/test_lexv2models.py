"""Unit tests for lexv2models-supported APIs."""

import boto3

from moto import mock_aws

import json

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
def test_create_bot():
    client = boto3.client("lexv2-models", region_name="ap-southeast-1")
    resp = client.create_bot(
        botName="test_bot",
        description="test_bot_description",
        roleArn="arn:aws:iam::123456789012:role/lex-role",
        dataPrivacy={"childDirected": False},
        idleSessionTTLInSeconds=300,
        botTags={"test_key": "test_value"},
        testBotAliasTags={"test_key": "test_value"},
        botType="test_bot_type",
        botMembers=[
            {
                "botMemberId": "test_bot_member_id",
                "botMemberName": "string",
                "botMemberAliasId": "test_bot_member_alias_id",
                "botMemberAliasName": "string",
                "botMemberVersion": "string",
            },
        ],
    )

    # print(resp)
    # print(json.dumps(resp, indent=4, sort_keys=True))

    # assert resp["botName"] == "test_bot"
    # assert resp["description"] == "test_bot_description"
    # assert resp["roleArn"] == "arn:aws:iam::123456789012:role/lex-role"
    # assert resp["dataPrivacy"] == {"childDirected": False}
    # assert resp["botStatus"] == "CREATING"

    print(client.describe_bot(botId=resp["botId"]))

    alias_resp = client.create_bot_alias(
        botAliasName="TestBotAlias",
        description="Alias for testing bot",
        botVersion="1.0",
        botAliasLocaleSettings={
            "en_US": {
                "enabled": True,
                "codeHookSpecification": {
                    "lambdaCodeHook": {
                        "lambdaARN": "arn:aws:lambda:us-east-1:123456789012:function:TestFunction",
                        "codeHookInterfaceVersion": "1.0"
                    }
                }
            }
        },
        conversationLogSettings={
            "textLogSettings": [
                {
                    "enabled": True,
                    "destination": {
                        "cloudWatch": {
                            "cloudWatchLogGroupArn": "arn:aws:logs:us-east-1:123456789012:log-group:/aws/lambda/TestFunction",
                            "logPrefix": "TestLogs"
                        }
                    },
                    "selectiveLoggingEnabled": False
                }
            ],
            "audioLogSettings": [
                {
                    "enabled": True,
                    "destination": {
                        "s3Bucket": {
                            "kmsKeyArn": "arn:aws:kms:us-east-1:123456789012:key/abcd1234-efgh-5678-ijkl-9mnopqrstuv",
                            "s3BucketArn": "arn:aws:s3:::my-lex-audio-logs",
                            "logPrefix": "AudioLogs"
                        }
                    },
                    "selectiveLoggingEnabled": False
                }
            ]
        },
        sentimentAnalysisSettings={
            "detectSentiment": True
        },
        botId=resp["botId"],
        tags={
            "Environment": "Test",
            "Project": "LexV2"
        }
    )

    print(alias_resp)

    print(client.describe_bot_alias(
        botId=resp["botId"], botAliasId=alias_resp["botAliasId"]))

# @mock_aws
# def test_describe_bot():
#     client = boto3.client("lexv2-models", region_name="eu-west-1")
#     resp = client.describe_bot()

#     raise Exception("NotYetImplemented")


# @mock_aws
# def test_update_bot():
#     client = boto3.client("lexv2-models", region_name="ap-southeast-1")
#     resp = client.update_bot()

#     raise Exception("NotYetImplemented")


# @mock_aws
# def test_list_bots():
#     client = boto3.client("lexv2-models", region_name="ap-southeast-1")
#     resp = client.list_bots()

#     raise Exception("NotYetImplemented")


# @mock_aws
# def test_delete_bot():
#     client = boto3.client("lexv2-models", region_name="us-east-2")
#     resp = client.delete_bot()

#     raise Exception("NotYetImplemented")


# @mock_aws
# def test_create_bot_alias():
#     client = boto3.client("lexv2-models", region_name="us-east-2")
#     resp = client.create_bot_alias()

#     raise Exception("NotYetImplemented")


# @mock_aws
# def test_describe_bot_alias():
#     client = boto3.client("lexv2-models", region_name="eu-west-1")
#     resp = client.describe_bot_alias()

#     raise Exception("NotYetImplemented")


# @mock_aws
# def test_update_bot_alias():
#     client = boto3.client("lexv2-models", region_name="eu-west-1")
#     resp = client.update_bot_alias()

#     raise Exception("NotYetImplemented")


# @mock_aws
# def test_list_bot_aliases():
#     client = boto3.client("lexv2-models", region_name="ap-southeast-1")
#     resp = client.list_bot_aliases()

#     raise Exception("NotYetImplemented")


# @mock_aws
# def test_delete_bot_alias():
#     client = boto3.client("lexv2-models", region_name="ap-southeast-1")
#     resp = client.delete_bot_alias()

#     raise Exception("NotYetImplemented")


# @mock_aws
# def test_create_resource_policy():
#     client = boto3.client("lexv2-models", region_name="eu-west-1")
#     resp = client.create_resource_policy()

#     raise Exception("NotYetImplemented")


# @mock_aws
# def test_describe_resource_policy():
#     client = boto3.client("lexv2-models", region_name="eu-west-1")
#     resp = client.describe_resource_policy()

#     raise Exception("NotYetImplemented")


# @mock_aws
# def test_delete_resource_policy():
#     client = boto3.client("lexv2-models", region_name="us-east-2")
#     resp = client.delete_resource_policy()

#     raise Exception("NotYetImplemented")


# @mock_aws
# def test_tag_resource():
#     client = boto3.client("lexv2-models", region_name="eu-west-1")
#     resp = client.tag_resource()

#     raise Exception("NotYetImplemented")


# @mock_aws
# def test_untag_resource():
#     client = boto3.client("lexv2-models", region_name="eu-west-1")
#     resp = client.untag_resource()

#     raise Exception("NotYetImplemented")


# @mock_aws
# def test_list_tags_for_resource():
#     client = boto3.client("lexv2-models", region_name="us-east-2")
#     resp = client.list_tags_for_resource()

#     raise Exception("NotYetImplemented")


# @mock_aws
# def test_update_resource_policy():
#     client = boto3.client("lexv2-models", region_name="ap-southeast-1")
#     resp = client.update_resource_policy()

#     raise Exception("NotYetImplemented")
