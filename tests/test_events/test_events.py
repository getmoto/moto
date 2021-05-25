import json
import random
import unittest
from datetime import datetime

import boto3
import pytz
import sure  # noqa

from botocore.exceptions import ClientError
import pytest

from moto import mock_logs
from moto.core import ACCOUNT_ID
from moto.core.utils import iso_8601_datetime_without_milliseconds
from moto.events import mock_events

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
def test_put_rule_error_schedule_expression_custom_event_bus():
    # given
    client = boto3.client("events", "eu-central-1")
    event_bus_name = "test-bus"
    client.create_event_bus(Name=event_bus_name)

    # when
    with pytest.raises(ClientError) as e:
        client.put_rule(
            Name="test-rule",
            ScheduleExpression="rate(5 minutes)",
            EventBusName=event_bus_name,
        )

    # then
    ex = e.value
    ex.operation_name.should.equal("PutRule")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("ValidationException")
    ex.response["Error"]["Message"].should.equal(
        "ScheduleExpression is supported only on the default event bus."
    )


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

    response["Name"].should.equal(rule_name)
    response["Arn"].should.equal(
        "arn:aws:events:us-west-2:{0}:rule/{1}".format(ACCOUNT_ID, rule_name)
    )


@mock_events
def test_describe_rule_with_event_bus_name():
    # given
    client = boto3.client("events", "eu-central-1")
    event_bus_name = "test-bus"
    rule_name = "test-rule"
    client.create_event_bus(Name=event_bus_name)
    client.put_rule(
        Name=rule_name,
        EventPattern=json.dumps({"account": [ACCOUNT_ID]}),
        State="DISABLED",
        Description="test rule",
        RoleArn="arn:aws:iam::{}:role/test-role".format(ACCOUNT_ID),
        EventBusName=event_bus_name,
    )

    # when
    response = client.describe_rule(Name=rule_name, EventBusName=event_bus_name)

    # then
    response["Arn"].should.equal(
        "arn:aws:events:eu-central-1:{0}:rule/{1}/{2}".format(
            ACCOUNT_ID, event_bus_name, rule_name
        )
    )
    response["CreatedBy"].should.equal(ACCOUNT_ID)
    response["Description"].should.equal("test rule")
    response["EventBusName"].should.equal(event_bus_name)
    json.loads(response["EventPattern"]).should.equal({"account": [ACCOUNT_ID]})
    response["Name"].should.equal(rule_name)
    response["RoleArn"].should.equal(
        "arn:aws:iam::{}:role/test-role".format(ACCOUNT_ID)
    )
    response["State"].should.equal("DISABLED")

    response.should_not.have.key("ManagedBy")
    response.should_not.have.key("ScheduleExpression")


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
def test_update_rule_with_targets():
    client = boto3.client("events", "us-west-2")
    client.put_rule(
        Name="test1", ScheduleExpression="rate(5 minutes)", EventPattern="",
    )

    client.put_targets(
        Rule="test1",
        Targets=[
            {
                "Id": "test-target-1",
                "Arn": "arn:aws:lambda:us-west-2:111111111111:function:test-function-1",
            }
        ],
    )

    targets = client.list_targets_by_rule(Rule="test1")["Targets"]
    targets_before = len(targets)
    assert targets_before == 1

    client.put_rule(
        Name="test1", ScheduleExpression="rate(1 minute)", EventPattern="",
    )

    targets = client.list_targets_by_rule(Rule="test1")["Targets"]

    assert len(targets) == 1
    assert targets[0].get("Id") == "test-target-1"


@mock_events
def test_remove_targets_error_unknown_rule():
    # given
    client = boto3.client("events", "eu-central-1")

    # when
    with pytest.raises(ClientError) as e:
        client.remove_targets(Rule="unknown", Ids=["something"])

    # then
    ex = e.value
    ex.operation_name.should.equal("RemoveTargets")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("ResourceNotFoundException")
    ex.response["Error"]["Message"].should.equal(
        "Rule unknown does not exist on EventBus default."
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

    targets_data = [{"Arn": "arn:aws:s3:::test-arn", "Id": "test_id"}]
    resp = client.put_targets(Rule=rule_name, Targets=targets_data)
    assert resp["FailedEntryCount"] == 0
    assert len(resp["FailedEntries"]) == 0

    targets = client.list_targets_by_rule(Rule=rule_name)["Targets"]
    targets_after = len(targets)
    assert targets_before + 1 == targets_after

    assert targets[0]["Arn"] == "arn:aws:s3:::test-arn"
    assert targets[0]["Id"] == "test_id"


@mock_events
def test_put_targets_error_invalid_arn():
    # given
    client = boto3.client("events", "eu-central-1")
    rule_name = "test-rule"
    client.put_rule(
        Name=rule_name,
        EventPattern=json.dumps({"account": [ACCOUNT_ID]}),
        State="ENABLED",
    )

    # when
    with pytest.raises(ClientError) as e:
        client.put_targets(
            Rule=rule_name,
            Targets=[
                {"Id": "s3", "Arn": "arn:aws:s3:::test-bucket"},
                {"Id": "s3", "Arn": "test-bucket"},
            ],
        )

    # then
    ex = e.value
    ex.operation_name.should.equal("PutTargets")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("ValidationException")
    ex.response["Error"]["Message"].should.equal(
        "Parameter test-bucket is not valid. "
        "Reason: Provided Arn is not in correct format."
    )


@mock_events
def test_put_targets_error_unknown_rule():
    # given
    client = boto3.client("events", "eu-central-1")

    # when
    with pytest.raises(ClientError) as e:
        client.put_targets(
            Rule="unknown", Targets=[{"Id": "s3", "Arn": "arn:aws:s3:::test-bucket"}]
        )

    # then
    ex = e.value
    ex.operation_name.should.equal("PutTargets")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("ResourceNotFoundException")
    ex.response["Error"]["Message"].should.equal(
        "Rule unknown does not exist on EventBus default."
    )


@mock_events
def test_put_targets_error_missing_parameter_sqs_fifo():
    # given
    client = boto3.client("events", "eu-central-1")

    # when
    with pytest.raises(ClientError) as e:
        client.put_targets(
            Rule="unknown",
            Targets=[
                {
                    "Id": "sqs-fifo",
                    "Arn": "arn:aws:sqs:eu-central-1:{}:test-queue.fifo".format(
                        ACCOUNT_ID
                    ),
                }
            ],
        )

    # then
    ex = e.value
    ex.operation_name.should.equal("PutTargets")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("ValidationException")
    ex.response["Error"]["Message"].should.equal(
        "Parameter(s) SqsParameters must be specified for target: sqs-fifo."
    )


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


@mock_events
def test_put_events_error_too_many_entries():
    # given
    client = boto3.client("events", "eu-central-1")

    # when
    with pytest.raises(ClientError) as e:
        client.put_events(
            Entries=[
                {
                    "Source": "source",
                    "DetailType": "type",
                    "Detail": '{ "key1": "value1" }',
                },
            ]
            * 11
        )

    # then
    ex = e.value
    ex.operation_name.should.equal("PutEvents")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("ValidationException")
    ex.response["Error"]["Message"].should.equal(
        "1 validation error detected: "
        "Value '[PutEventsRequestEntry]' at 'entries' failed to satisfy constraint: "
        "Member must have length less than or equal to 10"
    )


@mock_events
def test_put_events_error_missing_argument_source():
    # given
    client = boto3.client("events", "eu-central-1")

    # when
    response = client.put_events(Entries=[{}])

    # then
    response["FailedEntryCount"].should.equal(1)
    response["Entries"].should.have.length_of(1)
    response["Entries"][0].should.equal(
        {
            "ErrorCode": "InvalidArgument",
            "ErrorMessage": "Parameter Source is not valid. Reason: Source is a required argument.",
        }
    )


@mock_events
def test_put_events_error_missing_argument_detail_type():
    # given
    client = boto3.client("events", "eu-central-1")

    # when
    response = client.put_events(Entries=[{"Source": "source"}])

    # then
    response["FailedEntryCount"].should.equal(1)
    response["Entries"].should.have.length_of(1)
    response["Entries"][0].should.equal(
        {
            "ErrorCode": "InvalidArgument",
            "ErrorMessage": "Parameter DetailType is not valid. Reason: DetailType is a required argument.",
        }
    )


@mock_events
def test_put_events_error_missing_argument_detail():
    # given
    client = boto3.client("events", "eu-central-1")

    # when
    response = client.put_events(Entries=[{"DetailType": "type", "Source": "source"}])

    # then
    response["FailedEntryCount"].should.equal(1)
    response["Entries"].should.have.length_of(1)
    response["Entries"][0].should.equal(
        {
            "ErrorCode": "InvalidArgument",
            "ErrorMessage": "Parameter Detail is not valid. Reason: Detail is a required argument.",
        }
    )


@mock_events
def test_put_events_error_invalid_json_detail():
    # given
    client = boto3.client("events", "eu-central-1")

    # when
    response = client.put_events(
        Entries=[{"Detail": "detail", "DetailType": "type", "Source": "source"}]
    )

    # then
    response["FailedEntryCount"].should.equal(1)
    response["Entries"].should.have.length_of(1)
    response["Entries"][0].should.equal(
        {"ErrorCode": "MalformedDetail", "ErrorMessage": "Detail is malformed."}
    )


@mock_events
def test_put_events_with_mixed_entries():
    # given
    client = boto3.client("events", "eu-central-1")

    # when
    response = client.put_events(
        Entries=[
            {"Source": "source"},
            {"Detail": '{"key": "value"}', "DetailType": "type", "Source": "source"},
            {"Detail": "detail", "DetailType": "type", "Source": "source"},
            {"Detail": '{"key2": "value2"}', "DetailType": "type", "Source": "source"},
        ]
    )

    # then
    response["FailedEntryCount"].should.equal(2)
    response["Entries"].should.have.length_of(4)
    [
        entry for entry in response["Entries"] if "EventId" in entry
    ].should.have.length_of(2)
    [
        entry for entry in response["Entries"] if "ErrorCode" in entry
    ].should.have.length_of(2)


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
def test_tag_resource_error_unknown_arn():
    # given
    client = boto3.client("events", "eu-central-1")

    # when
    with pytest.raises(ClientError) as e:
        client.tag_resource(
            ResourceARN="arn:aws:events:eu-central-1:{0}:rule/unknown".format(
                ACCOUNT_ID
            ),
            Tags=[],
        )

    # then
    ex = e.value
    ex.operation_name.should.equal("TagResource")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("ResourceNotFoundException")
    ex.response["Error"]["Message"].should.equal(
        "Rule unknown does not exist on EventBus default."
    )


@mock_events
def test_untag_resource_error_unknown_arn():
    # given
    client = boto3.client("events", "eu-central-1")

    # when
    with pytest.raises(ClientError) as e:
        client.untag_resource(
            ResourceARN="arn:aws:events:eu-central-1:{0}:rule/unknown".format(
                ACCOUNT_ID
            ),
            TagKeys=[],
        )

    # then
    ex = e.value
    ex.operation_name.should.equal("UntagResource")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("ResourceNotFoundException")
    ex.response["Error"]["Message"].should.equal(
        "Rule unknown does not exist on EventBus default."
    )


@mock_events
def test_list_tags_for_resource_error_unknown_arn():
    # given
    client = boto3.client("events", "eu-central-1")

    # when
    with pytest.raises(ClientError) as e:
        client.list_tags_for_resource(
            ResourceARN="arn:aws:events:eu-central-1:{0}:rule/unknown".format(
                ACCOUNT_ID
            )
        )

    # then
    ex = e.value
    ex.operation_name.should.equal("ListTagsForResource")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("ResourceNotFoundException")
    ex.response["Error"]["Message"].should.equal(
        "Rule unknown does not exist on EventBus default."
    )


@mock_events
def test_create_archive():
    # given
    client = boto3.client("events", "eu-central-1")
    archive_name = "test-archive"

    # when
    response = client.create_archive(
        ArchiveName=archive_name,
        EventSourceArn="arn:aws:events:eu-central-1:{}:event-bus/default".format(
            ACCOUNT_ID
        ),
    )

    # then
    response["ArchiveArn"].should.equal(
        "arn:aws:events:eu-central-1:{0}:archive/{1}".format(ACCOUNT_ID, archive_name)
    )
    response["CreationTime"].should.be.a(datetime)
    response["State"].should.equal("ENABLED")

    # check for archive rule existence
    rule_name = "Events-Archive-{}".format(archive_name)
    response = client.describe_rule(Name=rule_name)

    response["Arn"].should.equal(
        "arn:aws:events:eu-central-1:{0}:rule/{1}".format(ACCOUNT_ID, rule_name)
    )
    response["CreatedBy"].should.equal(ACCOUNT_ID)
    response["EventBusName"].should.equal("default")
    json.loads(response["EventPattern"]).should.equal(
        {"replay-name": [{"exists": False}]}
    )
    response["ManagedBy"].should.equal("prod.vhs.events.aws.internal")
    response["Name"].should.equal(rule_name)
    response["State"].should.equal("ENABLED")

    response.should_not.have.key("Description")
    response.should_not.have.key("RoleArn")
    response.should_not.have.key("ScheduleExpression")


@mock_events
def test_create_archive_custom_event_bus():
    # given
    client = boto3.client("events", "eu-central-1")
    event_bus_arn = client.create_event_bus(Name="test-bus")["EventBusArn"]

    # when
    response = client.create_archive(
        ArchiveName="test-archive",
        EventSourceArn=event_bus_arn,
        EventPattern=json.dumps(
            {
                "key_1": {
                    "key_2": {"key_3": ["value_1", "value_2"], "key_4": ["value_3"]}
                }
            }
        ),
    )

    # then
    response["ArchiveArn"].should.equal(
        "arn:aws:events:eu-central-1:{}:archive/test-archive".format(ACCOUNT_ID)
    )
    response["CreationTime"].should.be.a(datetime)
    response["State"].should.equal("ENABLED")


@mock_events
def test_create_archive_error_long_name():
    # given
    client = boto3.client("events", "eu-central-1")
    name = "a" * 49

    # when
    with pytest.raises(ClientError) as e:
        client.create_archive(
            ArchiveName=name,
            EventSourceArn=(
                "arn:aws:events:eu-central-1:{}:event-bus/default".format(ACCOUNT_ID)
            ),
        )

    # then
    ex = e.value
    ex.operation_name.should.equal("CreateArchive")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("ValidationException")
    ex.response["Error"]["Message"].should.equal(
        " 1 validation error detected: "
        "Value '{}' at 'archiveName' failed to satisfy constraint: "
        "Member must have length less than or equal to 48".format(name)
    )


@mock_events
def test_create_archive_error_invalid_event_pattern():
    # given
    client = boto3.client("events", "eu-central-1")

    # when
    with pytest.raises(ClientError) as e:
        client.create_archive(
            ArchiveName="test-archive",
            EventSourceArn=(
                "arn:aws:events:eu-central-1:{}:event-bus/default".format(ACCOUNT_ID)
            ),
            EventPattern="invalid",
        )

    # then
    ex = e.value
    ex.operation_name.should.equal("CreateArchive")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("InvalidEventPatternException")
    ex.response["Error"]["Message"].should.equal("Event pattern is not valid.")


@mock_events
def test_create_archive_error_invalid_event_pattern_not_an_array():
    # given
    client = boto3.client("events", "eu-central-1")

    # when
    with pytest.raises(ClientError) as e:
        client.create_archive(
            ArchiveName="test-archive",
            EventSourceArn=(
                "arn:aws:events:eu-central-1:{}:event-bus/default".format(ACCOUNT_ID)
            ),
            EventPattern=json.dumps(
                {
                    "key_1": {
                        "key_2": {"key_3": ["value_1"]},
                        "key_4": {"key_5": ["value_2"], "key_6": "value_3"},
                    }
                }
            ),
        )

    # then
    ex = e.value
    ex.operation_name.should.equal("CreateArchive")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("InvalidEventPatternException")
    ex.response["Error"]["Message"].should.equal("Event pattern is not valid.")


@mock_events
def test_create_archive_error_unknown_event_bus():
    # given
    client = boto3.client("events", "eu-central-1")
    event_bus_name = "unknown"

    # when
    with pytest.raises(ClientError) as e:
        client.create_archive(
            ArchiveName="test-archive",
            EventSourceArn=(
                "arn:aws:events:eu-central-1:{}:event-bus/{}".format(
                    ACCOUNT_ID, event_bus_name
                )
            ),
        )

    # then
    ex = e.value
    ex.operation_name.should.equal("CreateArchive")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("ResourceNotFoundException")
    ex.response["Error"]["Message"].should.equal(
        "Event bus {} does not exist.".format(event_bus_name)
    )


@mock_events
def test_create_archive_error_duplicate():
    # given
    client = boto3.client("events", "eu-central-1")
    name = "test-archive"
    source_arn = "arn:aws:events:eu-central-1:{}:event-bus/default".format(ACCOUNT_ID)
    client.create_archive(ArchiveName=name, EventSourceArn=source_arn)

    # when
    with pytest.raises(ClientError) as e:
        client.create_archive(ArchiveName=name, EventSourceArn=source_arn)

    # then
    ex = e.value
    ex.operation_name.should.equal("CreateArchive")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("ResourceAlreadyExistsException")
    ex.response["Error"]["Message"].should.equal("Archive test-archive already exists.")


@mock_events
def test_describe_archive():
    # given
    client = boto3.client("events", "eu-central-1")
    name = "test-archive"
    source_arn = "arn:aws:events:eu-central-1:{}:event-bus/default".format(ACCOUNT_ID)
    event_pattern = json.dumps({"key": ["value"]})
    client.create_archive(
        ArchiveName=name,
        EventSourceArn=source_arn,
        Description="test archive",
        EventPattern=event_pattern,
    )

    # when
    response = client.describe_archive(ArchiveName=name)

    # then
    response["ArchiveArn"].should.equal(
        "arn:aws:events:eu-central-1:{0}:archive/{1}".format(ACCOUNT_ID, name)
    )
    response["ArchiveName"].should.equal(name)
    response["CreationTime"].should.be.a(datetime)
    response["Description"].should.equal("test archive")
    response["EventCount"].should.equal(0)
    response["EventPattern"].should.equal(event_pattern)
    response["EventSourceArn"].should.equal(source_arn)
    response["RetentionDays"].should.equal(0)
    response["SizeBytes"].should.equal(0)
    response["State"].should.equal("ENABLED")


@mock_events
def test_describe_archive_error_unknown_archive():
    # given
    client = boto3.client("events", "eu-central-1")
    name = "unknown"

    # when
    with pytest.raises(ClientError) as e:
        client.describe_archive(ArchiveName=name)

    # then
    ex = e.value
    ex.operation_name.should.equal("DescribeArchive")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("ResourceNotFoundException")
    ex.response["Error"]["Message"].should.equal(
        "Archive {} does not exist.".format(name)
    )


@mock_events
def test_list_archives():
    # given
    client = boto3.client("events", "eu-central-1")
    name = "test-archive"
    source_arn = "arn:aws:events:eu-central-1:{}:event-bus/default".format(ACCOUNT_ID)
    event_pattern = json.dumps({"key": ["value"]})
    client.create_archive(
        ArchiveName=name,
        EventSourceArn=source_arn,
        Description="test archive",
        EventPattern=event_pattern,
    )

    # when
    archives = client.list_archives()["Archives"]

    # then
    archives.should.have.length_of(1)
    archive = archives[0]
    archive["ArchiveName"].should.equal(name)
    archive["CreationTime"].should.be.a(datetime)
    archive["EventCount"].should.equal(0)
    archive["EventSourceArn"].should.equal(source_arn)
    archive["RetentionDays"].should.equal(0)
    archive["SizeBytes"].should.equal(0)
    archive["State"].should.equal("ENABLED")

    archive.should_not.have.key("ArchiveArn")
    archive.should_not.have.key("Description")
    archive.should_not.have.key("EventPattern")


@mock_events
def test_list_archives_with_name_prefix():
    # given
    client = boto3.client("events", "eu-central-1")
    source_arn = "arn:aws:events:eu-central-1:{}:event-bus/default".format(ACCOUNT_ID)
    client.create_archive(
        ArchiveName="test", EventSourceArn=source_arn,
    )
    client.create_archive(
        ArchiveName="test-archive", EventSourceArn=source_arn,
    )

    # when
    archives = client.list_archives(NamePrefix="test-")["Archives"]

    # then
    archives.should.have.length_of(1)
    archives[0]["ArchiveName"].should.equal("test-archive")


@mock_events
def test_list_archives_with_source_arn():
    # given
    client = boto3.client("events", "eu-central-1")
    source_arn = "arn:aws:events:eu-central-1:{}:event-bus/default".format(ACCOUNT_ID)
    source_arn_2 = client.create_event_bus(Name="test-bus")["EventBusArn"]
    client.create_archive(
        ArchiveName="test", EventSourceArn=source_arn,
    )
    client.create_archive(
        ArchiveName="test-archive", EventSourceArn=source_arn_2,
    )

    # when
    archives = client.list_archives(EventSourceArn=source_arn)["Archives"]

    # then
    archives.should.have.length_of(1)
    archives[0]["ArchiveName"].should.equal("test")


@mock_events
def test_list_archives_with_state():
    # given
    client = boto3.client("events", "eu-central-1")
    source_arn = "arn:aws:events:eu-central-1:{}:event-bus/default".format(ACCOUNT_ID)
    client.create_archive(
        ArchiveName="test", EventSourceArn=source_arn,
    )
    client.create_archive(
        ArchiveName="test-archive", EventSourceArn=source_arn,
    )

    # when
    archives = client.list_archives(State="DISABLED")["Archives"]

    # then
    archives.should.have.length_of(0)


@mock_events
def test_list_archives_error_multiple_filters():
    # given
    client = boto3.client("events", "eu-central-1")

    # when
    with pytest.raises(ClientError) as e:
        client.list_archives(NamePrefix="test", State="ENABLED")

    # then
    ex = e.value
    ex.operation_name.should.equal("ListArchives")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("ValidationException")
    ex.response["Error"]["Message"].should.equal(
        "At most one filter is allowed for ListArchives. "
        "Use either : State, EventSourceArn, or NamePrefix."
    )


@mock_events
def test_list_archives_error_invalid_state():
    # given
    client = boto3.client("events", "eu-central-1")

    # when
    with pytest.raises(ClientError) as e:
        client.list_archives(State="invalid")

    # then
    ex = e.value
    ex.operation_name.should.equal("ListArchives")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("ValidationException")
    ex.response["Error"]["Message"].should.equal(
        "1 validation error detected: "
        "Value 'invalid' at 'state' failed to satisfy constraint: "
        "Member must satisfy enum value set: "
        "[ENABLED, DISABLED, CREATING, UPDATING, CREATE_FAILED, UPDATE_FAILED]"
    )


@mock_events
def test_update_archive():
    # given
    client = boto3.client("events", "eu-central-1")
    name = "test-archive"
    source_arn = "arn:aws:events:eu-central-1:{}:event-bus/default".format(ACCOUNT_ID)
    event_pattern = json.dumps({"key": ["value"]})
    archive_arn = client.create_archive(ArchiveName=name, EventSourceArn=source_arn)[
        "ArchiveArn"
    ]

    # when
    response = client.update_archive(
        ArchiveName=name,
        Description="test archive",
        EventPattern=event_pattern,
        RetentionDays=14,
    )

    # then
    response["ArchiveArn"].should.equal(archive_arn)
    response["State"].should.equal("ENABLED")
    creation_time = response["CreationTime"]
    creation_time.should.be.a(datetime)

    response = client.describe_archive(ArchiveName=name)
    response["ArchiveArn"].should.equal(archive_arn)
    response["ArchiveName"].should.equal(name)
    response["CreationTime"].should.equal(creation_time)
    response["Description"].should.equal("test archive")
    response["EventCount"].should.equal(0)
    response["EventPattern"].should.equal(event_pattern)
    response["EventSourceArn"].should.equal(source_arn)
    response["RetentionDays"].should.equal(14)
    response["SizeBytes"].should.equal(0)
    response["State"].should.equal("ENABLED")


@mock_events
def test_update_archive_error_invalid_event_pattern():
    # given
    client = boto3.client("events", "eu-central-1")
    name = "test-archive"
    client.create_archive(
        ArchiveName=name,
        EventSourceArn="arn:aws:events:eu-central-1:{}:event-bus/default".format(
            ACCOUNT_ID
        ),
    )

    # when
    with pytest.raises(ClientError) as e:
        client.update_archive(
            ArchiveName=name, EventPattern="invalid",
        )

    # then
    ex = e.value
    ex.operation_name.should.equal("UpdateArchive")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("InvalidEventPatternException")
    ex.response["Error"]["Message"].should.equal("Event pattern is not valid.")


@mock_events
def test_update_archive_error_unknown_archive():
    # given
    client = boto3.client("events", "eu-central-1")
    name = "unknown"

    # when
    with pytest.raises(ClientError) as e:
        client.update_archive(ArchiveName=name)

    # then
    ex = e.value
    ex.operation_name.should.equal("UpdateArchive")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("ResourceNotFoundException")
    ex.response["Error"]["Message"].should.equal(
        "Archive {} does not exist.".format(name)
    )


@mock_events
def test_delete_archive():
    # given
    client = boto3.client("events", "eu-central-1")
    name = "test-archive"
    client.create_archive(
        ArchiveName=name,
        EventSourceArn="arn:aws:events:eu-central-1:{}:event-bus/default".format(
            ACCOUNT_ID
        ),
    )

    # when
    client.delete_archive(ArchiveName=name)

    # then
    response = client.list_archives(NamePrefix="test")["Archives"]
    response.should.have.length_of(0)


@mock_events
def test_delete_archive_error_unknown_archive():
    # given
    client = boto3.client("events", "eu-central-1")
    name = "unknown"

    # when
    with pytest.raises(ClientError) as e:
        client.delete_archive(ArchiveName=name)

    # then
    ex = e.value
    ex.operation_name.should.equal("DeleteArchive")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("ResourceNotFoundException")
    ex.response["Error"]["Message"].should.equal(
        "Archive {} does not exist.".format(name)
    )


@mock_events
def test_archive_actual_events():
    # given
    client = boto3.client("events", "eu-central-1")
    name = "test-archive"
    name_2 = "test-archive-no-match"
    name_3 = "test-archive-matches"
    event_bus_arn = "arn:aws:events:eu-central-1:{}:event-bus/default".format(
        ACCOUNT_ID
    )
    event = {
        "Source": "source",
        "DetailType": "type",
        "Detail": '{ "key1": "value1" }',
    }
    client.create_archive(ArchiveName=name, EventSourceArn=event_bus_arn)
    client.create_archive(
        ArchiveName=name_2,
        EventSourceArn=event_bus_arn,
        EventPattern=json.dumps({"detail-type": ["type"], "source": ["test"]}),
    )
    client.create_archive(
        ArchiveName=name_3,
        EventSourceArn=event_bus_arn,
        EventPattern=json.dumps({"detail-type": ["type"], "source": ["source"]}),
    )

    # when
    response = client.put_events(Entries=[event])

    # then
    response["FailedEntryCount"].should.equal(0)
    response["Entries"].should.have.length_of(1)

    response = client.describe_archive(ArchiveName=name)
    response["EventCount"].should.equal(1)
    response["SizeBytes"].should.be.greater_than(0)

    response = client.describe_archive(ArchiveName=name_2)
    response["EventCount"].should.equal(0)
    response["SizeBytes"].should.equal(0)

    response = client.describe_archive(ArchiveName=name_3)
    response["EventCount"].should.equal(1)
    response["SizeBytes"].should.be.greater_than(0)


@mock_events
def test_archive_event_with_bus_arn():
    # given
    client = boto3.client("events", "eu-central-1")
    event_bus_arn = "arn:aws:events:eu-central-1:{}:event-bus/default".format(
        ACCOUNT_ID
    )
    archive_name = "mock_archive"
    event_with_bus_arn = {
        "Source": "source",
        "DetailType": "type",
        "Detail": '{ "key1": "value1" }',
        "EventBusName": event_bus_arn,
    }
    client.create_archive(ArchiveName=archive_name, EventSourceArn=event_bus_arn)

    # when
    response = client.put_events(Entries=[event_with_bus_arn])

    # then
    response["FailedEntryCount"].should.equal(0)
    response["Entries"].should.have.length_of(1)

    response = client.describe_archive(ArchiveName=archive_name)
    response["EventCount"].should.equal(1)
    response["SizeBytes"].should.be.greater_than(0)


@mock_events
def test_start_replay():
    # given
    client = boto3.client("events", "eu-central-1")
    name = "test-replay"
    event_bus_arn = "arn:aws:events:eu-central-1:{}:event-bus/default".format(
        ACCOUNT_ID
    )
    archive_arn = client.create_archive(
        ArchiveName="test-archive", EventSourceArn=event_bus_arn,
    )["ArchiveArn"]

    # when
    response = client.start_replay(
        ReplayName=name,
        EventSourceArn=archive_arn,
        EventStartTime=datetime(2021, 2, 1),
        EventEndTime=datetime(2021, 2, 2),
        Destination={"Arn": event_bus_arn},
    )

    # then
    response["ReplayArn"].should.equal(
        "arn:aws:events:eu-central-1:{0}:replay/{1}".format(ACCOUNT_ID, name)
    )
    response["ReplayStartTime"].should.be.a(datetime)
    response["State"].should.equal("STARTING")


@mock_events
def test_start_replay_error_unknown_event_bus():
    # given
    client = boto3.client("events", "eu-central-1")
    event_bus_name = "unknown"

    # when
    with pytest.raises(ClientError) as e:
        client.start_replay(
            ReplayName="test",
            EventSourceArn="arn:aws:events:eu-central-1:{}:archive/test".format(
                ACCOUNT_ID
            ),
            EventStartTime=datetime(2021, 2, 1),
            EventEndTime=datetime(2021, 2, 2),
            Destination={
                "Arn": "arn:aws:events:eu-central-1:{0}:event-bus/{1}".format(
                    ACCOUNT_ID, event_bus_name
                ),
            },
        )

    # then
    ex = e.value
    ex.operation_name.should.equal("StartReplay")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("ResourceNotFoundException")
    ex.response["Error"]["Message"].should.equal(
        "Event bus {} does not exist.".format(event_bus_name)
    )


@mock_events
def test_start_replay_error_invalid_event_bus_arn():
    # given
    client = boto3.client("events", "eu-central-1")

    # when
    with pytest.raises(ClientError) as e:
        client.start_replay(
            ReplayName="test",
            EventSourceArn="arn:aws:events:eu-central-1:{}:archive/test".format(
                ACCOUNT_ID
            ),
            EventStartTime=datetime(2021, 2, 1),
            EventEndTime=datetime(2021, 2, 2),
            Destination={"Arn": "invalid",},
        )

    # then
    ex = e.value
    ex.operation_name.should.equal("StartReplay")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("ValidationException")
    ex.response["Error"]["Message"].should.equal(
        "Parameter Destination.Arn is not valid. Reason: Must contain an event bus ARN."
    )


@mock_events
def test_start_replay_error_unknown_archive():
    # given
    client = boto3.client("events", "eu-central-1")
    archive_name = "unknown"

    # when
    with pytest.raises(ClientError) as e:
        client.start_replay(
            ReplayName="test",
            EventSourceArn="arn:aws:events:eu-central-1:{0}:archive/{1}".format(
                ACCOUNT_ID, archive_name
            ),
            EventStartTime=datetime(2021, 2, 1),
            EventEndTime=datetime(2021, 2, 2),
            Destination={
                "Arn": "arn:aws:events:eu-central-1:{}:event-bus/default".format(
                    ACCOUNT_ID
                ),
            },
        )

    # then
    ex = e.value
    ex.operation_name.should.equal("StartReplay")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("ValidationException")
    ex.response["Error"]["Message"].should.equal(
        "Parameter EventSourceArn is not valid. "
        "Reason: Archive {} does not exist.".format(archive_name)
    )


@mock_events
def test_start_replay_error_cross_event_bus():
    # given
    client = boto3.client("events", "eu-central-1")
    archive_arn = client.create_archive(
        ArchiveName="test-archive",
        EventSourceArn="arn:aws:events:eu-central-1:{}:event-bus/default".format(
            ACCOUNT_ID
        ),
    )["ArchiveArn"]
    event_bus_arn = client.create_event_bus(Name="test-bus")["EventBusArn"]

    # when
    with pytest.raises(ClientError) as e:
        client.start_replay(
            ReplayName="test",
            EventSourceArn=archive_arn,
            EventStartTime=datetime(2021, 2, 1),
            EventEndTime=datetime(2021, 2, 2),
            Destination={"Arn": event_bus_arn},
        )

    # then
    ex = e.value
    ex.operation_name.should.equal("StartReplay")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("ValidationException")
    ex.response["Error"]["Message"].should.equal(
        "Parameter Destination.Arn is not valid. "
        "Reason: Cross event bus replay is not permitted."
    )


@mock_events
def test_start_replay_error_invalid_end_time():
    # given
    client = boto3.client("events", "eu-central-1")
    event_bus_arn = "arn:aws:events:eu-central-1:{}:event-bus/default".format(
        ACCOUNT_ID
    )
    archive_arn = client.create_archive(
        ArchiveName="test-archive", EventSourceArn=event_bus_arn,
    )["ArchiveArn"]

    # when
    with pytest.raises(ClientError) as e:
        client.start_replay(
            ReplayName="test",
            EventSourceArn=archive_arn,
            EventStartTime=datetime(2021, 2, 2),
            EventEndTime=datetime(2021, 2, 1),
            Destination={"Arn": event_bus_arn},
        )

    # then
    ex = e.value
    ex.operation_name.should.equal("StartReplay")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("ValidationException")
    ex.response["Error"]["Message"].should.equal(
        "Parameter EventEndTime is not valid. "
        "Reason: EventStartTime must be before EventEndTime."
    )


@mock_events
def test_start_replay_error_duplicate():
    # given
    client = boto3.client("events", "eu-central-1")
    name = "test-replay"
    event_bus_arn = "arn:aws:events:eu-central-1:{}:event-bus/default".format(
        ACCOUNT_ID
    )
    archive_arn = client.create_archive(
        ArchiveName="test-archive", EventSourceArn=event_bus_arn,
    )["ArchiveArn"]
    client.start_replay(
        ReplayName=name,
        EventSourceArn=archive_arn,
        EventStartTime=datetime(2021, 2, 1),
        EventEndTime=datetime(2021, 2, 2),
        Destination={"Arn": event_bus_arn},
    )

    # when
    with pytest.raises(ClientError) as e:
        client.start_replay(
            ReplayName=name,
            EventSourceArn=archive_arn,
            EventStartTime=datetime(2021, 2, 1),
            EventEndTime=datetime(2021, 2, 2),
            Destination={"Arn": event_bus_arn},
        )

    # then
    ex = e.value
    ex.operation_name.should.equal("StartReplay")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("ResourceAlreadyExistsException")
    ex.response["Error"]["Message"].should.equal(
        "Replay {} already exists.".format(name)
    )


@mock_events
def test_describe_replay():
    # given
    client = boto3.client("events", "eu-central-1")
    name = "test-replay"
    event_bus_arn = "arn:aws:events:eu-central-1:{}:event-bus/default".format(
        ACCOUNT_ID
    )
    archive_arn = client.create_archive(
        ArchiveName="test-archive", EventSourceArn=event_bus_arn,
    )["ArchiveArn"]
    client.start_replay(
        ReplayName=name,
        Description="test replay",
        EventSourceArn=archive_arn,
        EventStartTime=datetime(2021, 2, 1, tzinfo=pytz.utc),
        EventEndTime=datetime(2021, 2, 2, tzinfo=pytz.utc),
        Destination={"Arn": event_bus_arn},
    )

    # when
    response = client.describe_replay(ReplayName=name)

    # then
    response["Description"].should.equal("test replay")
    response["Destination"].should.equal({"Arn": event_bus_arn})
    response["EventSourceArn"].should.equal(archive_arn)
    response["EventStartTime"].should.equal(datetime(2021, 2, 1, tzinfo=pytz.utc))
    response["EventEndTime"].should.equal(datetime(2021, 2, 2, tzinfo=pytz.utc))
    response["ReplayArn"].should.equal(
        "arn:aws:events:eu-central-1:{0}:replay/{1}".format(ACCOUNT_ID, name)
    )
    response["ReplayName"].should.equal(name)
    response["ReplayStartTime"].should.be.a(datetime)
    response["ReplayEndTime"].should.be.a(datetime)
    response["State"].should.equal("COMPLETED")


@mock_events
def test_describe_replay_error_unknown_replay():
    # given
    client = boto3.client("events", "eu-central-1")
    name = "unknown"

    # when
    with pytest.raises(ClientError) as e:
        client.describe_replay(ReplayName=name)

    # then
    ex = e.value
    ex.operation_name.should.equal("DescribeReplay")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("ResourceNotFoundException")
    ex.response["Error"]["Message"].should.equal(
        "Replay {} does not exist.".format(name)
    )


@mock_events
def test_list_replays():
    # given
    client = boto3.client("events", "eu-central-1")
    name = "test-replay"
    event_bus_arn = "arn:aws:events:eu-central-1:{}:event-bus/default".format(
        ACCOUNT_ID
    )
    archive_arn = client.create_archive(
        ArchiveName="test-replay", EventSourceArn=event_bus_arn,
    )["ArchiveArn"]
    client.start_replay(
        ReplayName=name,
        Description="test replay",
        EventSourceArn=archive_arn,
        EventStartTime=datetime(2021, 2, 1, tzinfo=pytz.utc),
        EventEndTime=datetime(2021, 2, 2, tzinfo=pytz.utc),
        Destination={"Arn": event_bus_arn},
    )

    # when
    replays = client.list_replays()["Replays"]

    # then
    replays.should.have.length_of(1)
    replay = replays[0]
    replay["EventSourceArn"].should.equal(archive_arn)
    replay["EventStartTime"].should.equal(datetime(2021, 2, 1, tzinfo=pytz.utc))
    replay["EventEndTime"].should.equal(datetime(2021, 2, 2, tzinfo=pytz.utc))
    replay["ReplayName"].should.equal(name)
    replay["ReplayStartTime"].should.be.a(datetime)
    replay["ReplayEndTime"].should.be.a(datetime)
    replay["State"].should.equal("COMPLETED")


@mock_events
def test_list_replays_with_name_prefix():
    # given
    client = boto3.client("events", "eu-central-1")
    event_bus_arn = "arn:aws:events:eu-central-1:{}:event-bus/default".format(
        ACCOUNT_ID
    )
    archive_arn = client.create_archive(
        ArchiveName="test-replay", EventSourceArn=event_bus_arn,
    )["ArchiveArn"]
    client.start_replay(
        ReplayName="test",
        EventSourceArn=archive_arn,
        EventStartTime=datetime(2021, 1, 1, tzinfo=pytz.utc),
        EventEndTime=datetime(2021, 1, 2, tzinfo=pytz.utc),
        Destination={"Arn": event_bus_arn},
    )
    client.start_replay(
        ReplayName="test-replay",
        EventSourceArn=archive_arn,
        EventStartTime=datetime(2021, 2, 1, tzinfo=pytz.utc),
        EventEndTime=datetime(2021, 2, 2, tzinfo=pytz.utc),
        Destination={"Arn": event_bus_arn},
    )

    # when
    replays = client.list_replays(NamePrefix="test-")["Replays"]

    # then
    replays.should.have.length_of(1)
    replays[0]["ReplayName"].should.equal("test-replay")


@mock_events
def test_list_replays_with_source_arn():
    # given
    client = boto3.client("events", "eu-central-1")
    event_bus_arn = "arn:aws:events:eu-central-1:{}:event-bus/default".format(
        ACCOUNT_ID
    )
    archive_arn = client.create_archive(
        ArchiveName="test-replay", EventSourceArn=event_bus_arn,
    )["ArchiveArn"]
    client.start_replay(
        ReplayName="test",
        EventSourceArn=archive_arn,
        EventStartTime=datetime(2021, 1, 1, tzinfo=pytz.utc),
        EventEndTime=datetime(2021, 1, 2, tzinfo=pytz.utc),
        Destination={"Arn": event_bus_arn},
    )
    client.start_replay(
        ReplayName="test-replay",
        EventSourceArn=archive_arn,
        EventStartTime=datetime(2021, 2, 1, tzinfo=pytz.utc),
        EventEndTime=datetime(2021, 2, 2, tzinfo=pytz.utc),
        Destination={"Arn": event_bus_arn},
    )

    # when
    replays = client.list_replays(EventSourceArn=archive_arn)["Replays"]

    # then
    replays.should.have.length_of(2)


@mock_events
def test_list_replays_with_state():
    # given
    client = boto3.client("events", "eu-central-1")
    event_bus_arn = "arn:aws:events:eu-central-1:{}:event-bus/default".format(
        ACCOUNT_ID
    )
    archive_arn = client.create_archive(
        ArchiveName="test-replay", EventSourceArn=event_bus_arn,
    )["ArchiveArn"]
    client.start_replay(
        ReplayName="test",
        EventSourceArn=archive_arn,
        EventStartTime=datetime(2021, 1, 1, tzinfo=pytz.utc),
        EventEndTime=datetime(2021, 1, 2, tzinfo=pytz.utc),
        Destination={"Arn": event_bus_arn},
    )
    client.start_replay(
        ReplayName="test-replay",
        EventSourceArn=archive_arn,
        EventStartTime=datetime(2021, 2, 1, tzinfo=pytz.utc),
        EventEndTime=datetime(2021, 2, 2, tzinfo=pytz.utc),
        Destination={"Arn": event_bus_arn},
    )

    # when
    replays = client.list_replays(State="FAILED")["Replays"]

    # then
    replays.should.have.length_of(0)


@mock_events
def test_list_replays_error_multiple_filters():
    # given
    client = boto3.client("events", "eu-central-1")

    # when
    with pytest.raises(ClientError) as e:
        client.list_replays(NamePrefix="test", State="COMPLETED")

    # then
    ex = e.value
    ex.operation_name.should.equal("ListReplays")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("ValidationException")
    ex.response["Error"]["Message"].should.equal(
        "At most one filter is allowed for ListReplays. "
        "Use either : State, EventSourceArn, or NamePrefix."
    )


@mock_events
def test_list_replays_error_invalid_state():
    # given
    client = boto3.client("events", "eu-central-1")

    # when
    with pytest.raises(ClientError) as e:
        client.list_replays(State="invalid")

    # then
    ex = e.value
    ex.operation_name.should.equal("ListReplays")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("ValidationException")
    ex.response["Error"]["Message"].should.equal(
        "1 validation error detected: "
        "Value 'invalid' at 'state' failed to satisfy constraint: "
        "Member must satisfy enum value set: "
        "[CANCELLED, CANCELLING, COMPLETED, FAILED, RUNNING, STARTING]"
    )


@mock_events
def test_cancel_replay():
    # given
    client = boto3.client("events", "eu-central-1")
    name = "test-replay"
    event_bus_arn = "arn:aws:events:eu-central-1:{}:event-bus/default".format(
        ACCOUNT_ID
    )
    archive_arn = client.create_archive(
        ArchiveName="test-archive", EventSourceArn=event_bus_arn,
    )["ArchiveArn"]
    client.start_replay(
        ReplayName=name,
        Description="test replay",
        EventSourceArn=archive_arn,
        EventStartTime=datetime(2021, 2, 1, tzinfo=pytz.utc),
        EventEndTime=datetime(2021, 2, 2, tzinfo=pytz.utc),
        Destination={"Arn": event_bus_arn},
    )

    # when
    response = client.cancel_replay(ReplayName=name)

    # then
    response["ReplayArn"].should.equal(
        "arn:aws:events:eu-central-1:{0}:replay/{1}".format(ACCOUNT_ID, name)
    )
    response["State"].should.equal("CANCELLING")

    response = client.describe_replay(ReplayName=name)
    response["State"].should.equal("CANCELLED")


@mock_events
def test_cancel_replay_error_unknown_replay():
    # given
    client = boto3.client("events", "eu-central-1")
    name = "unknown"

    # when
    with pytest.raises(ClientError) as e:
        client.cancel_replay(ReplayName=name)

    # then
    ex = e.value
    ex.operation_name.should.equal("CancelReplay")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("ResourceNotFoundException")
    ex.response["Error"]["Message"].should.equal(
        "Replay {} does not exist.".format(name)
    )


@mock_events
def test_cancel_replay_error_illegal_state():
    # given
    client = boto3.client("events", "eu-central-1")
    name = "test-replay"
    event_bus_arn = "arn:aws:events:eu-central-1:{}:event-bus/default".format(
        ACCOUNT_ID
    )
    archive_arn = client.create_archive(
        ArchiveName="test-archive", EventSourceArn=event_bus_arn,
    )["ArchiveArn"]
    client.start_replay(
        ReplayName=name,
        Description="test replay",
        EventSourceArn=archive_arn,
        EventStartTime=datetime(2021, 2, 1, tzinfo=pytz.utc),
        EventEndTime=datetime(2021, 2, 2, tzinfo=pytz.utc),
        Destination={"Arn": event_bus_arn},
    )
    client.cancel_replay(ReplayName=name)

    # when
    with pytest.raises(ClientError) as e:
        client.cancel_replay(ReplayName=name)

    # then
    ex = e.value
    ex.operation_name.should.equal("CancelReplay")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("IllegalStatusException")
    ex.response["Error"]["Message"].should.equal(
        "Replay {} is not in a valid state for this operation.".format(name)
    )


@mock_events
@mock_logs
def test_start_replay_send_to_log_group():
    # given
    client = boto3.client("events", "eu-central-1")
    logs_client = boto3.client("logs", "eu-central-1")
    log_group_name = "/test-group"
    rule_name = "test-rule"
    logs_client.create_log_group(logGroupName=log_group_name)
    event_bus_arn = "arn:aws:events:eu-central-1:{}:event-bus/default".format(
        ACCOUNT_ID
    )
    client.put_rule(Name=rule_name, EventPattern=json.dumps({"account": [ACCOUNT_ID]}))
    client.put_targets(
        Rule=rule_name,
        Targets=[
            {
                "Id": "test",
                "Arn": "arn:aws:logs:eu-central-1:{0}:log-group:{1}".format(
                    ACCOUNT_ID, log_group_name
                ),
            }
        ],
    )
    archive_arn = client.create_archive(
        ArchiveName="test-archive", EventSourceArn=event_bus_arn,
    )["ArchiveArn"]
    event_time = datetime(2021, 1, 1, 12, 23, 34)
    client.put_events(
        Entries=[
            {
                "Time": event_time,
                "Source": "source",
                "DetailType": "type",
                "Detail": json.dumps({"key": "value"}),
            }
        ]
    )

    # when
    client.start_replay(
        ReplayName="test-replay",
        EventSourceArn=archive_arn,
        EventStartTime=datetime(2021, 1, 1),
        EventEndTime=datetime(2021, 1, 2),
        Destination={"Arn": event_bus_arn},
    )

    # then
    events = sorted(
        logs_client.filter_log_events(logGroupName=log_group_name)["events"],
        key=lambda item: item["eventId"],
    )
    event_original = json.loads(events[0]["message"])
    event_original["version"].should.equal("0")
    event_original["id"].should_not.be.empty
    event_original["detail-type"].should.equal("type")
    event_original["source"].should.equal("source")
    event_original["time"].should.equal(
        iso_8601_datetime_without_milliseconds(event_time)
    )
    event_original["region"].should.equal("eu-central-1")
    event_original["resources"].should.be.empty
    event_original["detail"].should.equal({"key": "value"})
    event_original.should_not.have.key("replay-name")

    event_replay = json.loads(events[1]["message"])
    event_replay["version"].should.equal("0")
    event_replay["id"].should_not.equal(event_original["id"])
    event_replay["detail-type"].should.equal("type")
    event_replay["source"].should.equal("source")
    event_replay["time"].should.equal(event_original["time"])
    event_replay["region"].should.equal("eu-central-1")
    event_replay["resources"].should.be.empty
    event_replay["detail"].should.equal({"key": "value"})
    event_replay["replay-name"].should.equal("test-replay")
