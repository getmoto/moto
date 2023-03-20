import json
import random
import unittest
from datetime import datetime, timezone

import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import
from botocore.exceptions import ClientError

from moto import mock_logs
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from moto.core.utils import iso_8601_datetime_without_milliseconds
from moto.events import mock_events

RULES = [
    {"Name": "test1", "ScheduleExpression": "rate(5 minutes)"},
    {
        "Name": "test2",
        "ScheduleExpression": "rate(1 minute)",
        "Tags": [{"Key": "tagk1", "Value": "tagv1"}],
    },
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


def generate_environment(add_targets=True):
    client = boto3.client("events", "us-west-2")

    for rule in RULES:
        client.put_rule(
            Name=rule["Name"],
            ScheduleExpression=rule.get("ScheduleExpression", ""),
            EventPattern=rule.get("EventPattern", ""),
            Tags=rule.get("Tags", []),
        )

        if add_targets:
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
def test_put_rule__where_event_bus_name_is_arn():
    client = boto3.client("events", "us-west-2")
    event_bus_name = "test-bus"
    event_bus_arn = client.create_event_bus(Name=event_bus_name)["EventBusArn"]

    rule_arn = client.put_rule(
        Name="my-event",
        EventPattern='{"source": ["test-source"]}',
        EventBusName=event_bus_arn,
    )["RuleArn"]
    assert rule_arn == f"arn:aws:events:us-west-2:{ACCOUNT_ID}:rule/test-bus/my-event"


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
    rules = response["Rules"]
    rules.should.have.length_of(len(RULES))


@mock_events
def test_list_rules_with_token():
    client = generate_environment()
    response = client.list_rules()
    response.shouldnt.have.key("NextToken")
    rules = response["Rules"]
    rules.should.have.length_of(len(RULES))
    #
    response = client.list_rules(Limit=1)
    response.should.have.key("NextToken")
    rules = response["Rules"]
    rules.should.have.length_of(1)
    #
    response = client.list_rules(NextToken=response["NextToken"])
    response.shouldnt.have.key("NextToken")
    rules = response["Rules"]
    rules.should.have.length_of(2)


@mock_events
def test_list_rules_with_prefix_and_token():
    client = generate_environment()
    response = client.list_rules(NamePrefix="test")
    response.shouldnt.have.key("NextToken")
    rules = response["Rules"]
    rules.should.have.length_of(len(RULES))
    #
    response = client.list_rules(NamePrefix="test", Limit=1)
    response.should.have.key("NextToken")
    rules = response["Rules"]
    rules.should.have.length_of(1)
    #
    response = client.list_rules(NamePrefix="test", NextToken=response["NextToken"])
    response.shouldnt.have.key("NextToken")
    rules = response["Rules"]
    rules.should.have.length_of(2)


@mock_events
def test_describe_rule():
    rule_name = get_random_rule()["Name"]
    client = generate_environment()
    response = client.describe_rule(Name=rule_name)

    response["Name"].should.equal(rule_name)
    response["Arn"].should.equal(
        f"arn:aws:events:us-west-2:{ACCOUNT_ID}:rule/{rule_name}"
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
        RoleArn=f"arn:aws:iam::{ACCOUNT_ID}:role/test-role",
        EventBusName=event_bus_name,
    )

    # when
    response = client.describe_rule(Name=rule_name, EventBusName=event_bus_name)

    # then
    response["Arn"].should.equal(
        f"arn:aws:events:eu-central-1:{ACCOUNT_ID}:rule/{event_bus_name}/{rule_name}"
    )
    response["CreatedBy"].should.equal(ACCOUNT_ID)
    response["Description"].should.equal("test rule")
    response["EventBusName"].should.equal(event_bus_name)
    json.loads(response["EventPattern"]).should.equal({"account": [ACCOUNT_ID]})
    response["Name"].should.equal(rule_name)
    response["RoleArn"].should.equal(f"arn:aws:iam::{ACCOUNT_ID}:role/test-role")
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
    with pytest.raises(ClientError) as ex:
        client.enable_rule(Name="junk")

    err = ex.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")


@mock_events
def test_disable_unknown_rule():
    client = generate_environment()

    with pytest.raises(ClientError) as ex:
        client.disable_rule(Name="unknown")
    err = ex.value.response["Error"]
    err["Message"].should.equal("Rule unknown does not exist.")


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
def test_list_rule_names_by_target_using_limit():
    test_1_target = TARGETS["test-target-1"]
    client = generate_environment()

    response = client.list_rule_names_by_target(TargetArn=test_1_target["Arn"], Limit=1)
    response.should.have.key("NextToken")
    response["RuleNames"].should.have.length_of(1)
    #
    response = client.list_rule_names_by_target(
        TargetArn=test_1_target["Arn"], NextToken=response["NextToken"]
    )
    response.shouldnt.have.key("NextToken")
    response["RuleNames"].should.have.length_of(1)


@mock_events
def test_delete_rule():
    client = generate_environment(add_targets=False)

    client.delete_rule(Name=RULES[0]["Name"])
    rules = client.list_rules()
    assert len(rules["Rules"]) == len(RULES) - 1


@mock_events
def test_delete_rule_with_targets():
    # given
    client = generate_environment()

    # when
    with pytest.raises(ClientError) as e:
        client.delete_rule(Name=RULES[0]["Name"])

    # then
    ex = e.value
    ex.operation_name.should.equal("DeleteRule")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("ValidationException")
    ex.response["Error"]["Message"].should.equal(
        "Rule can't be deleted since it has targets."
    )


@mock_events
def test_delete_unknown_rule():
    client = boto3.client("events", "us-west-1")
    resp = client.delete_rule(Name="unknown")

    # this fails silently - it just returns an empty 200. Verified against AWS.
    resp["ResponseMetadata"].should.have.key("HTTPStatusCode").equals(200)


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
def test_list_targets_by_rule_for_different_event_bus():
    client = generate_environment()

    client.create_event_bus(Name="newEventBus")

    client.put_rule(Name="test1", EventBusName="newEventBus", EventPattern="{}")
    client.put_targets(
        Rule="test1",
        EventBusName="newEventBus",
        Targets=[
            {
                "Id": "newtarget",
                "Arn": "arn:",
            }
        ],
    )

    # Total targets with this rule is 7, but, from the docs:
    # If you omit [the eventBusName-parameter], the default event bus is used.
    targets = client.list_targets_by_rule(Rule="test1")["Targets"]
    assert len([t["Id"] for t in targets]) == 6

    targets = client.list_targets_by_rule(Rule="test1", EventBusName="default")[
        "Targets"
    ]
    assert len([t["Id"] for t in targets]) == 6

    targets = client.list_targets_by_rule(Rule="test1", EventBusName="newEventBus")[
        "Targets"
    ]
    assert [t["Id"] for t in targets] == ["newtarget"]


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
    client.put_rule(Name="test1", ScheduleExpression="rate(5 minutes)", EventPattern="")

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

    client.put_rule(Name="test1", ScheduleExpression="rate(1 minute)", EventPattern="")

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
                    "Arn": f"arn:aws:sqs:eu-central-1:{ACCOUNT_ID}:test-queue.fifo",
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
def test_permission_policy():
    client = boto3.client("events", "eu-central-1")

    policy = {
        "Statement": [
            {
                "Sid": "asdf",
                "Action": "events:PutEvents",
                "Principal": "111111111111",
                "StatementId": "Account1",
                "Effect": "n/a",
                "Resource": "n/a",
            }
        ]
    }
    client.put_permission(Policy=json.dumps(policy))

    resp = client.describe_event_bus()
    resp_policy = json.loads(resp["Policy"])
    resp_policy["Statement"].should.have.length_of(1)
    resp_policy["Statement"][0]["Sid"].should.equal("asdf")


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
        f"arn:aws:events:us-east-1:{ACCOUNT_ID}:event-bus/test-bus"
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
        f"arn:aws:events:us-east-1:{ACCOUNT_ID}:event-bus/default"
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
        f"arn:aws:events:us-east-1:{ACCOUNT_ID}:event-bus/test-bus"
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
                    "Resource": f"arn:aws:events:us-east-1:{ACCOUNT_ID}:event-bus/test-bus",
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
                "Arn": f"arn:aws:events:us-east-1:{ACCOUNT_ID}:event-bus/default",
            },
            {
                "Name": "other-bus-1",
                "Arn": f"arn:aws:events:us-east-1:{ACCOUNT_ID}:event-bus/other-bus-1",
            },
            {
                "Name": "other-bus-2",
                "Arn": f"arn:aws:events:us-east-1:{ACCOUNT_ID}:event-bus/other-bus-2",
            },
            {
                "Name": "test-bus-1",
                "Arn": f"arn:aws:events:us-east-1:{ACCOUNT_ID}:event-bus/test-bus-1",
            },
            {
                "Name": "test-bus-2",
                "Arn": f"arn:aws:events:us-east-1:{ACCOUNT_ID}:event-bus/test-bus-2",
            },
        ]
    )

    response = client.list_event_buses(NamePrefix="other-bus")

    response["EventBuses"].should.have.length_of(2)
    sorted(response["EventBuses"], key=lambda i: i["Name"]).should.equal(
        [
            {
                "Name": "other-bus-1",
                "Arn": f"arn:aws:events:us-east-1:{ACCOUNT_ID}:event-bus/other-bus-1",
            },
            {
                "Name": "other-bus-2",
                "Arn": f"arn:aws:events:us-east-1:{ACCOUNT_ID}:event-bus/other-bus-2",
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
                "Arn": f"arn:aws:events:us-east-1:{ACCOUNT_ID}:event-bus/default",
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
def test_create_rule_with_tags():
    client = generate_environment()
    rule_name = "test2"
    rule_arn = client.describe_rule(Name=rule_name).get("Arn")

    actual = client.list_tags_for_resource(ResourceARN=rule_arn)["Tags"]
    actual.should.equal([{"Key": "tagk1", "Value": "tagv1"}])


@mock_events
def test_delete_rule_with_tags():
    client = generate_environment(add_targets=False)
    rule_name = "test2"
    rule_arn = client.describe_rule(Name=rule_name).get("Arn")
    client.delete_rule(Name=rule_name)

    with pytest.raises(ClientError) as ex:
        client.list_tags_for_resource(ResourceARN=rule_arn)
    err = ex.value.response["Error"]
    err["Message"].should.equal("Rule test2 does not exist on EventBus default.")

    with pytest.raises(ClientError) as ex:
        client.describe_rule(Name=rule_name)
    err = ex.value.response["Error"]
    err["Message"].should.equal("Rule test2 does not exist.")


@mock_events
def test_rule_tagging_happy():
    client = generate_environment()
    rule_name = "test1"
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
            ResourceARN=f"arn:aws:events:eu-central-1:{ACCOUNT_ID}:rule/unknown",
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
            ResourceARN=f"arn:aws:events:eu-central-1:{ACCOUNT_ID}:rule/unknown",
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
            ResourceARN=f"arn:aws:events:eu-central-1:{ACCOUNT_ID}:rule/unknown"
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
        EventSourceArn=f"arn:aws:events:eu-central-1:{ACCOUNT_ID}:event-bus/default",
    )

    # then
    response["ArchiveArn"].should.equal(
        f"arn:aws:events:eu-central-1:{ACCOUNT_ID}:archive/{archive_name}"
    )
    response["CreationTime"].should.be.a(datetime)
    response["State"].should.equal("ENABLED")

    # check for archive rule existence
    rule_name = f"Events-Archive-{archive_name}"
    response = client.describe_rule(Name=rule_name)

    response["Arn"].should.equal(
        f"arn:aws:events:eu-central-1:{ACCOUNT_ID}:rule/{rule_name}"
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
        f"arn:aws:events:eu-central-1:{ACCOUNT_ID}:archive/test-archive"
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
                f"arn:aws:events:eu-central-1:{ACCOUNT_ID}:event-bus/default"
            ),
        )

    # then
    ex = e.value
    ex.operation_name.should.equal("CreateArchive")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("ValidationException")
    ex.response["Error"]["Message"].should.equal(
        " 1 validation error detected: "
        f"Value '{name}' at 'archiveName' failed to satisfy constraint: "
        "Member must have length less than or equal to 48"
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
                f"arn:aws:events:eu-central-1:{ACCOUNT_ID}:event-bus/default"
            ),
            EventPattern="invalid",
        )

    # then
    ex = e.value
    ex.operation_name.should.equal("CreateArchive")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("InvalidEventPatternException")
    ex.response["Error"]["Message"].should.equal(
        "Event pattern is not valid. Reason: Invalid JSON"
    )


@mock_events
def test_create_archive_error_invalid_event_pattern_not_an_array():
    # given
    client = boto3.client("events", "eu-central-1")

    # when
    with pytest.raises(ClientError) as e:
        client.create_archive(
            ArchiveName="test-archive",
            EventSourceArn=(
                f"arn:aws:events:eu-central-1:{ACCOUNT_ID}:event-bus/default"
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
    ex.response["Error"]["Message"].should.equal(
        "Event pattern is not valid. Reason: 'key_6' must be an object or an array"
    )


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
                f"arn:aws:events:eu-central-1:{ACCOUNT_ID}:event-bus/{event_bus_name}"
            ),
        )

    # then
    ex = e.value
    ex.operation_name.should.equal("CreateArchive")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("ResourceNotFoundException")
    ex.response["Error"]["Message"].should.equal(
        f"Event bus {event_bus_name} does not exist."
    )


@mock_events
def test_create_archive_error_duplicate():
    # given
    client = boto3.client("events", "eu-central-1")
    name = "test-archive"
    source_arn = f"arn:aws:events:eu-central-1:{ACCOUNT_ID}:event-bus/default"
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
    source_arn = f"arn:aws:events:eu-central-1:{ACCOUNT_ID}:event-bus/default"
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
        f"arn:aws:events:eu-central-1:{ACCOUNT_ID}:archive/{name}"
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
    ex.response["Error"]["Message"].should.equal(f"Archive {name} does not exist.")


@mock_events
def test_list_archives():
    # given
    client = boto3.client("events", "eu-central-1")
    name = "test-archive"
    source_arn = f"arn:aws:events:eu-central-1:{ACCOUNT_ID}:event-bus/default"
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
    source_arn = f"arn:aws:events:eu-central-1:{ACCOUNT_ID}:event-bus/default"
    client.create_archive(ArchiveName="test", EventSourceArn=source_arn)
    client.create_archive(ArchiveName="test-archive", EventSourceArn=source_arn)

    # when
    archives = client.list_archives(NamePrefix="test-")["Archives"]

    # then
    archives.should.have.length_of(1)
    archives[0]["ArchiveName"].should.equal("test-archive")


@mock_events
def test_list_archives_with_source_arn():
    # given
    client = boto3.client("events", "eu-central-1")
    source_arn = f"arn:aws:events:eu-central-1:{ACCOUNT_ID}:event-bus/default"
    source_arn_2 = client.create_event_bus(Name="test-bus")["EventBusArn"]
    client.create_archive(ArchiveName="test", EventSourceArn=source_arn)
    client.create_archive(ArchiveName="test-archive", EventSourceArn=source_arn_2)

    # when
    archives = client.list_archives(EventSourceArn=source_arn)["Archives"]

    # then
    archives.should.have.length_of(1)
    archives[0]["ArchiveName"].should.equal("test")


@mock_events
def test_list_archives_with_state():
    # given
    client = boto3.client("events", "eu-central-1")
    source_arn = f"arn:aws:events:eu-central-1:{ACCOUNT_ID}:event-bus/default"
    client.create_archive(ArchiveName="test", EventSourceArn=source_arn)
    client.create_archive(ArchiveName="test-archive", EventSourceArn=source_arn)

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
    source_arn = f"arn:aws:events:eu-central-1:{ACCOUNT_ID}:event-bus/default"
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
        EventSourceArn=f"arn:aws:events:eu-central-1:{ACCOUNT_ID}:event-bus/default",
    )

    # when
    with pytest.raises(ClientError) as e:
        client.update_archive(ArchiveName=name, EventPattern="invalid")

    # then
    ex = e.value
    ex.operation_name.should.equal("UpdateArchive")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("InvalidEventPatternException")
    ex.response["Error"]["Message"].should.equal(
        "Event pattern is not valid. Reason: Invalid JSON"
    )


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
    ex.response["Error"]["Message"].should.equal(f"Archive {name} does not exist.")


@mock_events
def test_delete_archive():
    # given
    client = boto3.client("events", "eu-central-1")
    name = "test-archive"
    client.create_archive(
        ArchiveName=name,
        EventSourceArn=f"arn:aws:events:eu-central-1:{ACCOUNT_ID}:event-bus/default",
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
    ex.response["Error"]["Message"].should.equal(f"Archive {name} does not exist.")


@mock_events
def test_archive_actual_events():
    # given
    client = boto3.client("events", "eu-central-1")
    name = "test-archive"
    name_2 = "test-archive-no-match"
    name_3 = "test-archive-matches"
    event_bus_arn = f"arn:aws:events:eu-central-1:{ACCOUNT_ID}:event-bus/default"
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
    event_bus_arn = f"arn:aws:events:eu-central-1:{ACCOUNT_ID}:event-bus/default"
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
    event_bus_arn = f"arn:aws:events:eu-central-1:{ACCOUNT_ID}:event-bus/default"
    archive_arn = client.create_archive(
        ArchiveName="test-archive", EventSourceArn=event_bus_arn
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
        f"arn:aws:events:eu-central-1:{ACCOUNT_ID}:replay/{name}"
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
            EventSourceArn=f"arn:aws:events:eu-central-1:{ACCOUNT_ID}:archive/test",
            EventStartTime=datetime(2021, 2, 1),
            EventEndTime=datetime(2021, 2, 2),
            Destination={
                "Arn": f"arn:aws:events:eu-central-1:{ACCOUNT_ID}:event-bus/{event_bus_name}",
            },
        )

    # then
    ex = e.value
    ex.operation_name.should.equal("StartReplay")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("ResourceNotFoundException")
    ex.response["Error"]["Message"].should.equal(
        f"Event bus {event_bus_name} does not exist."
    )


@mock_events
def test_start_replay_error_invalid_event_bus_arn():
    # given
    client = boto3.client("events", "eu-central-1")

    # when
    with pytest.raises(ClientError) as e:
        client.start_replay(
            ReplayName="test",
            EventSourceArn=f"arn:aws:events:eu-central-1:{ACCOUNT_ID}:archive/test",
            EventStartTime=datetime(2021, 2, 1),
            EventEndTime=datetime(2021, 2, 2),
            Destination={
                "Arn": "invalid",
            },
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
            EventSourceArn=f"arn:aws:events:eu-central-1:{ACCOUNT_ID}:archive/{archive_name}",
            EventStartTime=datetime(2021, 2, 1),
            EventEndTime=datetime(2021, 2, 2),
            Destination={
                "Arn": f"arn:aws:events:eu-central-1:{ACCOUNT_ID}:event-bus/default",
            },
        )

    # then
    ex = e.value
    ex.operation_name.should.equal("StartReplay")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("ValidationException")
    ex.response["Error"]["Message"].should.equal(
        "Parameter EventSourceArn is not valid. "
        f"Reason: Archive {archive_name} does not exist."
    )


@mock_events
def test_start_replay_error_cross_event_bus():
    # given
    client = boto3.client("events", "eu-central-1")
    archive_arn = client.create_archive(
        ArchiveName="test-archive",
        EventSourceArn=f"arn:aws:events:eu-central-1:{ACCOUNT_ID}:event-bus/default",
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
    event_bus_arn = f"arn:aws:events:eu-central-1:{ACCOUNT_ID}:event-bus/default"
    archive_arn = client.create_archive(
        ArchiveName="test-archive", EventSourceArn=event_bus_arn
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
    event_bus_arn = f"arn:aws:events:eu-central-1:{ACCOUNT_ID}:event-bus/default"
    archive_arn = client.create_archive(
        ArchiveName="test-archive", EventSourceArn=event_bus_arn
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
    ex.response["Error"]["Message"].should.equal(f"Replay {name} already exists.")


@mock_events
def test_describe_replay():
    # given
    client = boto3.client("events", "eu-central-1")
    name = "test-replay"
    event_bus_arn = f"arn:aws:events:eu-central-1:{ACCOUNT_ID}:event-bus/default"
    archive_arn = client.create_archive(
        ArchiveName="test-archive", EventSourceArn=event_bus_arn
    )["ArchiveArn"]
    client.start_replay(
        ReplayName=name,
        Description="test replay",
        EventSourceArn=archive_arn,
        EventStartTime=datetime(2021, 2, 1, tzinfo=timezone.utc),
        EventEndTime=datetime(2021, 2, 2, tzinfo=timezone.utc),
        Destination={"Arn": event_bus_arn},
    )

    # when
    response = client.describe_replay(ReplayName=name)

    # then
    response["Description"].should.equal("test replay")
    response["Destination"].should.equal({"Arn": event_bus_arn})
    response["EventSourceArn"].should.equal(archive_arn)
    response["EventStartTime"].should.equal(datetime(2021, 2, 1, tzinfo=timezone.utc))
    response["EventEndTime"].should.equal(datetime(2021, 2, 2, tzinfo=timezone.utc))
    response["ReplayArn"].should.equal(
        f"arn:aws:events:eu-central-1:{ACCOUNT_ID}:replay/{name}"
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
    ex.response["Error"]["Message"].should.equal(f"Replay {name} does not exist.")


@mock_events
def test_list_replays():
    # given
    client = boto3.client("events", "eu-central-1")
    name = "test-replay"
    event_bus_arn = f"arn:aws:events:eu-central-1:{ACCOUNT_ID}:event-bus/default"
    archive_arn = client.create_archive(
        ArchiveName="test-replay", EventSourceArn=event_bus_arn
    )["ArchiveArn"]
    client.start_replay(
        ReplayName=name,
        Description="test replay",
        EventSourceArn=archive_arn,
        EventStartTime=datetime(2021, 2, 1, tzinfo=timezone.utc),
        EventEndTime=datetime(2021, 2, 2, tzinfo=timezone.utc),
        Destination={"Arn": event_bus_arn},
    )

    # when
    replays = client.list_replays()["Replays"]

    # then
    replays.should.have.length_of(1)
    replay = replays[0]
    replay["EventSourceArn"].should.equal(archive_arn)
    replay["EventStartTime"].should.equal(datetime(2021, 2, 1, tzinfo=timezone.utc))
    replay["EventEndTime"].should.equal(datetime(2021, 2, 2, tzinfo=timezone.utc))
    replay["ReplayName"].should.equal(name)
    replay["ReplayStartTime"].should.be.a(datetime)
    replay["ReplayEndTime"].should.be.a(datetime)
    replay["State"].should.equal("COMPLETED")


@mock_events
def test_list_replays_with_name_prefix():
    # given
    client = boto3.client("events", "eu-central-1")
    event_bus_arn = f"arn:aws:events:eu-central-1:{ACCOUNT_ID}:event-bus/default"
    archive_arn = client.create_archive(
        ArchiveName="test-replay", EventSourceArn=event_bus_arn
    )["ArchiveArn"]
    client.start_replay(
        ReplayName="test",
        EventSourceArn=archive_arn,
        EventStartTime=datetime(2021, 1, 1, tzinfo=timezone.utc),
        EventEndTime=datetime(2021, 1, 2, tzinfo=timezone.utc),
        Destination={"Arn": event_bus_arn},
    )
    client.start_replay(
        ReplayName="test-replay",
        EventSourceArn=archive_arn,
        EventStartTime=datetime(2021, 2, 1, tzinfo=timezone.utc),
        EventEndTime=datetime(2021, 2, 2, tzinfo=timezone.utc),
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
    event_bus_arn = f"arn:aws:events:eu-central-1:{ACCOUNT_ID}:event-bus/default"
    archive_arn = client.create_archive(
        ArchiveName="test-replay", EventSourceArn=event_bus_arn
    )["ArchiveArn"]
    client.start_replay(
        ReplayName="test",
        EventSourceArn=archive_arn,
        EventStartTime=datetime(2021, 1, 1, tzinfo=timezone.utc),
        EventEndTime=datetime(2021, 1, 2, tzinfo=timezone.utc),
        Destination={"Arn": event_bus_arn},
    )
    client.start_replay(
        ReplayName="test-replay",
        EventSourceArn=archive_arn,
        EventStartTime=datetime(2021, 2, 1, tzinfo=timezone.utc),
        EventEndTime=datetime(2021, 2, 2, tzinfo=timezone.utc),
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
    event_bus_arn = f"arn:aws:events:eu-central-1:{ACCOUNT_ID}:event-bus/default"
    archive_arn = client.create_archive(
        ArchiveName="test-replay", EventSourceArn=event_bus_arn
    )["ArchiveArn"]
    client.start_replay(
        ReplayName="test",
        EventSourceArn=archive_arn,
        EventStartTime=datetime(2021, 1, 1, tzinfo=timezone.utc),
        EventEndTime=datetime(2021, 1, 2, tzinfo=timezone.utc),
        Destination={"Arn": event_bus_arn},
    )
    client.start_replay(
        ReplayName="test-replay",
        EventSourceArn=archive_arn,
        EventStartTime=datetime(2021, 2, 1, tzinfo=timezone.utc),
        EventEndTime=datetime(2021, 2, 2, tzinfo=timezone.utc),
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
    event_bus_arn = f"arn:aws:events:eu-central-1:{ACCOUNT_ID}:event-bus/default"
    archive_arn = client.create_archive(
        ArchiveName="test-archive", EventSourceArn=event_bus_arn
    )["ArchiveArn"]
    client.start_replay(
        ReplayName=name,
        Description="test replay",
        EventSourceArn=archive_arn,
        EventStartTime=datetime(2021, 2, 1, tzinfo=timezone.utc),
        EventEndTime=datetime(2021, 2, 2, tzinfo=timezone.utc),
        Destination={"Arn": event_bus_arn},
    )

    # when
    response = client.cancel_replay(ReplayName=name)

    # then
    response["ReplayArn"].should.equal(
        f"arn:aws:events:eu-central-1:{ACCOUNT_ID}:replay/{name}"
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
    ex.response["Error"]["Message"].should.equal(f"Replay {name} does not exist.")


@mock_events
def test_cancel_replay_error_illegal_state():
    # given
    client = boto3.client("events", "eu-central-1")
    name = "test-replay"
    event_bus_arn = f"arn:aws:events:eu-central-1:{ACCOUNT_ID}:event-bus/default"
    archive_arn = client.create_archive(
        ArchiveName="test-archive", EventSourceArn=event_bus_arn
    )["ArchiveArn"]
    client.start_replay(
        ReplayName=name,
        Description="test replay",
        EventSourceArn=archive_arn,
        EventStartTime=datetime(2021, 2, 1, tzinfo=timezone.utc),
        EventEndTime=datetime(2021, 2, 2, tzinfo=timezone.utc),
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
        f"Replay {name} is not in a valid state for this operation."
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
    event_bus_arn = f"arn:aws:events:eu-central-1:{ACCOUNT_ID}:event-bus/default"
    client.put_rule(Name=rule_name, EventPattern=json.dumps({"account": [ACCOUNT_ID]}))
    client.put_targets(
        Rule=rule_name,
        Targets=[
            {
                "Id": "test",
                "Arn": f"arn:aws:logs:eu-central-1:{ACCOUNT_ID}:log-group:{log_group_name}",
            }
        ],
    )
    archive_arn = client.create_archive(
        ArchiveName="test-archive", EventSourceArn=event_bus_arn
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
    event_original["id"].should_not.equal(None)
    event_original["detail-type"].should.equal("type")
    event_original["source"].should.equal("source")
    event_original["time"].should.equal(
        iso_8601_datetime_without_milliseconds(event_time)
    )
    event_original["region"].should.equal("eu-central-1")
    event_original["resources"].should.equal([])
    event_original["detail"].should.equal({"key": "value"})
    event_original.should_not.have.key("replay-name")

    event_replay = json.loads(events[1]["message"])
    event_replay["version"].should.equal("0")
    event_replay["id"].should_not.equal(event_original["id"])
    event_replay["detail-type"].should.equal("type")
    event_replay["source"].should.equal("source")
    event_replay["time"].should.equal(event_original["time"])
    event_replay["region"].should.equal("eu-central-1")
    event_replay["resources"].should.equal([])
    event_replay["detail"].should.equal({"key": "value"})
    event_replay["replay-name"].should.equal("test-replay")


@mock_events
def test_create_and_list_connections():
    client = boto3.client("events", "eu-central-1")

    response = client.list_connections()

    assert len(response.get("Connections")) == 0

    response = client.create_connection(
        Name="test",
        Description="test description",
        AuthorizationType="API_KEY",
        AuthParameters={
            "ApiKeyAuthParameters": {"ApiKeyName": "test", "ApiKeyValue": "test"}
        },
    )

    response.get("ConnectionArn").should.contain(
        f"arn:aws:events:eu-central-1:{ACCOUNT_ID}:connection/test/"
    )

    response = client.list_connections()

    response.get("Connections")[0].get("ConnectionArn").should.contain(
        f"arn:aws:events:eu-central-1:{ACCOUNT_ID}:connection/test/"
    )


@mock_events
def test_create_and_describe_connection():
    client = boto3.client("events", "eu-central-1")

    client.create_connection(
        Name="test",
        Description="test description",
        AuthorizationType="API_KEY",
        AuthParameters={
            "ApiKeyAuthParameters": {"ApiKeyName": "test", "ApiKeyValue": "test"}
        },
    )

    description = client.describe_connection(Name="test")

    description["Name"].should.equal("test")
    description["Description"].should.equal("test description")
    description["AuthorizationType"].should.equal("API_KEY")
    description["ConnectionState"].should.equal("AUTHORIZED")
    description.should.have.key("CreationTime")


@mock_events
def test_create_and_update_connection():
    client = boto3.client("events", "eu-central-1")

    client.create_connection(
        Name="test",
        Description="test description",
        AuthorizationType="API_KEY",
        AuthParameters={
            "ApiKeyAuthParameters": {"ApiKeyName": "test", "ApiKeyValue": "test"}
        },
    )

    client.update_connection(Name="test", Description="updated desc")

    description = client.describe_connection(Name="test")

    description["Name"].should.equal("test")
    description["Description"].should.equal("updated desc")
    description["AuthorizationType"].should.equal("API_KEY")
    description["ConnectionState"].should.equal("AUTHORIZED")
    description.should.have.key("CreationTime")


@mock_events
def test_update_unknown_connection():
    client = boto3.client("events", "eu-north-1")

    with pytest.raises(ClientError) as ex:
        client.update_connection(Name="unknown")
    err = ex.value.response["Error"]
    err["Message"].should.equal("Connection 'unknown' does not exist.")


@mock_events
def test_delete_connection():
    client = boto3.client("events", "eu-central-1")

    conns = client.list_connections()["Connections"]
    conns.should.have.length_of(0)

    client.create_connection(
        Name="test",
        Description="test description",
        AuthorizationType="API_KEY",
        AuthParameters={
            "ApiKeyAuthParameters": {"ApiKeyName": "test", "ApiKeyValue": "test"}
        },
    )

    conns = client.list_connections()["Connections"]
    conns.should.have.length_of(1)

    client.delete_connection(Name="test")

    conns = client.list_connections()["Connections"]
    conns.should.have.length_of(0)


@mock_events
def test_create_and_list_api_destinations():
    client = boto3.client("events", "eu-central-1")

    response = client.create_connection(
        Name="test",
        Description="test description",
        AuthorizationType="API_KEY",
        AuthParameters={
            "ApiKeyAuthParameters": {"ApiKeyName": "test", "ApiKeyValue": "test"}
        },
    )

    destination_response = client.create_api_destination(
        Name="test",
        Description="test-description",
        ConnectionArn=response.get("ConnectionArn"),
        InvocationEndpoint="www.google.com",
        HttpMethod="GET",
    )

    arn_without_uuid = f"arn:aws:events:eu-central-1:{ACCOUNT_ID}:api-destination/test/"
    assert destination_response.get("ApiDestinationArn").startswith(arn_without_uuid)
    assert destination_response.get("ApiDestinationState") == "ACTIVE"

    destination_response = client.describe_api_destination(Name="test")

    assert destination_response.get("ApiDestinationArn").startswith(arn_without_uuid)

    assert destination_response.get("Name") == "test"
    assert destination_response.get("ApiDestinationState") == "ACTIVE"

    destination_response = client.list_api_destinations()
    assert (
        destination_response.get("ApiDestinations")[0]
        .get("ApiDestinationArn")
        .startswith(arn_without_uuid)
    )

    assert destination_response.get("ApiDestinations")[0].get("Name") == "test"
    assert (
        destination_response.get("ApiDestinations")[0].get("ApiDestinationState")
        == "ACTIVE"
    )


@pytest.mark.parametrize(
    "key,initial_value,updated_value",
    [
        ("Description", "my aspi dest", "my actual api dest"),
        ("InvocationEndpoint", "www.google.com", "www.google.cz"),
        ("InvocationRateLimitPerSecond", 1, 32),
        ("HttpMethod", "GET", "PATCH"),
    ],
)
@mock_events
def test_create_and_update_api_destination(key, initial_value, updated_value):
    client = boto3.client("events", "eu-central-1")

    response = client.create_connection(
        Name="test",
        Description="test description",
        AuthorizationType="API_KEY",
        AuthParameters={
            "ApiKeyAuthParameters": {"ApiKeyName": "test", "ApiKeyValue": "test"}
        },
    )

    default_params = {
        "Name": "test",
        "Description": "test-description",
        "ConnectionArn": response.get("ConnectionArn"),
        "InvocationEndpoint": "www.google.com",
        "HttpMethod": "GET",
    }
    default_params.update({key: initial_value})

    client.create_api_destination(**default_params)
    destination = client.describe_api_destination(Name="test")
    destination[key].should.equal(initial_value)

    client.update_api_destination(Name="test", **dict({key: updated_value}))

    destination = client.describe_api_destination(Name="test")
    destination[key].should.equal(updated_value)


@mock_events
def test_delete_api_destination():
    client = boto3.client("events", "eu-central-1")

    client.list_api_destinations()["ApiDestinations"].should.have.length_of(0)

    response = client.create_connection(
        Name="test",
        AuthorizationType="API_KEY",
        AuthParameters={
            "ApiKeyAuthParameters": {"ApiKeyName": "test", "ApiKeyValue": "test"}
        },
    )

    client.create_api_destination(
        Name="testdest",
        ConnectionArn=response.get("ConnectionArn"),
        InvocationEndpoint="www.google.com",
        HttpMethod="GET",
    )

    client.list_api_destinations()["ApiDestinations"].should.have.length_of(1)

    client.delete_api_destination(Name="testdest")

    client.list_api_destinations()["ApiDestinations"].should.have.length_of(0)


@mock_events
def test_describe_unknown_api_destination():
    client = boto3.client("events", "eu-central-1")

    with pytest.raises(ClientError) as ex:
        client.describe_api_destination(Name="unknown")
    err = ex.value.response["Error"]
    err["Message"].should.equal("An api-destination 'unknown' does not exist.")


@mock_events
def test_delete_unknown_api_destination():
    client = boto3.client("events", "eu-central-1")

    with pytest.raises(ClientError) as ex:
        client.delete_api_destination(Name="unknown")
    err = ex.value.response["Error"]
    err["Message"].should.equal("An api-destination 'unknown' does not exist.")


# Scenarios for describe_connection
# Scenario 01: Success
# Scenario 02: Failure - Connection not present
@mock_events
def test_describe_connection_success():
    # Given
    conn_name = "test_conn_name"
    conn_description = "test_conn_description"
    auth_type = "API_KEY"
    auth_params = {
        "ApiKeyAuthParameters": {"ApiKeyName": "test", "ApiKeyValue": "test"}
    }

    client = boto3.client("events", "eu-central-1")
    _ = client.create_connection(
        Name=conn_name,
        Description=conn_description,
        AuthorizationType=auth_type,
        AuthParameters=auth_params,
    )

    # When
    response = client.describe_connection(Name=conn_name)

    # Then
    assert response["Name"] == conn_name
    assert response["Description"] == conn_description
    assert response["AuthorizationType"] == auth_type
    expected_auth_param = {"ApiKeyAuthParameters": {"ApiKeyName": "test"}}
    assert response["AuthParameters"] == expected_auth_param


@mock_events
def test_describe_connection_not_present():
    conn_name = "test_conn_name"

    client = boto3.client("events", "eu-central-1")

    # When/Then
    with pytest.raises(ClientError):
        _ = client.describe_connection(Name=conn_name)


# Scenarios for delete_connection
# Scenario 01: Success
# Scenario 02: Failure - Connection not present


@mock_events
def test_delete_connection_success():
    # Given
    conn_name = "test_conn_name"
    conn_description = "test_conn_description"
    auth_type = "API_KEY"
    auth_params = {
        "ApiKeyAuthParameters": {"ApiKeyName": "test", "ApiKeyValue": "test"}
    }

    client = boto3.client("events", "eu-central-1")
    created_connection = client.create_connection(
        Name=conn_name,
        Description=conn_description,
        AuthorizationType=auth_type,
        AuthParameters=auth_params,
    )

    # When
    response = client.delete_connection(Name=conn_name)

    # Then
    assert response["ConnectionArn"] == created_connection["ConnectionArn"]
    assert response["ConnectionState"] == created_connection["ConnectionState"]
    assert response["CreationTime"] == created_connection["CreationTime"]

    with pytest.raises(ClientError):
        _ = client.describe_connection(Name=conn_name)


@mock_events
def test_delete_connection_not_present():
    conn_name = "test_conn_name"

    client = boto3.client("events", "eu-central-1")

    # When/Then
    with pytest.raises(ClientError):
        _ = client.delete_connection(Name=conn_name)
