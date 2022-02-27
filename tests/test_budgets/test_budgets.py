import boto3
import pytest

from botocore.exceptions import ClientError
import sure  # noqa # pylint: disable=unused-import
from datetime import datetime
from moto import mock_budgets
from moto.core import ACCOUNT_ID


@mock_budgets
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
    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    budget = client.describe_budget(AccountId=ACCOUNT_ID, BudgetName="testbudget")[
        "Budget"
    ]
    budget.should.have.key("BudgetLimit")
    budget["BudgetLimit"].should.have.key("Amount")
    budget["BudgetLimit"]["Amount"].should.equal("10")
    budget["BudgetLimit"].should.have.key("Unit")
    budget["BudgetLimit"]["Unit"].should.equal("USD")
    budget.should.have.key("BudgetName").equals("testbudget")
    budget.should.have.key("TimeUnit").equals("DAILY")
    budget.should.have.key("BudgetType").equals("COST")
    budget.should.have.key("CalculatedSpend")
    budget["CalculatedSpend"].should.have.key("ActualSpend")
    budget["CalculatedSpend"]["ActualSpend"].should.equal(
        {"Amount": "0", "Unit": "USD"}
    )
    budget["CalculatedSpend"].should.have.key("ForecastedSpend")
    budget["CalculatedSpend"]["ForecastedSpend"].should.equal(
        {"Amount": "0", "Unit": "USD"}
    )
    budget.should.have.key("CostTypes")
    budget["CostTypes"].should.have.key("IncludeCredit").equals(True)
    budget["CostTypes"].should.have.key("IncludeDiscount").equals(True)
    budget["CostTypes"].should.have.key("IncludeOtherSubscription").equals(True)
    budget["CostTypes"].should.have.key("IncludeRecurring").equals(True)
    budget["CostTypes"].should.have.key("IncludeRefund").equals(True)
    budget["CostTypes"].should.have.key("IncludeSubscription").equals(True)
    budget["CostTypes"].should.have.key("IncludeSupport").equals(True)
    budget["CostTypes"].should.have.key("IncludeTax").equals(True)
    budget["CostTypes"].should.have.key("IncludeUpfront").equals(True)
    budget["CostTypes"].should.have.key("UseAmortized").equals(False)
    budget["CostTypes"].should.have.key("UseBlended").equals(False)
    budget.should.have.key("LastUpdatedTime").should.be.a(datetime)
    budget.should.have.key("TimePeriod")
    budget["TimePeriod"].should.have.key("Start")
    budget["TimePeriod"]["Start"].should.be.a(datetime)
    budget["TimePeriod"].should.have.key("End")
    budget["TimePeriod"]["End"].should.be.a(datetime)
    budget.should.have.key("TimeUnit").equals("DAILY")


@mock_budgets
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
    err["Code"].should.equal("DuplicateRecordException")
    err["Message"].should.equal(
        "Error creating budget: testb - the budget already exists."
    )


@mock_budgets
def test_create_budget_without_limit_param():
    client = boto3.client("budgets", region_name="us-east-1")
    with pytest.raises(ClientError) as exc:
        client.create_budget(
            AccountId=ACCOUNT_ID,
            Budget={"BudgetName": "testb", "TimeUnit": "DAILY", "BudgetType": "COST"},
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("InvalidParameterException")
    err["Message"].should.equal(
        "Unable to create/update budget - please provide one of the followings: Budget Limit/ Planned Budget Limit/ Auto Adjust Data"
    )


@mock_budgets
def test_describe_unknown_budget():
    client = boto3.client("budgets", region_name="us-east-1")
    with pytest.raises(ClientError) as exc:
        client.describe_budget(AccountId=ACCOUNT_ID, BudgetName="unknown")
    err = exc.value.response["Error"]
    err["Code"].should.equal("NotFoundException")
    err["Message"].should.equal(
        "Unable to get budget: unknown - the budget doesn't exist."
    )


@mock_budgets
def test_describe_no_budgets():
    client = boto3.client("budgets", region_name="us-east-1")
    resp = client.describe_budgets(AccountId=ACCOUNT_ID)
    resp.should.have.key("Budgets").equals([])


@mock_budgets
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

    res = client.describe_budgets(AccountId=ACCOUNT_ID)
    res["Budgets"].should.have.length_of(1)


@mock_budgets
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
    resp["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)

    res = client.describe_budgets(AccountId=ACCOUNT_ID)
    res["Budgets"].should.have.length_of(0)


@mock_budgets
def test_delete_unknown_budget():
    client = boto3.client("budgets", region_name="us-east-1")
    with pytest.raises(ClientError) as exc:
        client.delete_budget(AccountId=ACCOUNT_ID, BudgetName="unknown")
    err = exc.value.response["Error"]
    err["Code"].should.equal("NotFoundException")
    err["Message"].should.equal(
        "Unable to delete budget: unknown - the budget doesn't exist. Try creating it first. "
    )
