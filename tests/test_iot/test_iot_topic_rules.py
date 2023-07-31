import boto3
import pytest

from botocore.exceptions import ClientError
from moto import mock_iot

name = "my-rule"
payload = {
    "sql": "SELECT * FROM 'topic/*' WHERE something > 0",
    "actions": [
        {"dynamoDBv2": {"putItem": {"tableName": "my-table"}, "roleArn": "my-role"}}
    ],
    "errorAction": {
        "republish": {"qos": 0, "roleArn": "my-role", "topic": "other-topic"}
    },
    "description": "my-description",
    "ruleDisabled": False,
    "awsIotSqlVersion": "2016-03-23",
}


@mock_iot
def test_topic_rule_create():
    client = boto3.client("iot", region_name="ap-northeast-1")

    client.create_topic_rule(ruleName=name, topicRulePayload=payload)

    # duplicated rule name
    with pytest.raises(ClientError) as ex:
        client.create_topic_rule(ruleName=name, topicRulePayload=payload)
    error_code = ex.value.response["Error"]["Code"]
    assert error_code == "ResourceAlreadyExistsException"


@mock_iot
def test_topic_rule_list():
    client = boto3.client("iot", region_name="ap-northeast-1")

    # empty response
    res = client.list_topic_rules()
    assert len(res["rules"]) == 0

    client.create_topic_rule(ruleName=name, topicRulePayload=payload)
    client.create_topic_rule(ruleName="my-rule-2", topicRulePayload=payload)

    res = client.list_topic_rules()
    assert len(res["rules"]) == 2
    for rule, rule_name in zip(res["rules"], [name, "my-rule-2"]):
        assert rule["ruleName"] == rule_name
        assert rule["createdAt"] is not None
        assert rule["ruleArn"] is not None
        assert rule["ruleDisabled"] == payload["ruleDisabled"]
        assert rule["topicPattern"] == "topic/*"


@mock_iot
def test_topic_rule_get():
    client = boto3.client("iot", region_name="ap-northeast-1")

    # no such rule
    with pytest.raises(ClientError) as ex:
        client.get_topic_rule(ruleName=name)
    error_code = ex.value.response["Error"]["Code"]
    assert error_code == "ResourceNotFoundException"

    client.create_topic_rule(ruleName=name, topicRulePayload=payload)

    rule = client.get_topic_rule(ruleName=name)

    assert rule["ruleArn"] is not None
    rrule = rule["rule"]
    assert rrule["actions"] == payload["actions"]
    assert rrule["awsIotSqlVersion"] == payload["awsIotSqlVersion"]
    assert rrule["createdAt"] is not None
    assert rrule["description"] == payload["description"]
    assert rrule["errorAction"] == payload["errorAction"]
    assert rrule["ruleDisabled"] == payload["ruleDisabled"]
    assert rrule["ruleName"] == name
    assert rrule["sql"] == payload["sql"]


@mock_iot
def test_topic_rule_replace():
    client = boto3.client("iot", region_name="ap-northeast-1")

    # no such rule
    with pytest.raises(ClientError) as ex:
        client.replace_topic_rule(ruleName=name, topicRulePayload=payload)
    error_code = ex.value.response["Error"]["Code"]
    assert error_code == "ResourceNotFoundException"

    client.create_topic_rule(ruleName=name, topicRulePayload=payload)

    my_payload = payload.copy()
    my_payload["description"] = "new-description"
    client.replace_topic_rule(ruleName=name, topicRulePayload=my_payload)

    rule = client.get_topic_rule(ruleName=name)
    assert rule["rule"]["ruleName"] == name
    assert rule["rule"]["description"] == my_payload["description"]


@mock_iot
def test_topic_rule_disable():
    client = boto3.client("iot", region_name="ap-northeast-1")

    # no such rule
    with pytest.raises(ClientError) as ex:
        client.disable_topic_rule(ruleName=name)
    error_code = ex.value.response["Error"]["Code"]
    assert error_code == "ResourceNotFoundException"

    client.create_topic_rule(ruleName=name, topicRulePayload=payload)

    client.disable_topic_rule(ruleName=name)

    rule = client.get_topic_rule(ruleName=name)
    assert rule["rule"]["ruleName"] == name
    assert rule["rule"]["ruleDisabled"] is True


@mock_iot
def test_topic_rule_enable():
    client = boto3.client("iot", region_name="ap-northeast-1")

    # no such rule
    with pytest.raises(ClientError) as ex:
        client.enable_topic_rule(ruleName=name)
    error_code = ex.value.response["Error"]["Code"]
    assert error_code == "ResourceNotFoundException"

    my_payload = payload.copy()
    my_payload["ruleDisabled"] = True
    client.create_topic_rule(ruleName=name, topicRulePayload=my_payload)

    client.enable_topic_rule(ruleName=name)

    rule = client.get_topic_rule(ruleName=name)
    assert rule["rule"]["ruleName"] == name
    assert rule["rule"]["ruleDisabled"] is False


@mock_iot
def test_topic_rule_delete():
    client = boto3.client("iot", region_name="ap-northeast-1")

    # no such rule
    with pytest.raises(ClientError) as ex:
        client.delete_topic_rule(ruleName=name)
    error_code = ex.value.response["Error"]["Code"]
    assert error_code == "ResourceNotFoundException"

    client.create_topic_rule(ruleName=name, topicRulePayload=payload)

    client.enable_topic_rule(ruleName=name)

    client.delete_topic_rule(ruleName=name)

    res = client.list_topic_rules()
    assert len(res["rules"]) == 0
