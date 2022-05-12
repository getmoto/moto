import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import

from botocore.exceptions import ClientError
from moto import mock_rds
from moto.core import ACCOUNT_ID

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


@mock_rds
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

    es["CustSubscriptionId"].should.equal(f"{db_identifier}-events")
    es["SnsTopicArn"].should.equal(
        f"arn:aws:sns::{ACCOUNT_ID}:{db_identifier}-events-topic"
    )
    es["SourceType"].should.equal("db-instance")
    es["EventCategoriesList"].should.equal(
        ["Backup", "Creation", "Deletion", "Failure", "Recovery", "Restoration"]
    )
    es["SourceIdsList"].should.equal([db_identifier])
    es["Enabled"].should.equal(False)


@mock_rds
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

    err["Code"].should.equal("SubscriptionAlreadyExistFault")
    err["Message"].should.equal("Subscription db-primary-1-events already exists.")


@mock_rds
def test_delete_event_subscription_fails_unknown_subscription():
    client = boto3.client("rds", region_name="us-west-2")
    with pytest.raises(ClientError) as ex:
        client.delete_event_subscription(SubscriptionName="my-db-events")

    err = ex.value.response["Error"]
    err["Code"].should.equal("SubscriptionNotFoundFault")
    err["Message"].should.equal("Subscription my-db-events not found.")


@mock_rds
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

    es["CustSubscriptionId"].should.equal(f"{db_identifier}-events")
    es["SnsTopicArn"].should.equal(
        f"arn:aws:sns::{ACCOUNT_ID}:{db_identifier}-events-topic"
    )


@mock_rds
def test_describe_event_subscriptions():
    client = boto3.client("rds", region_name="us-west-2")
    db_identifier = _prepare_db_instance(client)

    client.create_event_subscription(
        SubscriptionName=f"{db_identifier}-events",
        SnsTopicArn=f"arn:aws:sns::{ACCOUNT_ID}:{db_identifier}-events-topic",
    )

    subscriptions = client.describe_event_subscriptions().get("EventSubscriptionsList")

    subscriptions.should.have.length_of(1)
    subscriptions[0]["CustSubscriptionId"].should.equal(f"{db_identifier}-events")


@mock_rds
def test_describe_event_subscriptions_fails_unknown_subscription():
    client = boto3.client("rds", region_name="us-west-2")
    with pytest.raises(ClientError) as ex:
        client.describe_event_subscriptions(SubscriptionName="my-db-events")

    err = ex.value.response["Error"]

    err["Code"].should.equal("SubscriptionNotFoundFault")
    err["Message"].should.equal("Subscription my-db-events not found.")
