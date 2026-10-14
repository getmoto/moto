from datetime import datetime, timedelta, timezone

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID
from moto.glue.utils import count_dqdl_rules

RULESET = 'Rules = [ IsComplete "id", ColumnValues "status" in ["NEW", "DONE"], RowCount > 10 ]'


def ruleset_arn(name: str) -> str:
    return f"arn:aws:glue:us-east-1:{DEFAULT_ACCOUNT_ID}:dataQualityRuleset/{name}"


@mock_aws
def test_create_and_get_data_quality_ruleset():
    client = boto3.client("glue", region_name="us-east-1")

    resp = client.create_data_quality_ruleset(
        Name="orders-ruleset",
        Description="Checks for the orders table",
        Ruleset=RULESET,
        TargetTable={"TableName": "orders", "DatabaseName": "sales"},
        DataQualitySecurityConfiguration="dq-security-config",
    )
    assert resp["Name"] == "orders-ruleset"

    ruleset = client.get_data_quality_ruleset(Name="orders-ruleset")
    assert ruleset["Name"] == "orders-ruleset"
    assert ruleset["Description"] == "Checks for the orders table"
    assert ruleset["Ruleset"] == RULESET
    assert ruleset["TargetTable"] == {"TableName": "orders", "DatabaseName": "sales"}
    assert ruleset["DataQualitySecurityConfiguration"] == "dq-security-config"
    assert isinstance(ruleset["CreatedOn"], datetime)
    assert ruleset["LastModifiedOn"] == ruleset["CreatedOn"]


@mock_aws
def test_create_data_quality_ruleset_with_only_required_parameters():
    client = boto3.client("glue", region_name="us-east-1")

    client.create_data_quality_ruleset(Name="minimal", Ruleset=RULESET)

    ruleset = client.get_data_quality_ruleset(Name="minimal")
    assert ruleset["Name"] == "minimal"
    assert ruleset["Ruleset"] == RULESET
    assert "Description" not in ruleset
    assert "TargetTable" not in ruleset


@mock_aws
def test_create_data_quality_ruleset_that_already_exists():
    client = boto3.client("glue", region_name="us-east-1")
    client.create_data_quality_ruleset(Name="orders-ruleset", Ruleset=RULESET)

    with pytest.raises(ClientError) as exc:
        client.create_data_quality_ruleset(Name="orders-ruleset", Ruleset=RULESET)

    assert exc.value.response["Error"]["Code"] == "AlreadyExistsException"


@mock_aws
def test_get_data_quality_ruleset_that_does_not_exist():
    client = boto3.client("glue", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        client.get_data_quality_ruleset(Name="unknown")

    err = exc.value.response["Error"]
    assert err["Code"] == "EntityNotFoundException"
    assert "unknown" in err["Message"]


@mock_aws
def test_create_data_quality_ruleset_with_tags():
    client = boto3.client("glue", region_name="us-east-1")

    client.create_data_quality_ruleset(
        Name="orders-ruleset", Ruleset=RULESET, Tags={"team": "data", "env": "dev"}
    )

    tags = client.get_tags(ResourceArn=ruleset_arn("orders-ruleset"))["Tags"]
    assert tags == {"team": "data", "env": "dev"}


@mock_aws
def test_list_data_quality_rulesets():
    client = boto3.client("glue", region_name="us-east-1")
    client.create_data_quality_ruleset(
        Name="orders-ruleset",
        Description="Checks for the orders table",
        Ruleset=RULESET,
        TargetTable={"TableName": "orders", "DatabaseName": "sales"},
    )
    client.create_data_quality_ruleset(
        Name="customers-ruleset", Ruleset='Rules = [ IsUnique "email" ]'
    )

    rulesets = client.list_data_quality_rulesets()["Rulesets"]

    assert [r["Name"] for r in rulesets] == ["orders-ruleset", "customers-ruleset"]
    assert rulesets[0]["Description"] == "Checks for the orders table"
    assert rulesets[0]["TargetTable"] == {
        "TableName": "orders",
        "DatabaseName": "sales",
    }
    assert rulesets[0]["RuleCount"] == 3
    assert isinstance(rulesets[0]["CreatedOn"], datetime)
    assert isinstance(rulesets[0]["LastModifiedOn"], datetime)
    assert rulesets[1]["RuleCount"] == 1
    # The ruleset itself is only returned by GetDataQualityRuleset
    assert "Ruleset" not in rulesets[0]


@mock_aws
def test_list_data_quality_rulesets_when_none_exist():
    client = boto3.client("glue", region_name="us-east-1")

    resp = client.list_data_quality_rulesets()

    assert resp["Rulesets"] == []
    assert "NextToken" not in resp


@mock_aws
def test_list_data_quality_rulesets_pagination():
    client = boto3.client("glue", region_name="us-east-1")
    names = [f"ruleset-{i}" for i in range(5)]
    for name in names:
        client.create_data_quality_ruleset(Name=name, Ruleset=RULESET)

    first_page = client.list_data_quality_rulesets(MaxResults=2)
    assert [r["Name"] for r in first_page["Rulesets"]] == names[:2]

    second_page = client.list_data_quality_rulesets(
        MaxResults=2, NextToken=first_page["NextToken"]
    )
    assert [r["Name"] for r in second_page["Rulesets"]] == names[2:4]

    last_page = client.list_data_quality_rulesets(
        MaxResults=2, NextToken=second_page["NextToken"]
    )
    assert [r["Name"] for r in last_page["Rulesets"]] == names[4:]
    assert "NextToken" not in last_page


@mock_aws
def test_list_data_quality_rulesets_filtered_by_name_and_description():
    client = boto3.client("glue", region_name="us-east-1")
    client.create_data_quality_ruleset(
        Name="orders-ruleset", Description="orders", Ruleset=RULESET
    )
    client.create_data_quality_ruleset(
        Name="customers-ruleset", Description="customers", Ruleset=RULESET
    )

    by_name = client.list_data_quality_rulesets(Filter={"Name": "orders-ruleset"})
    assert [r["Name"] for r in by_name["Rulesets"]] == ["orders-ruleset"]

    by_description = client.list_data_quality_rulesets(
        Filter={"Description": "customers"}
    )
    assert [r["Name"] for r in by_description["Rulesets"]] == ["customers-ruleset"]


@mock_aws
def test_list_data_quality_rulesets_filtered_by_target_table():
    client = boto3.client("glue", region_name="us-east-1")
    client.create_data_quality_ruleset(
        Name="orders-ruleset",
        Ruleset=RULESET,
        TargetTable={"TableName": "orders", "DatabaseName": "sales"},
    )
    client.create_data_quality_ruleset(
        Name="customers-ruleset",
        Ruleset=RULESET,
        TargetTable={"TableName": "customers", "DatabaseName": "sales"},
    )
    client.create_data_quality_ruleset(Name="no-target-ruleset", Ruleset=RULESET)

    resp = client.list_data_quality_rulesets(
        Filter={"TargetTable": {"TableName": "orders", "DatabaseName": "sales"}}
    )

    assert [r["Name"] for r in resp["Rulesets"]] == ["orders-ruleset"]


@mock_aws
def test_list_data_quality_rulesets_filtered_by_dates():
    client = boto3.client("glue", region_name="us-east-1")
    client.create_data_quality_ruleset(Name="orders-ruleset", Ruleset=RULESET)
    an_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    in_an_hour = datetime.now(timezone.utc) + timedelta(hours=1)

    def names(**filter_criteria):
        resp = client.list_data_quality_rulesets(Filter=filter_criteria)
        return [r["Name"] for r in resp["Rulesets"]]

    assert names(CreatedAfter=an_hour_ago) == ["orders-ruleset"]
    assert names(CreatedAfter=in_an_hour) == []
    assert names(CreatedBefore=in_an_hour) == ["orders-ruleset"]
    assert names(CreatedBefore=an_hour_ago) == []
    assert names(LastModifiedAfter=an_hour_ago) == ["orders-ruleset"]
    assert names(LastModifiedAfter=in_an_hour) == []
    assert names(LastModifiedBefore=in_an_hour) == ["orders-ruleset"]
    assert names(LastModifiedBefore=an_hour_ago) == []


@mock_aws
def test_list_data_quality_rulesets_filtered_by_tags():
    client = boto3.client("glue", region_name="us-east-1")
    client.create_data_quality_ruleset(
        Name="orders-ruleset", Ruleset=RULESET, Tags={"team": "data", "env": "dev"}
    )
    client.create_data_quality_ruleset(
        Name="customers-ruleset", Ruleset=RULESET, Tags={"team": "crm"}
    )
    client.create_data_quality_ruleset(Name="untagged-ruleset", Ruleset=RULESET)

    resp = client.list_data_quality_rulesets(Tags={"team": "data"})
    assert [r["Name"] for r in resp["Rulesets"]] == ["orders-ruleset"]

    resp = client.list_data_quality_rulesets(Tags={"team": "data", "env": "prod"})
    assert resp["Rulesets"] == []


@mock_aws
def test_update_data_quality_ruleset():
    client = boto3.client("glue", region_name="us-east-1")
    client.create_data_quality_ruleset(
        Name="orders-ruleset", Description="old description", Ruleset=RULESET
    )
    created_on = client.get_data_quality_ruleset(Name="orders-ruleset")["CreatedOn"]
    new_ruleset = 'Rules = [ IsComplete "id" ]'

    resp = client.update_data_quality_ruleset(
        Name="orders-ruleset", Description="new description", Ruleset=new_ruleset
    )
    assert resp["Name"] == "orders-ruleset"
    assert resp["Description"] == "new description"
    assert resp["Ruleset"] == new_ruleset

    ruleset = client.get_data_quality_ruleset(Name="orders-ruleset")
    assert ruleset["Description"] == "new description"
    assert ruleset["Ruleset"] == new_ruleset
    assert ruleset["CreatedOn"] == created_on
    assert ruleset["LastModifiedOn"] >= created_on

    listed = client.list_data_quality_rulesets()["Rulesets"]
    assert listed[0]["RuleCount"] == 1


@mock_aws
def test_update_data_quality_ruleset_keeps_values_that_are_not_provided():
    client = boto3.client("glue", region_name="us-east-1")
    client.create_data_quality_ruleset(
        Name="orders-ruleset", Description="description", Ruleset=RULESET
    )

    client.update_data_quality_ruleset(Name="orders-ruleset", Description="updated")

    ruleset = client.get_data_quality_ruleset(Name="orders-ruleset")
    assert ruleset["Description"] == "updated"
    assert ruleset["Ruleset"] == RULESET


@mock_aws
def test_update_data_quality_ruleset_that_does_not_exist():
    client = boto3.client("glue", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        client.update_data_quality_ruleset(Name="unknown", Ruleset=RULESET)

    assert exc.value.response["Error"]["Code"] == "EntityNotFoundException"


@mock_aws
def test_delete_data_quality_ruleset():
    client = boto3.client("glue", region_name="us-east-1")
    client.create_data_quality_ruleset(
        Name="orders-ruleset", Ruleset=RULESET, Tags={"team": "data"}
    )
    client.create_data_quality_ruleset(Name="customers-ruleset", Ruleset=RULESET)

    client.delete_data_quality_ruleset(Name="orders-ruleset")

    rulesets = client.list_data_quality_rulesets()["Rulesets"]
    assert [r["Name"] for r in rulesets] == ["customers-ruleset"]
    with pytest.raises(ClientError) as exc:
        client.get_data_quality_ruleset(Name="orders-ruleset")
    assert exc.value.response["Error"]["Code"] == "EntityNotFoundException"

    # A new ruleset with the same name does not inherit the old tags
    client.create_data_quality_ruleset(Name="orders-ruleset", Ruleset=RULESET)
    assert client.get_tags(ResourceArn=ruleset_arn("orders-ruleset"))["Tags"] == {}


@mock_aws
def test_delete_data_quality_ruleset_that_does_not_exist():
    client = boto3.client("glue", region_name="us-east-1")

    with pytest.raises(ClientError) as exc:
        client.delete_data_quality_ruleset(Name="unknown")

    assert exc.value.response["Error"]["Code"] == "EntityNotFoundException"


@pytest.mark.parametrize(
    "ruleset,expected",
    [
        ('Rules = [ IsComplete "id" ]', 1),
        (RULESET, 3),
        ("Rules = [ ]", 0),
        ("Rules=[]", 0),
        # commas inside quotes, lists and parentheses don't separate rules
        ('Rules = [ ColumnValues "a,b" in ["x", "y"], RowCount between 1 and 10 ]', 2),
        ('Rules = [ (IsComplete "a") or (IsComplete "b"), IsUnique "c" ]', 2),
        # multi-line rulesets with a trailing comma
        ('Rules = [\n    IsComplete "id",\n    IsUnique "id",\n]', 2),
        # analyzers are not rules
        (
            'Rules = [ IsComplete "id" ]\nAnalyzers = [ Completeness "a", RowCount ]',
            1,
        ),
        ("Analyzers = [ RowCount ]", None),
    ],
)
def test_count_dqdl_rules(ruleset, expected):
    assert count_dqdl_rules(ruleset) == expected
