import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

DB_INSTANCE_IDENTIFIER = "db-primary-1"


def _prepare_db_instance(client):
    resp = client.create_db_instance(
        DBInstanceIdentifier=DB_INSTANCE_IDENTIFIER,
        AllocatedStorage=10,
        Engine="postgres",
        DBName="staging-postgres",
        DBInstanceClass="db.m1.small",
        MasterUsername="root",
        MasterUserPassword="hunter2",
        Port=1234,
        DBSecurityGroups=["my_sg"],
    )
    return resp["DBInstance"]["DBInstanceIdentifier"]


@mock_aws
def test_create_event_subscription():
    client = boto3.client("rds", region_name="us-west-2")
    db_identifier = _prepare_db_instance(client)

    es = client.create_event_subscription(
        SubscriptionName=f"{db_identifier}-events",
        SnsTopicArn=f"arn:aws:sns::{ACCOUNT_ID}:{db_identifier}-events-topic",
        SourceType="db-instance",
        EventCategories=[
            "Backup",
            "Creation",
            "Deletion",
            "Failure",
            "Recovery",
            "Restoration",
        ],
        SourceIds=[db_identifier],
    ).get("EventSubscription")

    assert es["CustSubscriptionId"] == f"{db_identifier}-events"
    assert es["SnsTopicArn"] == (
        f"arn:aws:sns::{ACCOUNT_ID}:{db_identifier}-events-topic"
    )
    assert es["SourceType"] == "db-instance"
    assert es["EventCategoriesList"] == (
        ["Backup", "Creation", "Deletion", "Failure", "Recovery", "Restoration"]
    )
    assert es["SourceIdsList"] == [db_identifier]
    assert es["Enabled"] is False


@mock_aws
def test_create_event_fail_already_exists():
    client = boto3.client("rds", region_name="us-west-2")
    db_identifier = _prepare_db_instance(client)

    client.create_event_subscription(
        SubscriptionName=f"{db_identifier}-events",
        SnsTopicArn=f"arn:aws:sns::{ACCOUNT_ID}:{db_identifier}-events-topic",
    )

    with pytest.raises(ClientError) as ex:
        client.create_event_subscription(
            SubscriptionName=f"{db_identifier}-events",
            SnsTopicArn=f"arn:aws:sns::{ACCOUNT_ID}:{db_identifier}-events-topic",
            Enabled=True,
        )

    err = ex.value.response["Error"]

    assert err["Code"] == "SubscriptionAlreadyExist"
    assert err["Message"] == "Subscription db-primary-1-events already exists."


@mock_aws
def test_delete_event_subscription_fails_unknown_subscription():
    client = boto3.client("rds", region_name="us-west-2")
    with pytest.raises(ClientError) as ex:
        client.delete_event_subscription(SubscriptionName="my-db-events")

    err = ex.value.response["Error"]
    assert err["Code"] == "SubscriptionNotFound"
    assert err["Message"] == "Subscription my-db-events not found."


@mock_aws
def test_delete_event_subscription():
    client = boto3.client("rds", region_name="us-west-2")
    db_identifier = _prepare_db_instance(client)

    client.create_event_subscription(
        SubscriptionName=f"{db_identifier}-events",
        SnsTopicArn=f"arn:aws:sns::{ACCOUNT_ID}:{db_identifier}-events-topic",
    )

    es = client.delete_event_subscription(
        SubscriptionName=f"{db_identifier}-events"
    ).get("EventSubscription")

    assert es["CustSubscriptionId"] == f"{db_identifier}-events"
    assert es["SnsTopicArn"] == (
        f"arn:aws:sns::{ACCOUNT_ID}:{db_identifier}-events-topic"
    )


@mock_aws
def test_describe_event_subscriptions():
    client = boto3.client("rds", region_name="us-west-2")
    db_identifier = _prepare_db_instance(client)

    client.create_event_subscription(
        SubscriptionName=f"{db_identifier}-events",
        SnsTopicArn=f"arn:aws:sns::{ACCOUNT_ID}:{db_identifier}-events-topic",
    )

    subscriptions = client.describe_event_subscriptions().get("EventSubscriptionsList")

    assert len(subscriptions) == 1
    assert subscriptions[0]["CustSubscriptionId"] == f"{db_identifier}-events"


@mock_aws
def test_describe_event_subscriptions_fails_unknown_subscription():
    client = boto3.client("rds", region_name="us-west-2")
    with pytest.raises(ClientError) as ex:
        client.describe_event_subscriptions(SubscriptionName="my-db-events")

    err = ex.value.response["Error"]

    assert err["Code"] == "SubscriptionNotFound"
    assert err["Message"] == "Subscription my-db-events not found."
