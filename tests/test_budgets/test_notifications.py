import boto3
import pytest

from botocore.exceptions import ClientError
import sure  # noqa # pylint: disable=unused-import
from moto import mock_budgets
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID


@mock_budgets
def test_create_and_describe_notification():
    client = boto3.client("budgets", region_name="us-east-1")
    client.create_budget(
        AccountId=ACCOUNT_ID,
        Budget={
            "BudgetLimit": {"Amount": "10", "Unit": "USD"},
            "BudgetName": "testbudget",
            "TimeUnit": "DAILY",
            "BudgetType": "COST",
        },
        NotificationsWithSubscribers=[
            {
                "Notification": {
                    "NotificationType": "ACTUAL",
                    "ComparisonOperator": "EQUAL_TO",
                    "Threshold": 123.0,
                    "ThresholdType": "ABSOLUTE_VALUE",
                    "NotificationState": "ALARM",
                },
                "Subscribers": [
                    {"SubscriptionType": "EMAIL", "Address": "admin@moto.com"},
                ],
            }
        ],
    )

    res = client.describe_notifications_for_budget(
        AccountId=ACCOUNT_ID, BudgetName="testbudget"
    )
    res.should.have.key("Notifications").length_of(1)
    notification = res["Notifications"][0]
    notification.should.have.key("NotificationType").should.equal("ACTUAL")
    notification.should.have.key("ComparisonOperator").should.equal("EQUAL_TO")
    notification.should.have.key("Threshold").should.equal(123)
    notification.should.have.key("ThresholdType").should.equal("ABSOLUTE_VALUE")
    notification.should.have.key("NotificationState").should.equal("ALARM")


@mock_budgets
def test_create_notification():
    client = boto3.client("budgets", region_name="us-east-1")
    client.create_budget(
        AccountId=ACCOUNT_ID,
        Budget={
            "BudgetLimit": {"Amount": "10", "Unit": "USD"},
            "BudgetName": "testbudget",
            "TimeUnit": "DAILY",
            "BudgetType": "COST",
        },
        NotificationsWithSubscribers=[
            {
                "Notification": {
                    "NotificationType": "ACTUAL",
                    "ComparisonOperator": "EQUAL_TO",
                    "Threshold": 123.0,
                    "ThresholdType": "ABSOLUTE_VALUE",
                    "NotificationState": "ALARM",
                },
                "Subscribers": [
                    {"SubscriptionType": "EMAIL", "Address": "admin@moto.com"},
                ],
            }
        ],
    )

    res = client.create_notification(
        AccountId=ACCOUNT_ID,
        BudgetName="testbudget",
        Notification={
            "NotificationType": "ACTUAL",
            "ComparisonOperator": "GREATER_THAN",
            "Threshold": 0.0,
            "ThresholdType": "ABSOLUTE_VALUE",
            "NotificationState": "OK",
        },
        Subscribers=[{"SubscriptionType": "SNS", "Address": "arn:sns:topic:mytopic"}],
    )
    res["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    res = client.describe_notifications_for_budget(
        AccountId=ACCOUNT_ID, BudgetName="testbudget"
    )
    res.should.have.key("Notifications").length_of(2)
    n_1 = res["Notifications"][0]
    n_1.should.have.key("NotificationType").should.equal("ACTUAL")
    n_1.should.have.key("ComparisonOperator").should.equal("EQUAL_TO")
    n_1.should.have.key("Threshold").should.equal(123)
    n_1.should.have.key("ThresholdType").should.equal("ABSOLUTE_VALUE")
    n_1.should.have.key("NotificationState").should.equal("ALARM")
    n_2 = res["Notifications"][1]
    n_2.should.have.key("NotificationType").should.equal("ACTUAL")
    n_2.should.have.key("ComparisonOperator").should.equal("GREATER_THAN")
    n_2.should.have.key("Threshold").should.equal(0)
    n_2.should.have.key("ThresholdType").should.equal("ABSOLUTE_VALUE")
    n_2.should.have.key("NotificationState").should.equal("OK")


@mock_budgets
def test_create_notification_unknown_budget():
    client = boto3.client("budgets", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        client.create_notification(
            AccountId=ACCOUNT_ID,
            BudgetName="testbudget",
            Notification={
                "NotificationType": "FORECASTED",  # doesn't exist
                "ComparisonOperator": "EQUAL_TO",
                "Threshold": 123.0,
                "ThresholdType": "ABSOLUTE_VALUE",
                "NotificationState": "ALARM",
            },
            Subscribers=[{"SubscriptionType": "EMAIL", "Address": "admin@moto.com"}],
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("NotFoundException")
    err["Message"].should.equal(
        "Unable to create notification - the budget doesn't exist."
    )


@mock_budgets
def test_delete_notification():
    client = boto3.client("budgets", region_name="us-east-1")
    client.create_budget(
        AccountId=ACCOUNT_ID,
        Budget={
            "BudgetLimit": {"Amount": "10", "Unit": "USD"},
            "BudgetName": "testbudget",
            "TimeUnit": "DAILY",
            "BudgetType": "COST",
        },
        NotificationsWithSubscribers=[
            {
                "Notification": {
                    "NotificationType": "ACTUAL",
                    "ComparisonOperator": "EQUAL_TO",
                    "Threshold": 123.0,
                    "ThresholdType": "ABSOLUTE_VALUE",
                    "NotificationState": "ALARM",
                },
                "Subscribers": [
                    {"SubscriptionType": "EMAIL", "Address": "admin@moto.com"},
                ],
            }
        ],
    )

    client.delete_notification(
        AccountId=ACCOUNT_ID,
        BudgetName="testbudget",
        Notification={
            "NotificationType": "ACTUAL",
            "ComparisonOperator": "EQUAL_TO",
            "Threshold": 123.0,
            "ThresholdType": "ABSOLUTE_VALUE",
            "NotificationState": "ALARM",
        },
    )

    res = client.describe_notifications_for_budget(
        AccountId=ACCOUNT_ID, BudgetName="testbudget"
    )
    res.should.have.key("Notifications").length_of(0)


@mock_budgets
def test_delete_notification_unknown_budget():
    client = boto3.client("budgets", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        client.delete_notification(
            AccountId=ACCOUNT_ID,
            BudgetName="testbudget",
            Notification={
                "NotificationType": "FORECASTED",
                "ComparisonOperator": "EQUAL_TO",
                "Threshold": 123.0,
                "ThresholdType": "ABSOLUTE_VALUE",
                "NotificationState": "ALARM",
            },
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("NotFoundException")
    err["Message"].should.equal(
        "Unable to delete notification - the budget doesn't exist."
    )
