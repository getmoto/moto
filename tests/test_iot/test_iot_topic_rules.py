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
    error_code.should.equal("ResourceAlreadyExistsException")


@mock_iot
def test_topic_rule_list():
    client = boto3.client("iot", region_name="ap-northeast-1")

    # empty response
    res = client.list_topic_rules()
    res.should.have.key("rules").which.should.have.length_of(0)

    client.create_topic_rule(ruleName=name, topicRulePayload=payload)
    client.create_topic_rule(ruleName="my-rule-2", topicRulePayload=payload)

    res = client.list_topic_rules()
    res.should.have.key("rules").which.should.have.length_of(2)
    for rule, rule_name in zip(res["rules"], [name, "my-rule-2"]):
        rule.should.have.key("ruleName").which.should.equal(rule_name)
        rule.should.have.key("createdAt").which.should_not.be.none
        rule.should.have.key("ruleArn").which.should_not.be.none
        rule.should.have.key("ruleDisabled").which.should.equal(payload["ruleDisabled"])
        rule.should.have.key("topicPattern").which.should.equal("topic/*")


@mock_iot
def test_topic_rule_get():
    client = boto3.client("iot", region_name="ap-northeast-1")

    # no such rule
    with pytest.raises(ClientError) as ex:
        client.get_topic_rule(ruleName=name)
    error_code = ex.value.response["Error"]["Code"]
    error_code.should.equal("ResourceNotFoundException")

    client.create_topic_rule(ruleName=name, topicRulePayload=payload)

    rule = client.get_topic_rule(ruleName=name)

    rule.should.have.key("ruleArn").which.should_not.be.none
    rule.should.have.key("rule")
    rrule = rule["rule"]
    rrule.should.have.key("actions").which.should.equal(payload["actions"])
    rrule.should.have.key("awsIotSqlVersion").which.should.equal(
        payload["awsIotSqlVersion"]
    )
    rrule.should.have.key("createdAt").which.should_not.be.none
    rrule.should.have.key("description").which.should.equal(payload["description"])
    rrule.should.have.key("errorAction").which.should.equal(payload["errorAction"])
    rrule.should.have.key("ruleDisabled").which.should.equal(payload["ruleDisabled"])
    rrule.should.have.key("ruleName").which.should.equal(name)
    rrule.should.have.key("sql").which.should.equal(payload["sql"])


@mock_iot
def test_topic_rule_replace():
    client = boto3.client("iot", region_name="ap-northeast-1")

    # no such rule
    with pytest.raises(ClientError) as ex:
        client.replace_topic_rule(ruleName=name, topicRulePayload=payload)
    error_code = ex.value.response["Error"]["Code"]
    error_code.should.equal("ResourceNotFoundException")

    client.create_topic_rule(ruleName=name, topicRulePayload=payload)

    my_payload = payload.copy()
    my_payload["description"] = "new-description"
    client.replace_topic_rule(
        ruleName=name, topicRulePayload=my_payload,
    )

    rule = client.get_topic_rule(ruleName=name)
    rule["rule"]["ruleName"].should.equal(name)
    rule["rule"]["description"].should.equal(my_payload["description"])


@mock_iot
def test_topic_rule_disable():
    client = boto3.client("iot", region_name="ap-northeast-1")

    # no such rule
    with pytest.raises(ClientError) as ex:
        client.disable_topic_rule(ruleName=name)
    error_code = ex.value.response["Error"]["Code"]
    error_code.should.equal("ResourceNotFoundException")

    client.create_topic_rule(ruleName=name, topicRulePayload=payload)

    client.disable_topic_rule(ruleName=name)

    rule = client.get_topic_rule(ruleName=name)
    rule["rule"]["ruleName"].should.equal(name)
    rule["rule"]["ruleDisabled"].should.equal(True)


@mock_iot
def test_topic_rule_enable():
    client = boto3.client("iot", region_name="ap-northeast-1")

    # no such rule
    with pytest.raises(ClientError) as ex:
        client.enable_topic_rule(ruleName=name)
    error_code = ex.value.response["Error"]["Code"]
    error_code.should.equal("ResourceNotFoundException")

    my_payload = payload.copy()
    my_payload["ruleDisabled"] = True
    client.create_topic_rule(ruleName=name, topicRulePayload=my_payload)

    client.enable_topic_rule(ruleName=name)

    rule = client.get_topic_rule(ruleName=name)
    rule["rule"]["ruleName"].should.equal(name)
    rule["rule"]["ruleDisabled"].should.equal(False)


@mock_iot
def test_topic_rule_delete():
    client = boto3.client("iot", region_name="ap-northeast-1")

    # no such rule
    with pytest.raises(ClientError) as ex:
        client.delete_topic_rule(ruleName=name)
    error_code = ex.value.response["Error"]["Code"]
    error_code.should.equal("ResourceNotFoundException")

    client.create_topic_rule(ruleName=name, topicRulePayload=payload)

    client.enable_topic_rule(ruleName=name)

    client.delete_topic_rule(ruleName=name)

    res = client.list_topic_rules()
    res.should.have.key("rules").which.should.have.length_of(0)
