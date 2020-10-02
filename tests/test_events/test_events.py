import json
import random
import unittest

import boto3
import sure  # noqa

from botocore.exceptions import ClientError
import pytest

from moto.core import ACCOUNT_ID
from moto.core.exceptions import JsonRESTError
from moto.events import mock_events
from moto.events.models import EventsBackend

RULES = [
    {"Name": "test1", "ScheduleExpression": "rate(5 minutes)"},
    {"Name": "test2", "ScheduleExpression": "rate(1 minute)"},
    {"Name": "test3", "EventPattern": '{"source": ["test-source"]}'},
]

TARGETS = {
    "test-target-1": {
        "Id": "test-target-1",
        "Arn": "arn:aws:lambda:us-west-2:111111111111:function:test-function-1",
        "Rules": ["test1", "test2"],
    },
    "test-target-2": {
        "Id": "test-target-2",
        "Arn": "arn:aws:lambda:us-west-2:111111111111:function:test-function-2",
        "Rules": ["test1", "test3"],
    },
    "test-target-3": {
        "Id": "test-target-3",
        "Arn": "arn:aws:lambda:us-west-2:111111111111:function:test-function-3",
        "Rules": ["test1", "test2"],
    },
    "test-target-4": {
        "Id": "test-target-4",
        "Arn": "arn:aws:lambda:us-west-2:111111111111:function:test-function-4",
        "Rules": ["test1", "test3"],
    },
    "test-target-5": {
        "Id": "test-target-5",
        "Arn": "arn:aws:lambda:us-west-2:111111111111:function:test-function-5",
        "Rules": ["test1", "test2"],
    },
    "test-target-6": {
        "Id": "test-target-6",
        "Arn": "arn:aws:lambda:us-west-2:111111111111:function:test-function-6",
        "Rules": ["test1", "test3"],
    },
}


def get_random_rule():
    return RULES[random.randint(0, len(RULES) - 1)]


def generate_environment():
    client = boto3.client("events", "us-west-2")

    for rule in RULES:
        client.put_rule(
            Name=rule["Name"],
            ScheduleExpression=rule.get("ScheduleExpression", ""),
            EventPattern=rule.get("EventPattern", ""),
        )

        targets = []
        for target in TARGETS:
            if rule["Name"] in TARGETS[target].get("Rules"):
                targets.append({"Id": target, "Arn": TARGETS[target]["Arn"]})

        client.put_targets(Rule=rule["Name"], Targets=targets)

    return client


@mock_events
def test_put_rule():
    client = boto3.client("events", "us-west-2")
    client.list_rules()["Rules"].should.have.length_of(0)

    rule_data = {
        "Name": "my-event",
        "ScheduleExpression": "rate(5 minutes)",
        "EventPattern": '{"source": ["test-source"]}',
    }

    client.put_rule(**rule_data)

    rules = client.list_rules()["Rules"]

    rules.should.have.length_of(1)
    rules[0]["Name"].should.equal(rule_data["Name"])
    rules[0]["ScheduleExpression"].should.equal(rule_data["ScheduleExpression"])
    rules[0]["EventPattern"].should.equal(rule_data["EventPattern"])
    rules[0]["State"].should.equal("ENABLED")


@mock_events
def test_list_rules():
    client = generate_environment()
    response = client.list_rules()

    assert response is not None
    assert len(response["Rules"]) > 0


@mock_events
def test_describe_rule():
    rule_name = get_random_rule()["Name"]
    client = generate_environment()
    response = client.describe_rule(Name=rule_name)

    assert response is not None
    assert response.get("Name") == rule_name
    assert response.get(
        "Arn"
    ) == "arn:aws:events:us-west-2:111111111111:rule/{0}".format(rule_name)


@mock_events
def test_enable_disable_rule():
    rule_name = get_random_rule()["Name"]
    client = generate_environment()

    # Rules should start out enabled in these tests.
    rule = client.describe_rule(Name=rule_name)
    assert rule["State"] == "ENABLED"

    client.disable_rule(Name=rule_name)
    rule = client.describe_rule(Name=rule_name)
    assert rule["State"] == "DISABLED"

    client.enable_rule(Name=rule_name)
    rule = client.describe_rule(Name=rule_name)
    assert rule["State"] == "ENABLED"

    # Test invalid name
    try:
        client.enable_rule(Name="junk")

    except ClientError as ce:
        assert ce.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_events
def test_list_rule_names_by_target():
    test_1_target = TARGETS["test-target-1"]
    test_2_target = TARGETS["test-target-2"]
    client = generate_environment()

    rules = client.list_rule_names_by_target(TargetArn=test_1_target["Arn"])
    assert len(rules["RuleNames"]) == len(test_1_target["Rules"])
    for rule in rules["RuleNames"]:
        assert rule in test_1_target["Rules"]

    rules = client.list_rule_names_by_target(TargetArn=test_2_target["Arn"])
    assert len(rules["RuleNames"]) == len(test_2_target["Rules"])
    for rule in rules["RuleNames"]:
        assert rule in test_2_target["Rules"]


@mock_events
def test_delete_rule():
    client = generate_environment()

    client.delete_rule(Name=RULES[0]["Name"])
    rules = client.list_rules()
    assert len(rules["Rules"]) == len(RULES) - 1


@mock_events
def test_list_targets_by_rule():
    rule_name = get_random_rule()["Name"]
    client = generate_environment()
    targets = client.list_targets_by_rule(Rule=rule_name)

    expected_targets = []
    for target in TARGETS:
        if rule_name in TARGETS[target].get("Rules"):
            expected_targets.append(target)

    assert len(targets["Targets"]) == len(expected_targets)


@mock_events
def test_remove_targets():
    rule_name = get_random_rule()["Name"]
    client = generate_environment()

    targets = client.list_targets_by_rule(Rule=rule_name)["Targets"]
    targets_before = len(targets)
    assert targets_before > 0

    response = client.remove_targets(Rule=rule_name, Ids=[targets[0]["Id"]])
    response["FailedEntryCount"].should.equal(0)
    response["FailedEntries"].should.have.length_of(0)

    targets = client.list_targets_by_rule(Rule=rule_name)["Targets"]
    targets_after = len(targets)
    assert targets_before - 1 == targets_after


@mock_events
def test_remove_targets_errors():
    client = boto3.client("events", "us-east-1")

    client.remove_targets.when.called_with(
        Rule="non-existent", Ids=["Id12345678"]
    ).should.throw(
        client.exceptions.ResourceNotFoundException,
        "An entity that you specified does not exist",
    )


@mock_events
def test_put_targets():
    client = boto3.client("events", "us-west-2")
    rule_name = "my-event"
    rule_data = {
        "Name": rule_name,
        "ScheduleExpression": "rate(5 minutes)",
        "EventPattern": '{"source": ["test-source"]}',
    }

    client.put_rule(**rule_data)

    targets = client.list_targets_by_rule(Rule=rule_name)["Targets"]
    targets_before = len(targets)
    assert targets_before == 0

    targets_data = [{"Arn": "test_arn", "Id": "test_id"}]
    resp = client.put_targets(Rule=rule_name, Targets=targets_data)
    assert resp["FailedEntryCount"] == 0
    assert len(resp["FailedEntries"]) == 0

    targets = client.list_targets_by_rule(Rule=rule_name)["Targets"]
    targets_after = len(targets)
    assert targets_before + 1 == targets_after

    assert targets[0]["Arn"] == "test_arn"
    assert targets[0]["Id"] == "test_id"


@mock_events
def test_permissions():
    client = boto3.client("events", "eu-central-1")

    client.put_permission(
        Action="events:PutEvents", Principal="111111111111", StatementId="Account1"
    )
    client.put_permission(
        Action="events:PutEvents", Principal="222222222222", StatementId="Account2"
    )

    resp = client.describe_event_bus()
    resp_policy = json.loads(resp["Policy"])
    assert len(resp_policy["Statement"]) == 2

    client.remove_permission(StatementId="Account2")

    resp = client.describe_event_bus()
    resp_policy = json.loads(resp["Policy"])
    assert len(resp_policy["Statement"]) == 1
    assert resp_policy["Statement"][0]["Sid"] == "Account1"


@mock_events
def test_put_permission_errors():
    client = boto3.client("events", "us-east-1")
    client.create_event_bus(Name="test-bus")

    client.put_permission.when.called_with(
        EventBusName="non-existing",
        Action="events:PutEvents",
        Principal="111111111111",
        StatementId="test",
    ).should.throw(ClientError, "Event bus non-existing does not exist.")

    client.put_permission.when.called_with(
        EventBusName="test-bus",
        Action="events:PutPermission",
        Principal="111111111111",
        StatementId="test",
    ).should.throw(
        ClientError, "Provided value in parameter 'action' is not supported."
    )


@mock_events
def test_remove_permission_errors():
    client = boto3.client("events", "us-east-1")
    client.create_event_bus(Name="test-bus")

    client.remove_permission.when.called_with(
        EventBusName="non-existing", StatementId="test"
    ).should.throw(ClientError, "Event bus non-existing does not exist.")

    client.remove_permission.when.called_with(
        EventBusName="test-bus", StatementId="test"
    ).should.throw(ClientError, "EventBus does not have a policy.")

    client.put_permission(
        EventBusName="test-bus",
        Action="events:PutEvents",
        Principal="111111111111",
        StatementId="test",
    )

    client.remove_permission.when.called_with(
        EventBusName="test-bus", StatementId="non-existing"
    ).should.throw(ClientError, "Statement with the provided id does not exist.")


@mock_events
def test_put_events():
    client = boto3.client("events", "eu-central-1")

    event = {
        "Source": "com.mycompany.myapp",
        "Detail": '{"key1": "value3", "key2": "value4"}',
        "Resources": ["resource1", "resource2"],
        "DetailType": "myDetailType",
    }

    response = client.put_events(Entries=[event])
    # Boto3 would error if it didn't return 200 OK
    response["FailedEntryCount"].should.equal(0)
    response["Entries"].should.have.length_of(1)

    with pytest.raises(ClientError):
        client.put_events(Entries=[event] * 20)


@mock_events
def test_create_event_bus():
    client = boto3.client("events", "us-east-1")
    response = client.create_event_bus(Name="test-bus")

    response["EventBusArn"].should.equal(
        "arn:aws:events:us-east-1:{}:event-bus/test-bus".format(ACCOUNT_ID)
    )


@mock_events
def test_create_event_bus_errors():
    client = boto3.client("events", "us-east-1")
    client.create_event_bus(Name="test-bus")

    client.create_event_bus.when.called_with(Name="test-bus").should.throw(
        ClientError, "Event bus test-bus already exists."
    )

    # the 'default' name is already used for the account's default event bus.
    client.create_event_bus.when.called_with(Name="default").should.throw(
        ClientError, "Event bus default already exists."
    )

    # non partner event buses can't contain the '/' character
    client.create_event_bus.when.called_with(Name="test/test-bus").should.throw(
        ClientError, "Event bus name must not contain '/'."
    )

    client.create_event_bus.when.called_with(
        Name="aws.partner/test/test-bus", EventSourceName="aws.partner/test/test-bus"
    ).should.throw(
        ClientError, "Event source aws.partner/test/test-bus does not exist."
    )


@mock_events
def test_describe_event_bus():
    client = boto3.client("events", "us-east-1")

    response = client.describe_event_bus()

    response["Name"].should.equal("default")
    response["Arn"].should.equal(
        "arn:aws:events:us-east-1:{}:event-bus/default".format(ACCOUNT_ID)
    )
    response.should_not.have.key("Policy")

    client.create_event_bus(Name="test-bus")
    client.put_permission(
        EventBusName="test-bus",
        Action="events:PutEvents",
        Principal="111111111111",
        StatementId="test",
    )

    response = client.describe_event_bus(Name="test-bus")

    response["Name"].should.equal("test-bus")
    response["Arn"].should.equal(
        "arn:aws:events:us-east-1:{}:event-bus/test-bus".format(ACCOUNT_ID)
    )
    json.loads(response["Policy"]).should.equal(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "test",
                    "Effect": "Allow",
                    "Principal": {"AWS": "arn:aws:iam::111111111111:root"},
                    "Action": "events:PutEvents",
                    "Resource": "arn:aws:events:us-east-1:{}:event-bus/test-bus".format(
                        ACCOUNT_ID
                    ),
                }
            ],
        }
    )


@mock_events
def test_describe_event_bus_errors():
    client = boto3.client("events", "us-east-1")

    client.describe_event_bus.when.called_with(Name="non-existing").should.throw(
        ClientError, "Event bus non-existing does not exist."
    )


@mock_events
def test_list_event_buses():
    client = boto3.client("events", "us-east-1")
    client.create_event_bus(Name="test-bus-1")
    client.create_event_bus(Name="test-bus-2")
    client.create_event_bus(Name="other-bus-1")
    client.create_event_bus(Name="other-bus-2")

    response = client.list_event_buses()

    response["EventBuses"].should.have.length_of(5)
    sorted(response["EventBuses"], key=lambda i: i["Name"]).should.equal(
        [
            {
                "Name": "default",
                "Arn": "arn:aws:events:us-east-1:{}:event-bus/default".format(
                    ACCOUNT_ID
                ),
            },
            {
                "Name": "other-bus-1",
                "Arn": "arn:aws:events:us-east-1:{}:event-bus/other-bus-1".format(
                    ACCOUNT_ID
                ),
            },
            {
                "Name": "other-bus-2",
                "Arn": "arn:aws:events:us-east-1:{}:event-bus/other-bus-2".format(
                    ACCOUNT_ID
                ),
            },
            {
                "Name": "test-bus-1",
                "Arn": "arn:aws:events:us-east-1:{}:event-bus/test-bus-1".format(
                    ACCOUNT_ID
                ),
            },
            {
                "Name": "test-bus-2",
                "Arn": "arn:aws:events:us-east-1:{}:event-bus/test-bus-2".format(
                    ACCOUNT_ID
                ),
            },
        ]
    )

    response = client.list_event_buses(NamePrefix="other-bus")

    response["EventBuses"].should.have.length_of(2)
    sorted(response["EventBuses"], key=lambda i: i["Name"]).should.equal(
        [
            {
                "Name": "other-bus-1",
                "Arn": "arn:aws:events:us-east-1:{}:event-bus/other-bus-1".format(
                    ACCOUNT_ID
                ),
            },
            {
                "Name": "other-bus-2",
                "Arn": "arn:aws:events:us-east-1:{}:event-bus/other-bus-2".format(
                    ACCOUNT_ID
                ),
            },
        ]
    )


@mock_events
def test_delete_event_bus():
    client = boto3.client("events", "us-east-1")
    client.create_event_bus(Name="test-bus")

    response = client.list_event_buses()
    response["EventBuses"].should.have.length_of(2)

    client.delete_event_bus(Name="test-bus")

    response = client.list_event_buses()
    response["EventBuses"].should.have.length_of(1)
    response["EventBuses"].should.equal(
        [
            {
                "Name": "default",
                "Arn": "arn:aws:events:us-east-1:{}:event-bus/default".format(
                    ACCOUNT_ID
                ),
            }
        ]
    )

    # deleting non existing event bus should be successful
    client.delete_event_bus(Name="non-existing")


@mock_events
def test_delete_event_bus_errors():
    client = boto3.client("events", "us-east-1")

    client.delete_event_bus.when.called_with(Name="default").should.throw(
        ClientError, "Cannot delete event bus default."
    )


@mock_events
def test_rule_tagging_happy():
    client = generate_environment()
    rule_name = get_random_rule()["Name"]
    rule_arn = client.describe_rule(Name=rule_name).get("Arn")

    tags = [{"Key": "key1", "Value": "value1"}, {"Key": "key2", "Value": "value2"}]
    client.tag_resource(ResourceARN=rule_arn, Tags=tags)

    actual = client.list_tags_for_resource(ResourceARN=rule_arn).get("Tags")
    tc = unittest.TestCase("__init__")
    expected = [{"Value": "value1", "Key": "key1"}, {"Value": "value2", "Key": "key2"}]
    tc.assertTrue(
        (expected[0] == actual[0] and expected[1] == actual[1])
        or (expected[1] == actual[0] and expected[0] == actual[1])
    )

    client.untag_resource(ResourceARN=rule_arn, TagKeys=["key1"])

    actual = client.list_tags_for_resource(ResourceARN=rule_arn).get("Tags")
    expected = [{"Key": "key2", "Value": "value2"}]
    assert expected == actual


@mock_events
def test_rule_tagging_sad():
    back_end = EventsBackend("us-west-2")

    try:
        back_end.tag_resource("unknown", [])
        raise "tag_resource should fail if ResourceARN is not known"
    except JsonRESTError:
        pass

    try:
        back_end.untag_resource("unknown", [])
        raise "untag_resource should fail if ResourceARN is not known"
    except JsonRESTError:
        pass

    try:
        back_end.list_tags_for_resource("unknown")
        raise "list_tags_for_resource should fail if ResourceARN is not known"
    except JsonRESTError:
        pass
