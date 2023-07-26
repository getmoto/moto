import boto3
import pytest

from botocore.exceptions import ClientError
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
    assert len(res["Notifications"]) == 1
    notification = res["Notifications"][0]
    assert notification["NotificationType"] == "ACTUAL"
    assert notification["ComparisonOperator"] == "EQUAL_TO"
    assert notification["Threshold"] == 123
    assert notification["ThresholdType"] == "ABSOLUTE_VALUE"
    assert notification["NotificationState"] == "ALARM"


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
    assert res["ResponseMetadata"]["HTTPStatusCode"] == 200

    res = client.describe_notifications_for_budget(
        AccountId=ACCOUNT_ID, BudgetName="testbudget"
    )
    assert len(res["Notifications"]) == 2
    n_1 = res["Notifications"][0]
    assert n_1["NotificationType"] == "ACTUAL"
    assert n_1["ComparisonOperator"] == "EQUAL_TO"
    assert n_1["Threshold"] == 123
    assert n_1["ThresholdType"] == "ABSOLUTE_VALUE"
    assert n_1["NotificationState"] == "ALARM"
    n_2 = res["Notifications"][1]
    assert n_2["NotificationType"] == "ACTUAL"
    assert n_2["ComparisonOperator"] == "GREATER_THAN"
    assert n_2["Threshold"] == 0
    assert n_2["ThresholdType"] == "ABSOLUTE_VALUE"
    assert n_2["NotificationState"] == "OK"


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
    assert err["Code"] == "NotFoundException"
    assert err["Message"] == "Unable to create notification - the budget doesn't exist."


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
    assert len(res["Notifications"]) == 0


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
    assert err["Code"] == "NotFoundException"
    assert err["Message"] == "Unable to delete notification - the budget doesn't exist."
