import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID


@mock_aws
def test_create_and_describe_budget_minimal_params():
    client = boto3.client("budgets", region_name="us-east-1")
    resp = client.create_budget(
        AccountId=ACCOUNT_ID,
        Budget={
            "BudgetLimit": {"Amount": "10", "Unit": "USD"},
            "BudgetName": "testbudget",
            "TimeUnit": "DAILY",
            "BudgetType": "COST",
        },
    )
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    try:
        budget = client.describe_budget(AccountId=ACCOUNT_ID, BudgetName="testbudget")[
            "Budget"
        ]
    except OverflowError:
        pytest.skip("This test requires 64-bit time_t")
    assert "BudgetLimit" in budget
    assert "Amount" in budget["BudgetLimit"]
    assert budget["BudgetLimit"]["Amount"] == "10"
    assert "Unit" in budget["BudgetLimit"]
    assert budget["BudgetLimit"]["Unit"] == "USD"
    assert budget["BudgetName"] == "testbudget"
    assert budget["TimeUnit"] == "DAILY"
    assert budget["BudgetType"] == "COST"
    assert "CalculatedSpend" in budget
    assert "ActualSpend" in budget["CalculatedSpend"]
    assert budget["CalculatedSpend"]["ActualSpend"] == {"Amount": "0", "Unit": "USD"}
    assert "ForecastedSpend" in budget["CalculatedSpend"]
    assert budget["CalculatedSpend"]["ForecastedSpend"] == {
        "Amount": "0",
        "Unit": "USD",
    }
    assert "CostTypes" in budget
    assert budget["CostTypes"]["IncludeCredit"] is True
    assert budget["CostTypes"]["IncludeDiscount"] is True
    assert budget["CostTypes"]["IncludeOtherSubscription"] is True
    assert budget["CostTypes"]["IncludeRecurring"] is True
    assert budget["CostTypes"]["IncludeRefund"] is True
    assert budget["CostTypes"]["IncludeSubscription"] is True
    assert budget["CostTypes"]["IncludeSupport"] is True
    assert budget["CostTypes"]["IncludeTax"] is True
    assert budget["CostTypes"]["IncludeUpfront"] is True
    assert budget["CostTypes"]["UseAmortized"] is False
    assert budget["CostTypes"]["UseBlended"] is False
    assert "LastUpdatedTime" in budget
    assert "TimePeriod" in budget
    assert "Start" in budget["TimePeriod"]
    assert budget["TimePeriod"]["Start"]
    assert "End" in budget["TimePeriod"]
    assert budget["TimePeriod"]["End"]
    assert budget["TimeUnit"] == "DAILY"


@mock_aws
def test_create_existing_budget():
    client = boto3.client("budgets", region_name="us-east-1")
    client.create_budget(
        AccountId=ACCOUNT_ID,
        Budget={
            "BudgetLimit": {"Amount": "10", "Unit": "USD"},
            "BudgetName": "testb",
            "TimeUnit": "DAILY",
            "BudgetType": "COST",
        },
    )

    with pytest.raises(ClientError) as exc:
        client.create_budget(
            AccountId=ACCOUNT_ID,
            Budget={
                "BudgetLimit": {"Amount": "10", "Unit": "USD"},
                "BudgetName": "testb",
                "TimeUnit": "DAILY",
                "BudgetType": "COST",
            },
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "DuplicateRecordException"
    assert err["Message"] == "Error creating budget: testb - the budget already exists."


@mock_aws
def test_create_budget_without_limit_param():
    client = boto3.client("budgets", region_name="us-east-1")
    with pytest.raises(ClientError) as exc:
        client.create_budget(
            AccountId=ACCOUNT_ID,
            Budget={"BudgetName": "testb", "TimeUnit": "DAILY", "BudgetType": "COST"},
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterException"
    assert (
        err["Message"]
        == "Unable to create/update budget - please provide one of the followings: Budget Limit/ Planned Budget Limit/ Auto Adjust Data"
    )


@mock_aws
def test_describe_unknown_budget():
    client = boto3.client("budgets", region_name="us-east-1")
    with pytest.raises(ClientError) as exc:
        client.describe_budget(AccountId=ACCOUNT_ID, BudgetName="unknown")
    err = exc.value.response["Error"]
    assert err["Code"] == "NotFoundException"
    assert err["Message"] == "Unable to get budget: unknown - the budget doesn't exist."


@mock_aws
def test_describe_no_budgets():
    client = boto3.client("budgets", region_name="us-east-1")
    resp = client.describe_budgets(AccountId=ACCOUNT_ID)
    assert resp["Budgets"] == []


@mock_aws
def test_create_and_describe_all_budgets():
    client = boto3.client("budgets", region_name="us-east-1")
    client.create_budget(
        AccountId=ACCOUNT_ID,
        Budget={
            "BudgetLimit": {"Amount": "10", "Unit": "USD"},
            "BudgetName": "testbudget",
            "TimeUnit": "DAILY",
            "BudgetType": "COST",
        },
    )

    try:
        res = client.describe_budgets(AccountId=ACCOUNT_ID)
    except OverflowError:
        pytest.skip("This test requires 64-bit time_t")
    assert len(res["Budgets"]) == 1


@mock_aws
def test_delete_budget():
    client = boto3.client("budgets", region_name="us-east-1")
    client.create_budget(
        AccountId=ACCOUNT_ID,
        Budget={
            "BudgetLimit": {"Amount": "10", "Unit": "USD"},
            "BudgetName": "b1",
            "TimeUnit": "DAILY",
            "BudgetType": "COST",
        },
    )

    resp = client.delete_budget(AccountId=ACCOUNT_ID, BudgetName="b1")
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    res = client.describe_budgets(AccountId=ACCOUNT_ID)
    assert len(res["Budgets"]) == 0


@mock_aws
def test_delete_unknown_budget():
    client = boto3.client("budgets", region_name="us-east-1")
    with pytest.raises(ClientError) as exc:
        client.delete_budget(AccountId=ACCOUNT_ID, BudgetName="unknown")
    err = exc.value.response["Error"]
    assert err["Code"] == "NotFoundException"
    assert (
        err["Message"]
        == "Unable to delete budget: unknown - the budget doesn't exist. Try creating it first. "
    )
