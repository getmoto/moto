import datetime
import re

from moto.core import DEFAULT_ACCOUNT_ID
from moto.organizations import utils


def test_make_random_org_id():
    org_id = utils.make_random_org_id()
    assert re.match(utils.ORG_ID_REGEX, org_id)


def test_make_random_root_id():
    root_id = utils.make_random_root_id()
    assert re.match(utils.ROOT_ID_REGEX, root_id)


def test_make_random_ou_id():
    root_id = utils.make_random_root_id()
    ou_id = utils.make_random_ou_id(root_id)
    assert re.match(utils.OU_ID_REGEX, ou_id)


def test_make_random_account_id():
    account_id = utils.make_random_account_id()
    assert re.match(utils.ACCOUNT_ID_REGEX, account_id)


def test_make_random_create_account_status_id():
    create_account_status_id = utils.make_random_create_account_status_id()
    assert re.match(utils.CREATE_ACCOUNT_STATUS_ID_REGEX, create_account_status_id)


def test_make_random_policy_id():
    policy_id = utils.make_random_policy_id()
    assert re.match(utils.POLICY_ID_REGEX, policy_id)


def validate_organization(response):
    org = response["Organization"]
    assert sorted(org.keys()) == [
        "Arn",
        "AvailablePolicyTypes",
        "FeatureSet",
        "Id",
        "MasterAccountArn",
        "MasterAccountEmail",
        "MasterAccountId",
    ]
    assert re.match(utils.ORG_ID_REGEX, org["Id"])
    assert org["MasterAccountId"] == DEFAULT_ACCOUNT_ID
    assert org["MasterAccountArn"] == (
        utils.MASTER_ACCOUNT_ARN_FORMAT.format(org["MasterAccountId"], org["Id"])
    )
    assert org["Arn"] == (
        utils.ORGANIZATION_ARN_FORMAT.format(org["MasterAccountId"], org["Id"])
    )
    assert org["MasterAccountEmail"] == utils.MASTER_ACCOUNT_EMAIL
    assert org["FeatureSet"] in ["ALL", "CONSOLIDATED_BILLING"]
    assert org["AvailablePolicyTypes"] == [
        {"Type": "SERVICE_CONTROL_POLICY", "Status": "ENABLED"}
    ]


def validate_roots(org, response):
    assert isinstance(response["Roots"], list)
    assert response["Roots"] != []
    root = response["Roots"][0]
    assert re.match(utils.ROOT_ID_REGEX, root["Id"])
    assert root["Arn"] == (
        utils.ROOT_ARN_FORMAT.format(org["MasterAccountId"], org["Id"], root["Id"])
    )
    assert isinstance(root["Name"], str)
    assert root["PolicyTypes"] == []


def validate_organizational_unit(org, response):
    assert isinstance(response["OrganizationalUnit"], dict)
    ou = response["OrganizationalUnit"]
    assert re.match(utils.OU_ID_REGEX, ou["Id"])
    assert ou["Arn"] == (
        utils.OU_ARN_FORMAT.format(org["MasterAccountId"], org["Id"], ou["Id"])
    )
    assert isinstance(ou["Name"], str)


def validate_account(org, account):
    assert sorted(account.keys()) == [
        "Arn",
        "Email",
        "Id",
        "JoinedMethod",
        "JoinedTimestamp",
        "Name",
        "Status",
    ]
    assert re.match(utils.ACCOUNT_ID_REGEX, account["Id"])
    assert account["Arn"] == (
        utils.ACCOUNT_ARN_FORMAT.format(
            org["MasterAccountId"], org["Id"], account["Id"]
        )
    )
    assert re.match(utils.EMAIL_REGEX, account["Email"])
    assert account["JoinedMethod"] in ["INVITED", "CREATED"]
    assert account["Status"] in ["ACTIVE", "SUSPENDED"]
    assert isinstance(account["Name"], str)
    assert isinstance(account["JoinedTimestamp"], datetime.datetime)


def validate_create_account_status(create_status):
    assert sorted(create_status.keys()) == [
        "AccountId",
        "AccountName",
        "CompletedTimestamp",
        "Id",
        "RequestedTimestamp",
        "State",
    ]
    assert re.match(utils.CREATE_ACCOUNT_STATUS_ID_REGEX, create_status["Id"])
    assert re.match(utils.ACCOUNT_ID_REGEX, create_status["AccountId"])
    assert isinstance(create_status["AccountName"], str)
    assert create_status["State"] == "SUCCEEDED"
    assert isinstance(create_status["RequestedTimestamp"], datetime.datetime)
    assert isinstance(create_status["CompletedTimestamp"], datetime.datetime)


def validate_policy_summary(org, summary):
    assert isinstance(summary, dict)
    assert re.match(utils.POLICY_ID_REGEX, summary["Id"])
    assert summary["Arn"] == (
        utils.SCP_ARN_FORMAT.format(org["MasterAccountId"], org["Id"], summary["Id"])
    )
    assert isinstance(summary["Name"], str)
    assert isinstance(summary["Description"], str)
    assert summary["Type"] == "SERVICE_CONTROL_POLICY"
    assert isinstance(summary["AwsManaged"], bool)


def validate_service_control_policy(org, response):
    assert isinstance(response["PolicySummary"], dict)
    assert isinstance(response["Content"], str)
    validate_policy_summary(org, response["PolicySummary"])
