import boto3
import json
import os

from datetime import datetime
from moto import mock_events, mock_logs, settings
from unittest import mock, SkipTest


@mock_events
def test_create_partner_event_bus():
    client_account = "111122223333"
    client = boto3.client("events", "us-east-1")
    client.create_partner_event_source(
        Name="mypartner/actions/action1", Account=client_account
    )
    resp = client.describe_partner_event_source(Name="mypartner/actions/action1")
    assert (
        resp["Arn"]
        == "arn:aws:events:us-east-1::event-source/aws.partner/mypartner/actions/action1"
    )
    assert resp["Name"] == "mypartner/actions/action1"


@mock_events
def test_describe_partner_event_busses():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't change accounts easily in ServerMode")
    # Having a separate partner account isn't 'strictly necessary - we could do that from the main account
    # But it makes it more obvious for the reader that we're accessing different accounts IMO
    partner_account = "111122223333"
    client_account = "444455556666"
    client = boto3.client("events", "us-east-1")
    name = "mypartner/actions/action1"
    with mock.patch.dict(os.environ, {"MOTO_ACCOUNT_ID": partner_account}):
        client.create_partner_event_source(Name=name, Account=client_account)

    with mock.patch.dict(os.environ, {"MOTO_ACCOUNT_ID": client_account}):
        resp = client.describe_event_source(Name=name)
        assert resp["Name"] == name
        assert resp["CreatedBy"] == "mypartner"
        assert resp["State"] == "ACTIVE"

        client.create_event_bus(Name=name, EventSourceName=name)
        resp = client.describe_event_bus(Name=name)
        assert resp["Name"] == name

    with mock.patch.dict(os.environ, {"MOTO_ACCOUNT_ID": partner_account}):
        client.delete_partner_event_source(Name=name, Account=client_account)

    with mock.patch.dict(os.environ, {"MOTO_ACCOUNT_ID": client_account}):
        resp = client.describe_event_source(Name=name)
        assert resp["State"] == "DELETED"


@mock_events
@mock_logs
def test_put_partner_events():
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Can't change accounts easily in ServerMode")

    partner_account = "111122223333"
    client_account = "444455556666"
    events = boto3.client("events", "us-east-1")
    logs = boto3.client("logs", region_name="us-east-1")
    name = "mypartner/actions/action1"
    with mock.patch.dict(os.environ, {"MOTO_ACCOUNT_ID": partner_account}):
        events.create_partner_event_source(Name=name, Account=client_account)

    with mock.patch.dict(os.environ, {"MOTO_ACCOUNT_ID": client_account}):
        events.create_event_bus(Name=name, EventSourceName=name)

        log_group_name = "/test-group"
        rule_name = "test-rule"
        logs.create_log_group(logGroupName=log_group_name)
        log_group_arn = (
            f"arn:aws:logs:us-east-1:{client_account}:log-group:{log_group_name}"
        )
        events.put_rule(
            Name=rule_name,
            EventPattern=json.dumps({"account": [client_account]}),
            State="ENABLED",
        )
        events.put_targets(
            Rule=rule_name,
            Targets=[{"Id": "logs", "Arn": log_group_arn}],
        )

    with mock.patch.dict(os.environ, {"MOTO_ACCOUNT_ID": partner_account}):
        resp = events.put_partner_events(
            Entries=[
                {
                    "Time": datetime.now(),
                    "Source": name,
                    "DetailType": "test-detail-type",
                    "Detail": json.dumps({"foo": "123", "bar": "123"}),
                }
            ]
        )
        assert resp["FailedEntryCount"] == 0

    with mock.patch.dict(os.environ, {"MOTO_ACCOUNT_ID": client_account}):
        log_events = logs.filter_log_events(logGroupName=log_group_name)["events"]
        assert len(log_events) == 1
        assert "test-detail-type" in log_events[0]["message"]
