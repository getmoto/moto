"""Unit tests for lexv2models-supported APIs."""

import boto3

from moto import mock_aws

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

    assert resp.get("botId")
    assert resp["botName"] == "test_bot"
    assert resp["description"] == "test_bot_description"
    assert resp["roleArn"] == "arn:aws:iam::123456789012:role/lex-role"
    assert resp["dataPrivacy"] == {"childDirected": False}
    assert resp["idleSessionTTLInSeconds"] == 300
    assert resp["botStatus"] == "CREATING"
    assert resp.get("creationDateTime")
    assert resp["botTags"] == {"test_key": "test_value"}
    assert resp["testBotAliasTags"] == {"test_key": "test_value"}
    assert resp["botType"] == "test_bot_type"
    assert resp["botMembers"] == [
        {
            "botMemberId": "test_bot_member_id",
            "botMemberName": "string",
            "botMemberAliasId": "test_bot_member_alias_id",
            "botMemberAliasName": "string",
            "botMemberVersion": "string",
        }
    ]
    assert resp.get("creationDateTime")


@mock_aws
def test_describe_bot():
    client = boto3.client("lexv2-models", region_name="eu-west-1")
    bot = client.create_bot(
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

    resp = client.describe_bot(botId=bot["botId"])

    assert resp["botId"] == bot["botId"]
    assert resp["botName"] == "test_bot"
    assert resp["description"] == "test_bot_description"
    assert resp["roleArn"] == "arn:aws:iam::123456789012:role/lex-role"
    assert resp["dataPrivacy"] == {"childDirected": False}
    assert resp["idleSessionTTLInSeconds"] == 300
    assert resp["botStatus"] == "CREATING"
    assert resp.get("creationDateTime")
    assert resp.get("lastUpdatedDateTime")
    assert resp["botType"] == "test_bot_type"
    assert resp["botMembers"] == [
        {
            "botMemberId": "test_bot_member_id",
            "botMemberName": "string",
            "botMemberAliasId": "test_bot_member_alias_id",
            "botMemberAliasName": "string",
            "botMemberVersion": "string",
        }
    ]
    assert resp["failureReasons"] == []


@mock_aws
def test_update_bot():
    client = boto3.client("lexv2-models", region_name="ap-southeast-1")
    bot = client.create_bot(
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

    resp = client.update_bot(
        botId=bot["botId"],
        botName="test_bot_updated",
        description="test_bot_description_updated",
        roleArn="arn:aws:iam::123456789012:role/lex-role-updated",
        dataPrivacy={"childDirected": True},
        idleSessionTTLInSeconds=600,
        botType="test_bot_type_updated",
        botMembers=[
            {
                "botMemberId": "test_bot_member_id_updated",
                "botMemberName": "string",
                "botMemberAliasId": "test_bot_member_alias_id_updated",
                "botMemberAliasName": "string",
                "botMemberVersion": "string",
            },
        ],
    )

    assert resp["botId"] == bot["botId"]
    assert resp["botName"] == "test_bot_updated"
    assert resp["description"] == "test_bot_description_updated"
    assert resp["roleArn"] == "arn:aws:iam::123456789012:role/lex-role-updated"
    assert resp["dataPrivacy"] == {"childDirected": True}
    assert resp["idleSessionTTLInSeconds"] == 600
    assert resp["botStatus"] == "CREATING"
    assert resp.get("creationDateTime")
    assert resp.get("lastUpdatedDateTime")
    assert resp.get("lastUpdatedDateTime") != resp.get("creationDateTime")
    assert resp["botType"] == "test_bot_type_updated"
    assert resp["botMembers"] == [
        {
            "botMemberId": "test_bot_member_id_updated",
            "botMemberName": "string",
            "botMemberAliasId": "test_bot_member_alias_id_updated",
            "botMemberAliasName": "string",
            "botMemberVersion": "string",
        }
    ]


@mock_aws
def test_list_bots():
    client = boto3.client("lexv2-models", region_name="ap-southeast-1")
    bot = client.create_bot(
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

    resp = client.list_bots()["botSummaries"]
    assert len(resp) == 1
    assert resp[0]["botId"] == bot["botId"]
    assert resp[0]["botName"] == "test_bot"
    assert resp[0]["description"] == "test_bot_description"
    assert resp[0]["botStatus"] == "CREATING"
    assert resp[0]["latestBotVersion"] == 1
    assert resp[0]["lastUpdatedDateTime"]
    assert resp[0]["botType"] == "test_bot_type"

    client.delete_bot(botId=bot["botId"], skipResourceInUseCheck=True)
    resp = client.list_bots()["botSummaries"]
    assert len(resp) == 0


@mock_aws
def test_bot_alias():
    client = boto3.client("lexv2-models", region_name="ap-southeast-1")
    resp = client.create_bot_alias(
        botAliasName="test_bot_alias",
        description="test_bot_alias_description",
        botVersion="1",
        botAliasLocaleSettings={"en-US": {"enabled": True}},
        conversationLogSettings={
            "textLogSettings": [
                {
                    "enabled": True,
                    "destination": {
                        "cloudWatch": {
                            "cloudWatchLogGroupArn": "test_log_group_arn",
                            "logPrefix": "test_log_prefix",
                        }
                    },
                }
            ]
        },
        sentimentAnalysisSettings={"detectSentiment": True},
        botId="test_bot_id",
        tags={"test_key": "test_value"},
    )

    assert resp.get("botAliasId")
    assert resp["botAliasName"] == "test_bot_alias"
    assert resp["description"] == "test_bot_alias_description"
    assert resp["botVersion"] == "1"
    assert resp["botAliasLocaleSettings"] == {"en-US": {"enabled": True}}
    assert resp["conversationLogSettings"] == {
        "textLogSettings": [
            {
                "enabled": True,
                "destination": {
                    "cloudWatch": {
                        "cloudWatchLogGroupArn": "test_log_group_arn",
                        "logPrefix": "test_log_prefix",
                    }
                },
            }
        ]
    }
    assert resp["sentimentAnalysisSettings"] == {"detectSentiment": True}
    assert resp["botAliasStatus"] == "CREATING"
    assert resp["botId"] == "test_bot_id"
    assert resp.get("creationDateTime")
    assert resp["tags"] == {"test_key": "test_value"}

    desc_resp = client.describe_bot_alias(
        botAliasId=resp["botAliasId"], botId="test_bot_id"
    )

    assert desc_resp["botAliasId"] == resp["botAliasId"]
    assert desc_resp["botAliasName"] == "test_bot_alias"
    assert desc_resp["description"] == "test_bot_alias_description"
    assert desc_resp["botVersion"] == "1"
    assert desc_resp["botAliasLocaleSettings"] == {"en-US": {"enabled": True}}
    assert desc_resp["conversationLogSettings"] == {
        "textLogSettings": [
            {
                "enabled": True,
                "destination": {
                    "cloudWatch": {
                        "cloudWatchLogGroupArn": "test_log_group_arn",
                        "logPrefix": "test_log_prefix",
                    }
                },
            }
        ]
    }
    assert desc_resp["sentimentAnalysisSettings"] == {"detectSentiment": True}
    assert desc_resp["botAliasHistoryEvents"] == []
    assert desc_resp["botAliasStatus"] == "CREATING"
    assert desc_resp["botId"] == "test_bot_id"
    assert desc_resp.get("creationDateTime")
    assert desc_resp.get("lastUpdatedDateTime")
    assert desc_resp["parentBotNetworks"] == []

    list_resp = client.list_bot_aliases(botId="test_bot_id")["botAliasSummaries"]

    assert len(list_resp) == 1
    assert list_resp[0]["botAliasId"] == resp["botAliasId"]
    assert list_resp[0]["botAliasName"] == "test_bot_alias"
    assert list_resp[0]["description"] == "test_bot_alias_description"
    assert list_resp[0]["botVersion"] == "1"
    assert list_resp[0]["botAliasStatus"] == "CREATING"
    assert list_resp[0]["creationDateTime"] == resp["creationDateTime"]

    update_resp = client.update_bot_alias(
        botAliasId=resp["botAliasId"],
        botId="test_bot_id",
        botAliasName="test_bot_alias_updated",
        description="test_bot_alias_description_updated",
        botVersion="1",
        botAliasLocaleSettings={"en-US": {"enabled": True}},
        conversationLogSettings={
            "textLogSettings": [
                {
                    "enabled": True,
                    "destination": {
                        "cloudWatch": {
                            "cloudWatchLogGroupArn": "test_log_group_arn_updated",
                            "logPrefix": "test_log_prefix_updated",
                        }
                    },
                }
            ]
        },
        sentimentAnalysisSettings={"detectSentiment": False},
    )
    assert update_resp["botAliasId"] == resp["botAliasId"]
    assert update_resp["botAliasName"] == "test_bot_alias_updated"
    assert update_resp["description"] == "test_bot_alias_description_updated"
    assert update_resp["botVersion"] == "1"
    assert update_resp["botAliasLocaleSettings"] == {"en-US": {"enabled": True}}
    assert update_resp["conversationLogSettings"] == {
        "textLogSettings": [
            {
                "enabled": True,
                "destination": {
                    "cloudWatch": {
                        "cloudWatchLogGroupArn": "test_log_group_arn_updated",
                        "logPrefix": "test_log_prefix_updated",
                    }
                },
            }
        ]
    }
    assert update_resp["sentimentAnalysisSettings"] == {"detectSentiment": False}
    assert update_resp["botAliasStatus"] == "CREATING"
    assert update_resp["botId"] == "test_bot_id"
    assert update_resp.get("lastUpdatedDateTime") != resp.get("creationDateTime")

    client.delete_bot_alias(botAliasId=resp["botAliasId"], botId="test_bot_id")
    list_resp = client.list_bot_aliases(botId="test_bot_id")["botAliasSummaries"]
    assert len(list_resp) == 0


@mock_aws
def test_resource_policy():
    client = boto3.client("lexv2-models", region_name="eu-west-1")

    arn = "arn:aws:lex:eu-west-1:123456789012:bot/MyLexBot"

    resp = client.create_resource_policy(
        resourceArn=arn,
        policy="test_resource_policy",
    )

    assert resp["resourceArn"] == arn
    assert resp.get("revisionId")

    desc_resp = client.describe_resource_policy(resourceArn=arn)
    assert desc_resp["resourceArn"] == arn
    assert desc_resp["policy"] == "test_resource_policy"
    assert desc_resp.get("revisionId")

    update_resp = client.update_resource_policy(
        resourceArn=arn,
        policy="test_resource_policy_updated",
        expectedRevisionId=resp["revisionId"],
    )

    assert update_resp["resourceArn"] == arn
    assert update_resp["revisionId"] != resp["revisionId"]

    delete_resp = client.delete_resource_policy(
        resourceArn=arn,
        expectedRevisionId=update_resp["revisionId"],
    )
    assert delete_resp["resourceArn"] == arn


@mock_aws
def test_tag_resource():
    sts = boto3.client("sts", "eu-west-1")
    account_id = sts.get_caller_identity()["Account"]
    region_name = "eu-west-1"

    client = boto3.client("lexv2-models", region_name="eu-west-1")
    cr_resp = client.create_bot(
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

    arn = f"arn:aws:lex:{region_name}:{account_id}:bot/{cr_resp['botId']}"

    resp = client.list_tags_for_resource(resourceARN=arn)
    assert resp["tags"] == {"test_key": "test_value"}

    client.tag_resource(resourceARN=arn, tags={"new_key": "new_value"})
    resp = client.list_tags_for_resource(resourceARN=arn)
    assert resp["tags"] == {"test_key": "test_value", "new_key": "new_value"}

    client.untag_resource(resourceARN=arn, tagKeys=["new_key"])
    resp = client.list_tags_for_resource(resourceARN=arn)
    assert resp["tags"] == {"test_key": "test_value"}
