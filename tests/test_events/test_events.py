import json
import random
import unittest
from datetime import datetime

import boto3
import sure  # noqa

from botocore.exceptions import ClientError
import pytest

from moto.core import ACCOUNT_ID
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
        "EventBusName": "test-bus",
    }

    client.put_rule(**rule_data)

    rules = client.list_rules()["Rules"]

    rules.should.have.length_of(1)
    rules[0]["Name"].should.equal(rule_data["Name"])
    rules[0]["ScheduleExpression"].should.equal(rule_data["ScheduleExpression"])
    rules[0]["EventPattern"].should.equal(rule_data["EventPattern"])
    rules[0]["EventBusName"].should.equal(rule_data["EventBusName"])
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

    # when
    response = client.create_archive(
        ArchiveName="test-archive",
        EventSourceArn="arn:aws:events:eu-central-1:{}:event-bus/default".format(
            ACCOUNT_ID
        ),
    )

    # then
    response["ArchiveArn"].should.equal(
        "arn:aws:events:eu-central-1:{}:archive/test-archive".format(ACCOUNT_ID)
    )
    response["CreationTime"].should.be.a(datetime)
    response["State"].should.equal("ENABLED")


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
        "1 validation error detected: Value 'invalid' at 'state' failed to satisfy constraint: "
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
        EventPattern=json.dumps({"DetailType": ["type"], "Source": ["test"]}),
    )
    client.create_archive(
        ArchiveName=name_3,
        EventSourceArn=event_bus_arn,
        EventPattern=json.dumps({"DetailType": ["type"], "Source": ["source"]}),
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
