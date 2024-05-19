import json
import re
from datetime import datetime

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from moto.organizations import utils
from moto.organizations.exceptions import InvalidInputException, TargetNotFoundException
from moto.organizations.models import (
    FakeAccount,
    FakeOrganization,
    FakeOrganizationalUnit,
    FakePolicy,
    FakeRoot,
    OrganizationsBackend,
)

from .organizations_test_utils import (
    validate_account,
    validate_create_account_status,
    validate_organization,
    validate_organizational_unit,
    validate_policy_summary,
    validate_roots,
    validate_service_control_policy,
)


@mock_aws
@pytest.mark.parametrize(
    "region,partition",
    [("us-east-1", "aws"), ("cn-north-1", "aws-cn"), ("us-isob-east-1", "aws-iso-b")],
)
def test_create_organization(region, partition):
    client = boto3.client("organizations", region_name=region)
    response = client.create_organization(FeatureSet="ALL")
    validate_organization(response, partition=partition)
    organization = response["Organization"]
    assert organization["FeatureSet"] == "ALL"

    response = client.list_accounts()
    assert len(response["Accounts"]) == 1
    assert response["Accounts"][0]["Name"] == "master"
    assert response["Accounts"][0]["Id"] == ACCOUNT_ID
    assert response["Accounts"][0]["Email"] == utils.MASTER_ACCOUNT_EMAIL
    assert (
        response["Accounts"][0]["Arn"]
        == f"arn:{partition}:organizations::{ACCOUNT_ID}:account/{organization['Id']}/{ACCOUNT_ID}"
    )

    response = client.list_policies(Filter="SERVICE_CONTROL_POLICY")
    assert len(response["Policies"]) == 1
    assert response["Policies"][0]["Name"] == "FullAWSAccess"
    assert response["Policies"][0]["Id"] == utils.DEFAULT_POLICY_ID
    assert response["Policies"][0]["AwsManaged"] is True

    response = client.list_targets_for_policy(PolicyId=utils.DEFAULT_POLICY_ID)
    assert len(response["Targets"]) == 2
    root_ou = [t for t in response["Targets"] if t["Type"] == "ROOT"][0]
    assert root_ou["Name"] == "Root"
    master_account = [t for t in response["Targets"] if t["Type"] == "ACCOUNT"][0]
    assert master_account["Name"] == "master"


@mock_aws
def test_create_organization_without_feature_set():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization()
    response = client.describe_organization()
    validate_organization(response)
    assert response["Organization"]["FeatureSet"] == "ALL"


@mock_aws
def test_describe_organization():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")
    response = client.describe_organization()
    validate_organization(response)


@mock_aws
def test_describe_organization_exception():
    client = boto3.client("organizations", region_name="us-east-1")
    with pytest.raises(ClientError) as e:
        client.describe_organization()
    ex = e.value
    assert ex.operation_name == "DescribeOrganization"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "AWSOrganizationsNotInUseException" in ex.response["Error"]["Code"]
    assert ex.response["Error"]["Message"] == (
        "Your account is not a member of an organization."
    )


# Organizational Units


@mock_aws
def test_list_roots():
    client = boto3.client("organizations", region_name="us-east-1")
    org = client.create_organization(FeatureSet="ALL")["Organization"]
    response = client.list_roots()
    validate_roots(org, response)


@mock_aws
def test_create_organizational_unit():
    client = boto3.client("organizations", region_name="us-east-1")
    org = client.create_organization(FeatureSet="ALL")["Organization"]
    root_id = client.list_roots()["Roots"][0]["Id"]
    ou_name = "ou01"
    response = client.create_organizational_unit(ParentId=root_id, Name=ou_name)
    validate_organizational_unit(org, response)
    assert response["OrganizationalUnit"]["Name"] == ou_name


@mock_aws
def test_delete_organizational_unit():
    client = boto3.client("organizations", region_name="us-east-1")
    org = client.create_organization(FeatureSet="ALL")["Organization"]
    root_id = client.list_roots()["Roots"][0]["Id"]
    ou_name = "ou01"
    response = client.create_organizational_unit(ParentId=root_id, Name=ou_name)
    validate_organizational_unit(org, response)

    # delete organizational unit
    ou_id = response["OrganizationalUnit"]["Id"]
    response = client.delete_organizational_unit(OrganizationalUnitId=ou_id)
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    # verify the deletion
    with pytest.raises(ClientError) as e:
        client.describe_organizational_unit(OrganizationalUnitId=ou_id)
    ex = e.value
    assert ex.operation_name == "DescribeOrganizationalUnit"
    assert ex.response["Error"]["Code"] == "400"
    assert "OrganizationalUnitNotFoundException" in ex.response["Error"]["Message"]


@mock_aws
def test_describe_organizational_unit():
    client = boto3.client("organizations", region_name="us-east-1")
    org = client.create_organization(FeatureSet="ALL")["Organization"]
    root_id = client.list_roots()["Roots"][0]["Id"]
    ou_id = client.create_organizational_unit(ParentId=root_id, Name="ou01")[
        "OrganizationalUnit"
    ]["Id"]
    response = client.describe_organizational_unit(OrganizationalUnitId=ou_id)
    validate_organizational_unit(org, response)


@mock_aws
def test_describe_organizational_unit_exception():
    client = boto3.client("organizations", region_name="us-east-1")
    _ = client.create_organization(FeatureSet="ALL")["Organization"]
    with pytest.raises(ClientError) as e:
        client.describe_organizational_unit(
            OrganizationalUnitId=utils.make_random_root_id()
        )
    ex = e.value
    assert ex.operation_name == "DescribeOrganizationalUnit"
    assert ex.response["Error"]["Code"] == "400"
    assert "OrganizationalUnitNotFoundException" in ex.response["Error"]["Message"]


@mock_aws
def test_list_organizational_units_for_parent():
    client = boto3.client("organizations", region_name="us-east-1")
    org = client.create_organization(FeatureSet="ALL")["Organization"]
    root_id = client.list_roots()["Roots"][0]["Id"]
    client.create_organizational_unit(ParentId=root_id, Name="ou01")
    client.create_organizational_unit(ParentId=root_id, Name="ou02")
    client.create_organizational_unit(ParentId=root_id, Name="ou03")
    response = client.list_organizational_units_for_parent(ParentId=root_id)
    assert isinstance(response["OrganizationalUnits"], list)
    for ou in response["OrganizationalUnits"]:
        validate_organizational_unit(org, {"OrganizationalUnit": ou})


@mock_aws
def test_list_organizational_units_pagination():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")
    root_id = client.list_roots()["Roots"][0]["Id"]
    for i in range(20):
        name = "ou" + str(i)
        client.create_organizational_unit(ParentId=root_id, Name=name)
    response = client.list_organizational_units_for_parent(ParentId=root_id)
    assert "NextToken" not in response
    assert len(response["OrganizationalUnits"]) >= i

    paginator = client.get_paginator("list_organizational_units_for_parent")
    page_iterator = paginator.paginate(MaxResults=5, ParentId=root_id)
    page_list = list(page_iterator)
    for page in page_list:
        assert len(page["OrganizationalUnits"]) <= 5
    assert "19" in page_list[-1]["OrganizationalUnits"][-1]["Name"]


@mock_aws
def test_list_organizational_units_for_parent_exception():
    client = boto3.client("organizations", region_name="us-east-1")
    with pytest.raises(ClientError) as e:
        client.list_organizational_units_for_parent(
            ParentId=utils.make_random_root_id()
        )
    ex = e.value
    assert ex.operation_name == "ListOrganizationalUnitsForParent"
    assert ex.response["Error"]["Code"] == "400"
    assert "ParentNotFoundException" in ex.response["Error"]["Message"]


# Accounts
mockname = "mock-account"
mockdomain = "moto-example.org"
mockemail = "@".join([mockname, mockdomain])


@mock_aws
def test_create_account():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")
    create_status = client.create_account(AccountName=mockname, Email=mockemail)[
        "CreateAccountStatus"
    ]
    validate_create_account_status(create_status)
    assert create_status["AccountName"] == mockname


@mock_aws
def test_close_account_returns_nothing():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")
    create_status = client.create_account(AccountName=mockname, Email=mockemail)[
        "CreateAccountStatus"
    ]
    created_account_id = create_status["AccountId"]

    resp = client.close_account(AccountId=created_account_id)

    del resp["ResponseMetadata"]

    assert resp == {}


@mock_aws
def test_close_account_puts_account_in_suspended_status():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")
    create_status = client.create_account(AccountName=mockname, Email=mockemail)[
        "CreateAccountStatus"
    ]
    created_account_id = create_status["AccountId"]

    client.close_account(AccountId=created_account_id)

    account = client.describe_account(AccountId=created_account_id)["Account"]
    assert account["Status"] == "SUSPENDED"


@mock_aws
def test_close_account_id_not_in_org_raises_exception():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")
    uncreated_fake_account_id = "123456789101"

    with pytest.raises(ClientError) as e:
        client.close_account(AccountId=uncreated_fake_account_id)
    ex = e.value
    assert ex.operation_name == "CloseAccount"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "AccountNotFoundException" in ex.response["Error"]["Code"]
    assert ex.response["Error"]["Message"] == (
        "You specified an account that doesn't exist."
    )


@mock_aws
def test_describe_create_account_status():
    client = boto3.client("organizations", region_name="us-east-1")
    _ = client.create_organization(FeatureSet="ALL")["Organization"]
    request_id = client.create_account(AccountName=mockname, Email=mockemail)[
        "CreateAccountStatus"
    ]["Id"]
    response = client.describe_create_account_status(CreateAccountRequestId=request_id)
    validate_create_account_status(response["CreateAccountStatus"])


@mock_aws
def test_describe_account():
    client = boto3.client("organizations", region_name="us-east-1")
    org = client.create_organization(FeatureSet="ALL")["Organization"]
    account_id = client.create_account(AccountName=mockname, Email=mockemail)[
        "CreateAccountStatus"
    ]["AccountId"]
    response = client.describe_account(AccountId=account_id)
    validate_account(org, response["Account"])
    assert response["Account"]["Name"] == mockname
    assert response["Account"]["Email"] == mockemail


@mock_aws
def test_describe_account_exception():
    client = boto3.client("organizations", region_name="us-east-1")
    with pytest.raises(ClientError) as e:
        client.describe_account(AccountId=utils.make_random_account_id())
    ex = e.value
    assert ex.operation_name == "DescribeAccount"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "AccountNotFoundException" in ex.response["Error"]["Code"]
    assert ex.response["Error"]["Message"] == (
        "You specified an account that doesn't exist."
    )


@mock_aws
def test_list_accounts():
    client = boto3.client("organizations", region_name="us-east-1")
    org = client.create_organization(FeatureSet="ALL")["Organization"]
    for i in range(5):
        name = mockname + str(i)
        email = name + "@" + mockdomain
        client.create_account(AccountName=name, Email=email)
    response = client.list_accounts()
    assert "Accounts" in response
    accounts = response["Accounts"]
    assert len(accounts) == 6
    for account in accounts:
        validate_account(org, account)
    assert accounts[4]["Name"] == mockname + "3"
    assert accounts[3]["Email"] == mockname + "2" + "@" + mockdomain


@mock_aws
def test_list_accounts_pagination():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")
    for i in range(25):
        name = mockname + str(i)
        email = name + "@" + mockdomain
        client.create_account(AccountName=name, Email=email)
    response = client.list_accounts()
    assert "NextToken" not in response
    assert len(response["Accounts"]) >= i

    paginator = client.get_paginator("list_accounts")
    page_iterator = paginator.paginate(MaxResults=5)
    page_list = list(page_iterator)
    for page in page_list:
        assert len(page["Accounts"]) <= 5
    assert "24" in page_list[-1]["Accounts"][-1]["Name"]


@mock_aws
def test_list_accounts_for_parent():
    client = boto3.client("organizations", region_name="us-east-1")
    _ = client.create_organization(FeatureSet="ALL")["Organization"]
    root_id = client.list_roots()["Roots"][0]["Id"]
    account_id = client.create_account(AccountName=mockname, Email=mockemail)[
        "CreateAccountStatus"
    ]["AccountId"]
    response = client.list_accounts_for_parent(ParentId=root_id)
    assert account_id in [account["Id"] for account in response["Accounts"]]


@mock_aws
def test_list_accounts_for_parent_pagination():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")
    root_id = client.list_roots()["Roots"][0]["Id"]
    response = client.list_accounts_for_parent(ParentId=root_id)
    assert "NextToken" not in response
    num_existing_accounts = len(response["Accounts"])
    for i in range(num_existing_accounts, 21):
        name = mockname + str(i)
        email = name + "@" + mockdomain
        client.create_account(AccountName=name, Email=email)
    response = client.list_accounts_for_parent(ParentId=root_id)
    assert len(response["Accounts"]) >= i

    paginator = client.get_paginator("list_accounts_for_parent")
    page_iterator = paginator.paginate(MaxResults=5, ParentId=root_id)
    page_list = list(page_iterator)
    for page in page_list:
        assert len(page["Accounts"]) <= 5
    assert "20" in page_list[-1]["Accounts"][-1]["Name"]


@mock_aws
def test_move_account():
    client = boto3.client("organizations", region_name="us-east-1")
    _ = client.create_organization(FeatureSet="ALL")["Organization"]
    root_id = client.list_roots()["Roots"][0]["Id"]
    account_id = client.create_account(AccountName=mockname, Email=mockemail)[
        "CreateAccountStatus"
    ]["AccountId"]
    ou01 = client.create_organizational_unit(ParentId=root_id, Name="ou01")
    ou01_id = ou01["OrganizationalUnit"]["Id"]
    client.move_account(
        AccountId=account_id, SourceParentId=root_id, DestinationParentId=ou01_id
    )
    response = client.list_accounts_for_parent(ParentId=ou01_id)
    assert account_id in [account["Id"] for account in response["Accounts"]]


@mock_aws
def test_list_parents_for_ou():
    client = boto3.client("organizations", region_name="us-east-1")
    _ = client.create_organization(FeatureSet="ALL")["Organization"]
    root_id = client.list_roots()["Roots"][0]["Id"]
    ou01 = client.create_organizational_unit(ParentId=root_id, Name="ou01")
    ou01_id = ou01["OrganizationalUnit"]["Id"]
    response01 = client.list_parents(ChildId=ou01_id)
    assert isinstance(response01["Parents"], list)
    assert response01["Parents"][0]["Id"] == root_id
    assert response01["Parents"][0]["Type"] == "ROOT"
    ou02 = client.create_organizational_unit(ParentId=ou01_id, Name="ou02")
    ou02_id = ou02["OrganizationalUnit"]["Id"]
    response02 = client.list_parents(ChildId=ou02_id)
    assert isinstance(response02["Parents"], list)
    assert response02["Parents"][0]["Id"] == ou01_id
    assert response02["Parents"][0]["Type"] == "ORGANIZATIONAL_UNIT"


@mock_aws
def test_list_parents_for_accounts():
    client = boto3.client("organizations", region_name="us-east-1")
    _ = client.create_organization(FeatureSet="ALL")["Organization"]
    root_id = client.list_roots()["Roots"][0]["Id"]
    ou01 = client.create_organizational_unit(ParentId=root_id, Name="ou01")
    ou01_id = ou01["OrganizationalUnit"]["Id"]
    account01_id = client.create_account(
        AccountName="account01", Email="account01@moto-example.org"
    )["CreateAccountStatus"]["AccountId"]
    account02_id = client.create_account(
        AccountName="account02", Email="account02@moto-example.org"
    )["CreateAccountStatus"]["AccountId"]
    client.move_account(
        AccountId=account02_id, SourceParentId=root_id, DestinationParentId=ou01_id
    )
    response01 = client.list_parents(ChildId=account01_id)
    assert isinstance(response01["Parents"], list)
    assert response01["Parents"][0]["Id"] == root_id
    assert response01["Parents"][0]["Type"] == "ROOT"
    response02 = client.list_parents(ChildId=account02_id)
    assert isinstance(response02["Parents"], list)
    assert response02["Parents"][0]["Id"] == ou01_id
    assert response02["Parents"][0]["Type"] == "ORGANIZATIONAL_UNIT"


@mock_aws
def test_list_children():
    client = boto3.client("organizations", region_name="us-east-1")
    _ = client.create_organization(FeatureSet="ALL")["Organization"]
    root_id = client.list_roots()["Roots"][0]["Id"]
    ou01 = client.create_organizational_unit(ParentId=root_id, Name="ou01")
    ou01_id = ou01["OrganizationalUnit"]["Id"]
    ou02 = client.create_organizational_unit(ParentId=ou01_id, Name="ou02")
    ou02_id = ou02["OrganizationalUnit"]["Id"]
    account01_id = client.create_account(
        AccountName="account01", Email="account01@moto-example.org"
    )["CreateAccountStatus"]["AccountId"]
    account02_id = client.create_account(
        AccountName="account02", Email="account02@moto-example.org"
    )["CreateAccountStatus"]["AccountId"]
    client.move_account(
        AccountId=account02_id, SourceParentId=root_id, DestinationParentId=ou01_id
    )
    response01 = client.list_children(ParentId=root_id, ChildType="ACCOUNT")
    response02 = client.list_children(ParentId=root_id, ChildType="ORGANIZATIONAL_UNIT")
    response03 = client.list_children(ParentId=ou01_id, ChildType="ACCOUNT")
    response04 = client.list_children(ParentId=ou01_id, ChildType="ORGANIZATIONAL_UNIT")
    assert response01["Children"][0]["Id"] == ACCOUNT_ID
    assert response01["Children"][0]["Type"] == "ACCOUNT"
    assert response01["Children"][1]["Id"] == account01_id
    assert response01["Children"][1]["Type"] == "ACCOUNT"
    assert response02["Children"][0]["Id"] == ou01_id
    assert response02["Children"][0]["Type"] == "ORGANIZATIONAL_UNIT"
    assert response03["Children"][0]["Id"] == account02_id
    assert response03["Children"][0]["Type"] == "ACCOUNT"
    assert response04["Children"][0]["Id"] == ou02_id
    assert response04["Children"][0]["Type"] == "ORGANIZATIONAL_UNIT"


@mock_aws
def test_list_children_exception():
    client = boto3.client("organizations", region_name="us-east-1")
    _ = client.create_organization(FeatureSet="ALL")["Organization"]
    root_id = client.list_roots()["Roots"][0]["Id"]
    with pytest.raises(ClientError) as e:
        client.list_children(ParentId=utils.make_random_root_id(), ChildType="ACCOUNT")
    ex = e.value
    assert ex.operation_name == "ListChildren"
    assert ex.response["Error"]["Code"] == "400"
    assert "ParentNotFoundException" in ex.response["Error"]["Message"]
    with pytest.raises(ClientError) as e:
        client.list_children(ParentId=root_id, ChildType="BLEE")
    ex = e.value
    assert ex.operation_name == "ListChildren"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "InvalidInputException" in ex.response["Error"]["Code"]
    assert ex.response["Error"]["Message"] == "You specified an invalid value."


@mock_aws
def test_list_create_account_status():
    client = boto3.client("organizations", region_name="us-east-1")
    _ = client.create_organization(FeatureSet="ALL")["Organization"]
    response = client.list_create_account_status()
    createAccountStatuses = response["CreateAccountStatuses"]
    assert len(createAccountStatuses) == 1
    validate_create_account_status(createAccountStatuses[0])

    _ = client.create_account(AccountName=mockname, Email=mockemail)[
        "CreateAccountStatus"
    ]["Id"]
    response = client.list_create_account_status()
    createAccountStatuses = response["CreateAccountStatuses"]
    assert len(createAccountStatuses) == 2
    for createAccountStatus in createAccountStatuses:
        validate_create_account_status(createAccountStatus)


@mock_aws
def test_list_create_account_status_succeeded():
    client = boto3.client("organizations", region_name="us-east-1")
    _ = client.create_organization(FeatureSet="ALL")["Organization"]
    requiredStates = ["SUCCEEDED"]
    response = client.list_create_account_status(States=requiredStates)
    createAccountStatuses = response["CreateAccountStatuses"]
    assert len(createAccountStatuses) == 1
    validate_create_account_status(createAccountStatuses[0])


@mock_aws
def test_list_create_account_status_in_progress():
    client = boto3.client("organizations", region_name="us-east-1")
    _ = client.create_organization(FeatureSet="ALL")["Organization"]
    requiredStates = ["IN_PROGRESS"]
    response = client.list_create_account_status(States=requiredStates)
    createAccountStatuses = response["CreateAccountStatuses"]
    assert len(createAccountStatuses) == 0


@mock_aws
def test_get_paginated_list_create_account_status():
    client = boto3.client("organizations", region_name="us-east-1")
    _ = client.create_organization(FeatureSet="ALL")["Organization"]
    for _ in range(5):
        _ = client.create_account(AccountName=mockname, Email=mockemail)[
            "CreateAccountStatus"
        ]["Id"]
    response = client.list_create_account_status(MaxResults=2)
    createAccountStatuses = response["CreateAccountStatuses"]
    assert len(createAccountStatuses) == 2
    for createAccountStatus in createAccountStatuses:
        validate_create_account_status(createAccountStatus)
    next_token = response["NextToken"]
    assert next_token is not None
    response2 = client.list_create_account_status(NextToken=next_token)
    createAccountStatuses.extend(response2["CreateAccountStatuses"])
    assert len(createAccountStatuses) == 6
    assert "NextToken" not in response2.keys()
    for createAccountStatus in createAccountStatuses:
        validate_create_account_status(createAccountStatus)


@mock_aws
def test_remove_account_from_organization():
    client = boto3.client("organizations", region_name="us-east-1")
    _ = client.create_organization(FeatureSet="ALL")["Organization"]
    create_account_status = client.create_account(
        AccountName=mockname, Email=mockemail
    )["CreateAccountStatus"]
    account_id = create_account_status["AccountId"]

    def created_account_exists(accounts):
        return any(
            account
            for account in accounts
            if account["Name"] == mockname and account["Email"] == mockemail
        )

    accounts = client.list_accounts()["Accounts"]
    assert len(accounts) == 2
    assert created_account_exists(accounts)
    client.remove_account_from_organization(AccountId=account_id)
    accounts = client.list_accounts()["Accounts"]
    assert len(accounts) == 1
    assert not created_account_exists(accounts)


@mock_aws
def test_delete_organization_with_existing_account():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")
    create_account_status = client.create_account(
        Email=mockemail, AccountName=mockname
    )["CreateAccountStatus"]
    account_id = create_account_status["AccountId"]
    with pytest.raises(ClientError) as e:
        client.delete_organization()
    e.match("OrganizationNotEmptyException")
    client.remove_account_from_organization(AccountId=account_id)
    client.delete_organization()
    with pytest.raises(ClientError) as e:
        client.describe_organization()
    e.match("AWSOrganizationsNotInUseException")


# Service Control Policies
policy_doc01 = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "MockPolicyStatement",
            "Effect": "Allow",
            "Action": "s3:*",
            "Resource": "*",
        }
    ],
}


@mock_aws
def test_create_policy():
    client = boto3.client("organizations", region_name="us-east-1")
    org = client.create_organization(FeatureSet="ALL")["Organization"]
    policy = client.create_policy(
        Content=json.dumps(policy_doc01),
        Description="A dummy service control policy",
        Name="MockServiceControlPolicy",
        Type="SERVICE_CONTROL_POLICY",
    )["Policy"]
    validate_service_control_policy(org, policy)
    assert policy["PolicySummary"]["Name"] == "MockServiceControlPolicy"
    assert policy["PolicySummary"]["Description"] == "A dummy service control policy"
    assert policy["Content"] == json.dumps(policy_doc01)


@mock_aws
def test_create_policy_errors():
    # given
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")

    # invalid policy type
    # when
    with pytest.raises(ClientError) as e:
        client.create_policy(
            Content=json.dumps(policy_doc01),
            Description="moto",
            Name="moto",
            Type="MOTO",
        )

    # then
    ex = e.value
    assert ex.operation_name == "CreatePolicy"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "InvalidInputException" in ex.response["Error"]["Code"]
    assert ex.response["Error"]["Message"] == "You specified an invalid value."


@mock_aws
def test_describe_policy():
    client = boto3.client("organizations", region_name="us-east-1")
    org = client.create_organization(FeatureSet="ALL")["Organization"]
    policy_id = client.create_policy(
        Content=json.dumps(policy_doc01),
        Description="A dummy service control policy",
        Name="MockServiceControlPolicy",
        Type="SERVICE_CONTROL_POLICY",
    )["Policy"]["PolicySummary"]["Id"]
    policy = client.describe_policy(PolicyId=policy_id)["Policy"]
    validate_service_control_policy(org, policy)
    assert policy["PolicySummary"]["Name"] == "MockServiceControlPolicy"
    assert policy["PolicySummary"]["Description"] == "A dummy service control policy"
    assert policy["Content"] == json.dumps(policy_doc01)


@mock_aws
def test_describe_policy_exception():
    client = boto3.client("organizations", region_name="us-east-1")
    _ = client.create_organization(FeatureSet="ALL")["Organization"]
    policy_id = "p-47fhe9s3"
    with pytest.raises(ClientError) as e:
        client.describe_policy(PolicyId=policy_id)
    ex = e.value
    assert ex.operation_name == "DescribePolicy"
    assert ex.response["Error"]["Code"] == "PolicyNotFoundException"
    assert (
        ex.response["Error"]["Message"] == "You specified a policy that doesn't exist."
    )
    with pytest.raises(ClientError) as e:
        client.describe_policy(PolicyId="meaninglessstring")
    ex = e.value
    assert ex.operation_name == "DescribePolicy"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "InvalidInputException" in ex.response["Error"]["Code"]
    assert ex.response["Error"]["Message"] == "You specified an invalid value."


@mock_aws
def test_attach_policy():
    client = boto3.client("organizations", region_name="us-east-1")
    _ = client.create_organization(FeatureSet="ALL")["Organization"]
    root_id = client.list_roots()["Roots"][0]["Id"]
    ou_id = client.create_organizational_unit(ParentId=root_id, Name="ou01")[
        "OrganizationalUnit"
    ]["Id"]
    account_id = client.create_account(AccountName=mockname, Email=mockemail)[
        "CreateAccountStatus"
    ]["AccountId"]
    policy_id = client.create_policy(
        Content=json.dumps(policy_doc01),
        Description="A dummy service control policy",
        Name="MockServiceControlPolicy",
        Type="SERVICE_CONTROL_POLICY",
    )["Policy"]["PolicySummary"]["Id"]
    response = client.attach_policy(PolicyId=policy_id, TargetId=root_id)
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    response = client.attach_policy(PolicyId=policy_id, TargetId=ou_id)
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    response = client.attach_policy(PolicyId=policy_id, TargetId=account_id)
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200


@mock_aws
def test_detach_policy():
    client = boto3.client("organizations", region_name="us-east-1")
    _ = client.create_organization(FeatureSet="ALL")["Organization"]
    root_id = client.list_roots()["Roots"][0]["Id"]
    ou_id = client.create_organizational_unit(ParentId=root_id, Name="ou01")[
        "OrganizationalUnit"
    ]["Id"]
    account_id = client.create_account(AccountName=mockname, Email=mockemail)[
        "CreateAccountStatus"
    ]["AccountId"]
    policy_id = client.create_policy(
        Content=json.dumps(policy_doc01),
        Description="A dummy service control policy",
        Name="MockServiceControlPolicy",
        Type="SERVICE_CONTROL_POLICY",
    )["Policy"]["PolicySummary"]["Id"]
    # Attach/List/Detach policy
    for name, target in [("OU", ou_id), ("Root", root_id), ("Account", account_id)]:
        #
        assert (
            len(get_nonaws_policies(target, client)) == 0
        ), "We should start with 0 policies"

        #
        client.attach_policy(PolicyId=policy_id, TargetId=target)
        assert (
            len(get_nonaws_policies(target, client)) == 1
        ), f"Expecting 1 policy after creation of target={name}"

        #
        response = client.detach_policy(PolicyId=policy_id, TargetId=target)
        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
        assert (
            len(get_nonaws_policies(target, client)) == 0
        ), f"Expecting 0 policies after deletion of target={name}"


def get_nonaws_policies(account_id, client):
    return [
        p
        for p in client.list_policies_for_target(
            TargetId=account_id, Filter="SERVICE_CONTROL_POLICY"
        )["Policies"]
        if not p["AwsManaged"]
    ]


@mock_aws
def test_detach_policy_root_ou_not_found_exception():
    client = boto3.client("organizations", region_name="us-east-1")
    _ = client.create_organization(FeatureSet="ALL")["Organization"]
    root_id = client.list_roots()["Roots"][0]["Id"]
    _ = client.create_organizational_unit(ParentId=root_id, Name="ou01")[
        "OrganizationalUnit"
    ]["Id"]
    account_id = client.create_account(AccountName=mockname, Email=mockemail)[
        "CreateAccountStatus"
    ]["AccountId"]
    policy_id = client.create_policy(
        Content=json.dumps(policy_doc01),
        Description="A dummy service control policy",
        Name="MockServiceControlPolicy",
        Type="SERVICE_CONTROL_POLICY",
    )["Policy"]["PolicySummary"]["Id"]
    client.attach_policy(PolicyId=policy_id, TargetId=root_id)
    client.attach_policy(PolicyId=policy_id, TargetId=account_id)
    with pytest.raises(ClientError) as e:
        client.detach_policy(PolicyId=policy_id, TargetId="r-xy85")
    ex = e.value
    assert ex.operation_name == "DetachPolicy"
    assert ex.response["Error"]["Code"] == "400"
    assert "OrganizationalUnitNotFoundException" in ex.response["Error"]["Message"]


@mock_aws
def test_detach_policy_ou_not_found_exception():
    client = boto3.client("organizations", region_name="us-east-1")
    _ = client.create_organization(FeatureSet="ALL")["Organization"]
    root_id = client.list_roots()["Roots"][0]["Id"]
    ou_id = client.create_organizational_unit(ParentId=root_id, Name="ou01")[
        "OrganizationalUnit"
    ]["Id"]
    policy_id = client.create_policy(
        Content=json.dumps(policy_doc01),
        Description="A dummy service control policy",
        Name="MockServiceControlPolicy",
        Type="SERVICE_CONTROL_POLICY",
    )["Policy"]["PolicySummary"]["Id"]
    client.attach_policy(PolicyId=policy_id, TargetId=ou_id)
    with pytest.raises(ClientError) as e:
        client.detach_policy(PolicyId=policy_id, TargetId="ou-zx86-z3x4yr2t7")
    ex = e.value
    assert ex.operation_name == "DetachPolicy"
    assert ex.response["Error"]["Code"] == "400"
    assert "OrganizationalUnitNotFoundException" in ex.response["Error"]["Message"]


@mock_aws
def test_detach_policy_account_id_not_found_exception():
    client = boto3.client("organizations", region_name="us-east-1")
    _ = client.create_organization(FeatureSet="ALL")["Organization"]
    account_id = client.create_account(AccountName=mockname, Email=mockemail)[
        "CreateAccountStatus"
    ]["AccountId"]
    policy_id = client.create_policy(
        Content=json.dumps(policy_doc01),
        Description="A dummy service control policy",
        Name="MockServiceControlPolicy",
        Type="SERVICE_CONTROL_POLICY",
    )["Policy"]["PolicySummary"]["Id"]
    client.attach_policy(PolicyId=policy_id, TargetId=account_id)
    with pytest.raises(ClientError) as e:
        client.detach_policy(PolicyId=policy_id, TargetId="111619863336")
    ex = e.value
    assert ex.operation_name == "DetachPolicy"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "AccountNotFoundException" in ex.response["Error"]["Code"]
    assert ex.response["Error"]["Message"] == (
        "You specified an account that doesn't exist."
    )


@mock_aws
def test_detach_policy_invalid_target_exception():
    client = boto3.client("organizations", region_name="us-east-1")
    _ = client.create_organization(FeatureSet="ALL")["Organization"]
    root_id = client.list_roots()["Roots"][0]["Id"]
    ou_id = client.create_organizational_unit(ParentId=root_id, Name="ou01")[
        "OrganizationalUnit"
    ]["Id"]
    policy_id = client.create_policy(
        Content=json.dumps(policy_doc01),
        Description="A dummy service control policy",
        Name="MockServiceControlPolicy",
        Type="SERVICE_CONTROL_POLICY",
    )["Policy"]["PolicySummary"]["Id"]
    client.attach_policy(PolicyId=policy_id, TargetId=ou_id)
    with pytest.raises(ClientError) as e:
        client.detach_policy(PolicyId=policy_id, TargetId="invalidtargetid")
    ex = e.value
    assert ex.operation_name == "DetachPolicy"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "InvalidInputException" in ex.response["Error"]["Code"]
    assert ex.response["Error"]["Message"] == "You specified an invalid value."


@mock_aws
def test_delete_policy():
    client = boto3.client("organizations", region_name="us-east-1")
    _ = client.create_organization(FeatureSet="ALL")["Organization"]
    base_policies = client.list_policies(Filter="SERVICE_CONTROL_POLICY")["Policies"]
    assert len(base_policies) == 1
    policy_id = client.create_policy(
        Content=json.dumps(policy_doc01),
        Description="A dummy service control policy",
        Name="MockServiceControlPolicy",
        Type="SERVICE_CONTROL_POLICY",
    )["Policy"]["PolicySummary"]["Id"]
    new_policies = client.list_policies(Filter="SERVICE_CONTROL_POLICY")["Policies"]
    assert len(new_policies) == 2
    response = client.delete_policy(PolicyId=policy_id)
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200
    new_policies = client.list_policies(Filter="SERVICE_CONTROL_POLICY")["Policies"]
    assert new_policies == base_policies
    assert len(new_policies) == 1


@mock_aws
def test_delete_policy_exception():
    client = boto3.client("organizations", region_name="us-east-1")
    _ = client.create_organization(FeatureSet="ALL")["Organization"]
    non_existent_policy_id = utils.make_random_policy_id()
    with pytest.raises(ClientError) as e:
        client.delete_policy(PolicyId=non_existent_policy_id)
    ex = e.value
    assert ex.operation_name == "DeletePolicy"
    assert ex.response["Error"]["Code"] == "PolicyNotFoundException"
    assert (
        ex.response["Error"]["Message"]
        == "We can't find a policy with the PolicyId that you specified."
    )

    # Attempt to delete an attached policy
    policy_id = client.create_policy(
        Content=json.dumps(policy_doc01),
        Description="A dummy service control policy",
        Name="MockServiceControlPolicy",
        Type="SERVICE_CONTROL_POLICY",
    )["Policy"]["PolicySummary"]["Id"]
    root_id = client.list_roots()["Roots"][0]["Id"]
    client.attach_policy(PolicyId=policy_id, TargetId=root_id)
    with pytest.raises(ClientError) as e:
        client.delete_policy(PolicyId=policy_id)
    ex = e.value
    assert ex.operation_name == "DeletePolicy"
    assert ex.response["Error"]["Code"] == "400"
    assert "PolicyInUseException" in ex.response["Error"]["Message"]


@mock_aws
def test_attach_policy_exception():
    client = boto3.client("organizations", region_name="us-east-1")
    _ = client.create_organization(FeatureSet="ALL")["Organization"]
    root_id = "r-dj873"
    ou_id = "ou-gi99-i7r8eh2i2"
    account_id = "126644886543"
    policy_id = client.create_policy(
        Content=json.dumps(policy_doc01),
        Description="A dummy service control policy",
        Name="MockServiceControlPolicy",
        Type="SERVICE_CONTROL_POLICY",
    )["Policy"]["PolicySummary"]["Id"]
    with pytest.raises(ClientError) as e:
        client.attach_policy(PolicyId=policy_id, TargetId=root_id)
    ex = e.value
    assert ex.operation_name == "AttachPolicy"
    assert ex.response["Error"]["Code"] == "400"
    assert "OrganizationalUnitNotFoundException" in ex.response["Error"]["Message"]
    with pytest.raises(ClientError) as e:
        client.attach_policy(PolicyId=policy_id, TargetId=ou_id)
    ex = e.value
    assert ex.operation_name == "AttachPolicy"
    assert ex.response["Error"]["Code"] == "400"
    assert "OrganizationalUnitNotFoundException" in ex.response["Error"]["Message"]
    with pytest.raises(ClientError) as e:
        client.attach_policy(PolicyId=policy_id, TargetId=account_id)
    ex = e.value
    assert ex.operation_name == "AttachPolicy"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "AccountNotFoundException" in ex.response["Error"]["Code"]
    assert ex.response["Error"]["Message"] == (
        "You specified an account that doesn't exist."
    )
    with pytest.raises(ClientError) as e:
        client.attach_policy(PolicyId=policy_id, TargetId="meaninglessstring")
    ex = e.value
    assert ex.operation_name == "AttachPolicy"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "InvalidInputException" in ex.response["Error"]["Code"]
    assert ex.response["Error"]["Message"] == "You specified an invalid value."


@mock_aws
def test_update_policy():
    client = boto3.client("organizations", region_name="us-east-1")
    org = client.create_organization(FeatureSet="ALL")["Organization"]

    policy_dict = {
        "Content": json.dumps(policy_doc01),
        "Description": "A dummy service control policy",
        "Name": "MockServiceControlPolicy",
        "Type": "SERVICE_CONTROL_POLICY",
    }
    policy_id = client.create_policy(**policy_dict)["Policy"]["PolicySummary"]["Id"]

    for key in ("Description", "Name"):
        response = client.update_policy(**{"PolicyId": policy_id, key: "foobar"})
        policy = client.describe_policy(PolicyId=policy_id)
        assert policy["Policy"]["PolicySummary"][key] == "foobar"
        validate_service_control_policy(org, response["Policy"])

    response = client.update_policy(PolicyId=policy_id, Content="foobar")
    policy = client.describe_policy(PolicyId=policy_id)
    assert policy["Policy"]["Content"] == "foobar"
    validate_service_control_policy(org, response["Policy"])


@mock_aws
def test_update_policy_exception():
    client = boto3.client("organizations", region_name="us-east-1")
    _ = client.create_organization(FeatureSet="ALL")["Organization"]
    non_existent_policy_id = utils.make_random_policy_id()
    with pytest.raises(ClientError) as e:
        client.update_policy(PolicyId=non_existent_policy_id)
    ex = e.value
    assert ex.operation_name == "UpdatePolicy"
    assert ex.response["Error"]["Code"] == "PolicyNotFoundException"
    assert (
        ex.response["Error"]["Message"]
        == "We can't find a policy with the PolicyId that you specified."
    )


@mock_aws
def test_list_polices():
    client = boto3.client("organizations", region_name="us-east-1")
    org = client.create_organization(FeatureSet="ALL")["Organization"]
    for i in range(0, 4):
        client.create_policy(
            Content=json.dumps(policy_doc01),
            Description="A dummy service control policy",
            Name="MockServiceControlPolicy" + str(i),
            Type="SERVICE_CONTROL_POLICY",
        )
    response = client.list_policies(Filter="SERVICE_CONTROL_POLICY")
    for policy in response["Policies"]:
        validate_policy_summary(org, policy)


@mock_aws
def test_list_policies_for_target():
    client = boto3.client("organizations", region_name="us-east-1")
    org = client.create_organization(FeatureSet="ALL")["Organization"]
    root_id = client.list_roots()["Roots"][0]["Id"]
    ou_id = client.create_organizational_unit(ParentId=root_id, Name="ou01")[
        "OrganizationalUnit"
    ]["Id"]
    account_id = client.create_account(AccountName=mockname, Email=mockemail)[
        "CreateAccountStatus"
    ]["AccountId"]
    policy_id = client.create_policy(
        Content=json.dumps(policy_doc01),
        Description="A dummy service control policy",
        Name="MockServiceControlPolicy",
        Type="SERVICE_CONTROL_POLICY",
    )["Policy"]["PolicySummary"]["Id"]
    client.attach_policy(PolicyId=policy_id, TargetId=ou_id)
    response = client.list_policies_for_target(
        TargetId=ou_id, Filter="SERVICE_CONTROL_POLICY"
    )
    for policy in response["Policies"]:
        validate_policy_summary(org, policy)
    client.attach_policy(PolicyId=policy_id, TargetId=account_id)
    response = client.list_policies_for_target(
        TargetId=account_id, Filter="SERVICE_CONTROL_POLICY"
    )
    for policy in response["Policies"]:
        validate_policy_summary(org, policy)


@mock_aws
def test_list_policies_for_target_exception():
    client = boto3.client("organizations", region_name="us-east-1")
    _ = client.create_organization(FeatureSet="ALL")["Organization"]
    root_id = client.list_roots()["Roots"][0]["Id"]
    ou_id = "ou-gi99-i7r8eh2i2"
    account_id = "126644886543"
    with pytest.raises(ClientError) as e:
        client.list_policies_for_target(TargetId=ou_id, Filter="SERVICE_CONTROL_POLICY")
    ex = e.value
    assert ex.operation_name == "ListPoliciesForTarget"
    assert ex.response["Error"]["Code"] == "400"
    assert "OrganizationalUnitNotFoundException" in ex.response["Error"]["Message"]
    with pytest.raises(ClientError) as e:
        client.list_policies_for_target(
            TargetId=account_id, Filter="SERVICE_CONTROL_POLICY"
        )
    ex = e.value
    assert ex.operation_name == "ListPoliciesForTarget"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "AccountNotFoundException" in ex.response["Error"]["Code"]
    assert ex.response["Error"]["Message"] == (
        "You specified an account that doesn't exist."
    )
    with pytest.raises(ClientError) as e:
        client.list_policies_for_target(
            TargetId="meaninglessstring", Filter="SERVICE_CONTROL_POLICY"
        )
    ex = e.value
    assert ex.operation_name == "ListPoliciesForTarget"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "InvalidInputException" in ex.response["Error"]["Code"]
    assert ex.response["Error"]["Message"] == "You specified an invalid value."

    # not existing root
    # when
    with pytest.raises(ClientError) as e:
        client.list_policies_for_target(
            TargetId="r-0000", Filter="SERVICE_CONTROL_POLICY"
        )

    # then
    ex = e.value
    assert ex.operation_name == "ListPoliciesForTarget"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "TargetNotFoundException" in ex.response["Error"]["Code"]
    assert ex.response["Error"]["Message"] == (
        "You specified a target that doesn't exist."
    )

    # invalid policy type
    # when
    with pytest.raises(ClientError) as e:
        client.list_policies_for_target(TargetId=root_id, Filter="MOTO")

    # then
    ex = e.value
    assert ex.operation_name == "ListPoliciesForTarget"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "InvalidInputException" in ex.response["Error"]["Code"]
    assert ex.response["Error"]["Message"] == "You specified an invalid value."


@mock_aws
def test_list_targets_for_policy():
    client = boto3.client("organizations", region_name="us-east-1")
    _ = client.create_organization(FeatureSet="ALL")["Organization"]
    root_id = client.list_roots()["Roots"][0]["Id"]
    ou_id = client.create_organizational_unit(ParentId=root_id, Name="ou01")[
        "OrganizationalUnit"
    ]["Id"]
    account_id = client.create_account(AccountName=mockname, Email=mockemail)[
        "CreateAccountStatus"
    ]["AccountId"]
    policy_id = client.create_policy(
        Content=json.dumps(policy_doc01),
        Description="A dummy service control policy",
        Name="MockServiceControlPolicy",
        Type="SERVICE_CONTROL_POLICY",
    )["Policy"]["PolicySummary"]["Id"]
    client.attach_policy(PolicyId=policy_id, TargetId=root_id)
    client.attach_policy(PolicyId=policy_id, TargetId=ou_id)
    client.attach_policy(PolicyId=policy_id, TargetId=account_id)
    response = client.list_targets_for_policy(PolicyId=policy_id)
    for target in response["Targets"]:
        assert isinstance(target, dict)
        assert isinstance(target["Name"], str)
        assert isinstance(target["Arn"], str)
        assert isinstance(target["TargetId"], str)
        assert target["Type"] in ["ROOT", "ORGANIZATIONAL_UNIT", "ACCOUNT"]


@mock_aws
def test_list_targets_for_policy_exception():
    client = boto3.client("organizations", region_name="us-east-1")
    _ = client.create_organization(FeatureSet="ALL")["Organization"]
    policy_id = "p-47fhe9s3"
    with pytest.raises(ClientError) as e:
        client.list_targets_for_policy(PolicyId=policy_id)
    ex = e.value
    assert ex.operation_name == "ListTargetsForPolicy"
    assert ex.response["Error"]["Code"] == "PolicyNotFoundException"
    assert (
        ex.response["Error"]["Message"] == "You specified a policy that doesn't exist."
    )
    with pytest.raises(ClientError) as e:
        client.list_targets_for_policy(PolicyId="meaninglessstring")
    ex = e.value
    assert ex.operation_name == "ListTargetsForPolicy"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "InvalidInputException" in ex.response["Error"]["Code"]
    assert ex.response["Error"]["Message"] == "You specified an invalid value."


@mock_aws
def test_tag_resource_account():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")
    resource_id = client.create_account(AccountName=mockname, Email=mockemail)[
        "CreateAccountStatus"
    ]["AccountId"]

    client.tag_resource(ResourceId=resource_id, Tags=[{"Key": "key", "Value": "value"}])

    response = client.list_tags_for_resource(ResourceId=resource_id)
    assert response["Tags"] == [{"Key": "key", "Value": "value"}]

    # adding a tag with an existing key, will update the value
    client.tag_resource(
        ResourceId=resource_id, Tags=[{"Key": "key", "Value": "new-value"}]
    )

    response = client.list_tags_for_resource(ResourceId=resource_id)
    assert response["Tags"] == [{"Key": "key", "Value": "new-value"}]

    client.untag_resource(ResourceId=resource_id, TagKeys=["key"])

    response = client.list_tags_for_resource(ResourceId=resource_id)
    assert response["Tags"] == []


@mock_aws
def test_tag_resource_organization_organization_root():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")

    resource_id = client.list_roots()["Roots"][0]["Id"]
    client.tag_resource(ResourceId=resource_id, Tags=[{"Key": "key", "Value": "value"}])

    response = client.list_tags_for_resource(ResourceId=resource_id)
    assert response["Tags"] == [{"Key": "key", "Value": "value"}]

    # adding a tag with an existing key, will update the value
    client.tag_resource(
        ResourceId=resource_id, Tags=[{"Key": "key", "Value": "new-value"}]
    )

    response = client.list_tags_for_resource(ResourceId=resource_id)
    assert response["Tags"] == [{"Key": "key", "Value": "new-value"}]

    client.untag_resource(ResourceId=resource_id, TagKeys=["key"])

    response = client.list_tags_for_resource(ResourceId=resource_id)
    assert response["Tags"] == []


@mock_aws
def test_tag_resource_organization_organizational_unit():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")
    root_id = client.list_roots()["Roots"][0]["Id"]
    resource_id = client.create_organizational_unit(ParentId=root_id, Name="ou01")[
        "OrganizationalUnit"
    ]["Id"]

    client.tag_resource(ResourceId=resource_id, Tags=[{"Key": "key", "Value": "value"}])

    response = client.list_tags_for_resource(ResourceId=resource_id)
    assert response["Tags"] == [{"Key": "key", "Value": "value"}]

    # adding a tag with an existing key, will update the value
    client.tag_resource(
        ResourceId=resource_id, Tags=[{"Key": "key", "Value": "new-value"}]
    )

    response = client.list_tags_for_resource(ResourceId=resource_id)
    assert response["Tags"] == [{"Key": "key", "Value": "new-value"}]

    client.untag_resource(ResourceId=resource_id, TagKeys=["key"])

    response = client.list_tags_for_resource(ResourceId=resource_id)
    assert response["Tags"] == []


@mock_aws
@pytest.mark.parametrize(
    "policy_type", ["AISERVICES_OPT_OUT_POLICY", "SERVICE_CONTROL_POLICY"]
)
@pytest.mark.parametrize(
    "region,partition",
    [("us-east-1", "aws"), ("cn-north-1", "aws-cn"), ("us-isob-east-1", "aws-iso-b")],
)
def test_tag_resource_policy(policy_type, region, partition):
    client = boto3.client("organizations", region_name=region)
    client.create_organization(FeatureSet="ALL")
    _ = client.list_roots()["Roots"][0]["Id"]

    policy = client.create_policy(
        Content=json.dumps(policy_doc01),
        Description="A dummy service control policy",
        Name="MockServiceControlPolicy",
        Type=policy_type,
    )["Policy"]["PolicySummary"]
    assert policy["Arn"].startswith(
        f"arn:{partition}:organizations::{ACCOUNT_ID}:policy/"
    )

    resource_id = policy["Id"]

    client.tag_resource(ResourceId=resource_id, Tags=[{"Key": "key", "Value": "value"}])

    response = client.list_tags_for_resource(ResourceId=resource_id)
    assert response["Tags"] == [{"Key": "key", "Value": "value"}]

    # adding a tag with an existing key, will update the value
    client.tag_resource(
        ResourceId=resource_id, Tags=[{"Key": "key", "Value": "new-value"}]
    )

    response = client.list_tags_for_resource(ResourceId=resource_id)
    assert response["Tags"] == [{"Key": "key", "Value": "new-value"}]

    client.untag_resource(ResourceId=resource_id, TagKeys=["key"])

    response = client.list_tags_for_resource(ResourceId=resource_id)
    assert response["Tags"] == []


@mock_aws
def test_tag_resource_errors():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")

    with pytest.raises(ClientError) as e:
        client.tag_resource(
            ResourceId="0A000000X000", Tags=[{"Key": "key", "Value": "value"}]
        )
    ex = e.value
    assert ex.operation_name == "TagResource"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "InvalidInputException" in ex.response["Error"]["Code"]
    assert ex.response["Error"]["Message"] == (
        "You provided a value that does not match the required pattern."
    )
    with pytest.raises(ClientError) as e:
        client.tag_resource(
            ResourceId="000000000000", Tags=[{"Key": "key", "Value": "value"}]
        )
    ex = e.value
    assert ex.operation_name == "TagResource"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "TargetNotFoundException" in ex.response["Error"]["Code"]
    assert (
        ex.response["Error"]["Message"] == "You specified a target that doesn't exist."
    )


def test__get_resource_for_tagging_existing_root():
    org = FakeOrganization(ACCOUNT_ID, region_name="us-east-1", feature_set="ALL")
    root = FakeRoot(org)

    org_backend = OrganizationsBackend(region_name="N/A", account_id="N/A")
    org_backend.ou.append(root)
    response = org_backend._get_resource_for_tagging(root.id)
    assert response.id == root.id


def test__get_resource_for_tagging_existing_non_root():
    org_backend = OrganizationsBackend(region_name="N/A", account_id="N/A")
    with pytest.raises(TargetNotFoundException) as e:
        org_backend._get_resource_for_tagging("r-abcd")
    ex = e.value
    assert ex.code == 400
    assert "TargetNotFoundException" in ex.description
    assert ex.message == "You specified a target that doesn't exist."


def test__get_resource_for_tagging_existing_ou():
    org = FakeOrganization(ACCOUNT_ID, region_name="us-east-1", feature_set="ALL")
    ou = FakeOrganizationalUnit(org)
    org_backend = OrganizationsBackend(region_name="N/A", account_id="N/A")

    org_backend.ou.append(ou)
    response = org_backend._get_resource_for_tagging(ou.id)
    assert response.id == ou.id


def test__get_resource_for_tagging_non_existing_ou():
    org_backend = OrganizationsBackend(region_name="N/A", account_id="N/A")
    with pytest.raises(TargetNotFoundException) as e:
        org_backend._get_resource_for_tagging("ou-9oyc-lv2q36ln")
    ex = e.value
    assert ex.code == 400
    assert "TargetNotFoundException" in ex.description
    assert ex.message == "You specified a target that doesn't exist."


def test__get_resource_for_tagging_existing_account():
    org = FakeOrganization(ACCOUNT_ID, region_name="us-east-1", feature_set="ALL")
    org_backend = OrganizationsBackend(region_name="N/A", account_id="N/A")
    account = FakeAccount(org, AccountName="test", Email="test@test.test")

    org_backend.accounts.append(account)
    response = org_backend._get_resource_for_tagging(account.id)
    assert response.id == account.id


def test__get_resource_for_tagging_non_existing_account():
    org_backend = OrganizationsBackend(region_name="N/A", account_id="N/A")
    with pytest.raises(TargetNotFoundException) as e:
        org_backend._get_resource_for_tagging("100326223992")
    ex = e.value
    assert ex.code == 400
    assert "TargetNotFoundException" in ex.description
    assert ex.message == "You specified a target that doesn't exist."


def test__get_resource_for_tagging_existing_policy():
    org = FakeOrganization(ACCOUNT_ID, region_name="us-east-1", feature_set="ALL")
    org_backend = OrganizationsBackend(region_name="N/A", account_id="N/A")
    policy = FakePolicy(org, Type="SERVICE_CONTROL_POLICY")

    org_backend.policies.append(policy)
    response = org_backend._get_resource_for_tagging(policy.id)
    assert response.id == policy.id


def test__get_resource_for_tagging_non_existing_policy():
    org_backend = OrganizationsBackend(region_name="N/A", account_id="N/A")
    with pytest.raises(TargetNotFoundException) as e:
        org_backend._get_resource_for_tagging("p-y1vas4da")
    ex = e.value
    assert ex.code == 400
    assert "TargetNotFoundException" in ex.description
    assert ex.message == "You specified a target that doesn't exist."


def test__get_resource_to_tag_incorrect_resource():
    org_backend = OrganizationsBackend(region_name="N/A", account_id="N/A")
    with pytest.raises(InvalidInputException) as e:
        org_backend._get_resource_for_tagging("10032622399200")
    ex = e.value
    assert ex.code == 400
    assert "InvalidInputException" in ex.description
    assert ex.message == (
        "You provided a value that does not match the required pattern."
    )


@mock_aws
def test_list_tags_for_resource():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")
    account_id = client.create_account(AccountName=mockname, Email=mockemail)[
        "CreateAccountStatus"
    ]["AccountId"]
    client.tag_resource(ResourceId=account_id, Tags=[{"Key": "key", "Value": "value"}])

    response = client.list_tags_for_resource(ResourceId=account_id)

    assert response["Tags"] == [{"Key": "key", "Value": "value"}]


@mock_aws
def test_list_tags_for_resource_errors():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")

    with pytest.raises(ClientError) as e:
        client.list_tags_for_resource(ResourceId="000x00000A00")
    ex = e.value
    assert ex.operation_name == "ListTagsForResource"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "InvalidInputException" in ex.response["Error"]["Code"]
    assert ex.response["Error"]["Message"] == (
        "You provided a value that does not match the required pattern."
    )
    with pytest.raises(ClientError) as e:
        client.list_tags_for_resource(ResourceId="000000000000")
    ex = e.value
    assert ex.operation_name == "ListTagsForResource"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "TargetNotFoundException" in ex.response["Error"]["Code"]
    assert ex.response["Error"]["Message"] == (
        "You specified a target that doesn't exist."
    )


@mock_aws
def test_untag_resource():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")
    account_id = client.create_account(AccountName=mockname, Email=mockemail)[
        "CreateAccountStatus"
    ]["AccountId"]
    client.tag_resource(ResourceId=account_id, Tags=[{"Key": "key", "Value": "value"}])
    response = client.list_tags_for_resource(ResourceId=account_id)
    assert response["Tags"] == [{"Key": "key", "Value": "value"}]

    # removing a non existing tag should not raise any error
    client.untag_resource(ResourceId=account_id, TagKeys=["not-existing"])
    response = client.list_tags_for_resource(ResourceId=account_id)
    assert response["Tags"] == [{"Key": "key", "Value": "value"}]

    client.untag_resource(ResourceId=account_id, TagKeys=["key"])
    response = client.list_tags_for_resource(ResourceId=account_id)
    assert len(response["Tags"]) == 0


@mock_aws
def test_untag_resource_errors():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")

    with pytest.raises(ClientError) as e:
        client.untag_resource(ResourceId="0X00000000A0", TagKeys=["key"])
    ex = e.value
    assert ex.operation_name == "UntagResource"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "InvalidInputException" in ex.response["Error"]["Code"]
    assert ex.response["Error"]["Message"] == (
        "You provided a value that does not match the required pattern."
    )
    with pytest.raises(ClientError) as e:
        client.untag_resource(ResourceId="000000000000", TagKeys=["key"])
    ex = e.value
    assert ex.operation_name == "UntagResource"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "TargetNotFoundException" in ex.response["Error"]["Code"]
    assert (
        ex.response["Error"]["Message"] == "You specified a target that doesn't exist."
    )


@mock_aws
def test_update_organizational_unit():
    client = boto3.client("organizations", region_name="us-east-1")
    org = client.create_organization(FeatureSet="ALL")["Organization"]
    root_id = client.list_roots()["Roots"][0]["Id"]
    ou_name = "ou01"
    response = client.create_organizational_unit(ParentId=root_id, Name=ou_name)
    validate_organizational_unit(org, response)
    assert response["OrganizationalUnit"]["Name"] == ou_name
    new_ou_name = "ou02"
    response = client.update_organizational_unit(
        OrganizationalUnitId=response["OrganizationalUnit"]["Id"], Name=new_ou_name
    )
    validate_organizational_unit(org, response)
    assert response["OrganizationalUnit"]["Name"] == new_ou_name


@mock_aws
def test_update_organizational_unit_duplicate_error():
    client = boto3.client("organizations", region_name="us-east-1")
    org = client.create_organization(FeatureSet="ALL")["Organization"]
    root_id = client.list_roots()["Roots"][0]["Id"]
    ou_name = "ou01"
    response = client.create_organizational_unit(ParentId=root_id, Name=ou_name)
    validate_organizational_unit(org, response)
    assert response["OrganizationalUnit"]["Name"] == ou_name
    with pytest.raises(ClientError) as e:
        client.update_organizational_unit(
            OrganizationalUnitId=response["OrganizationalUnit"]["Id"], Name=ou_name
        )
    exc = e.value
    assert exc.operation_name == "UpdateOrganizationalUnit"
    assert "DuplicateOrganizationalUnitException" in exc.response["Error"]["Code"]
    assert (
        exc.response["Error"]["Message"] == "An OU with the same name already exists."
    )


@mock_aws
def test_enable_aws_service_access():
    # given
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")

    # when
    client.enable_aws_service_access(ServicePrincipal="config.amazonaws.com")

    # then
    response = client.list_aws_service_access_for_organization()
    assert len(response["EnabledServicePrincipals"]) == 1
    service = response["EnabledServicePrincipals"][0]
    assert service["ServicePrincipal"] == "config.amazonaws.com"
    date_enabled = service["DateEnabled"]
    assert isinstance(date_enabled, datetime)

    # enabling the same service again should not result in any error or change
    # when
    client.enable_aws_service_access(ServicePrincipal="config.amazonaws.com")

    # then
    response = client.list_aws_service_access_for_organization()
    assert len(response["EnabledServicePrincipals"]) == 1
    service = response["EnabledServicePrincipals"][0]
    assert service["ServicePrincipal"] == "config.amazonaws.com"
    assert service["DateEnabled"] == date_enabled


@mock_aws
def test_enable_aws_service_access_error():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")

    with pytest.raises(ClientError) as e:
        client.enable_aws_service_access(ServicePrincipal="moto.amazonaws.com")
    ex = e.value
    assert ex.operation_name == "EnableAWSServiceAccess"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "InvalidInputException" in ex.response["Error"]["Code"]
    assert ex.response["Error"]["Message"] == (
        "You specified an unrecognized service principal."
    )


@mock_aws
def test_enable_multiple_aws_service_access():
    # given
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")
    client.enable_aws_service_access(ServicePrincipal="config.amazonaws.com")
    client.enable_aws_service_access(ServicePrincipal="ram.amazonaws.com")

    # when
    response = client.list_aws_service_access_for_organization()

    # then
    assert len(response["EnabledServicePrincipals"]) == 2
    services = sorted(
        response["EnabledServicePrincipals"], key=lambda i: i["ServicePrincipal"]
    )
    assert services[0]["ServicePrincipal"] == "config.amazonaws.com"
    assert isinstance(services[0]["DateEnabled"], datetime)
    assert services[1]["ServicePrincipal"] == "ram.amazonaws.com"
    assert isinstance(services[1]["DateEnabled"], datetime)


@mock_aws
def test_disable_aws_service_access():
    # given
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")
    client.enable_aws_service_access(ServicePrincipal="config.amazonaws.com")

    # when
    client.disable_aws_service_access(ServicePrincipal="config.amazonaws.com")

    # then
    response = client.list_aws_service_access_for_organization()
    assert len(response["EnabledServicePrincipals"]) == 0

    # disabling the same service again should not result in any error
    # when
    client.disable_aws_service_access(ServicePrincipal="config.amazonaws.com")

    # then
    response = client.list_aws_service_access_for_organization()
    assert len(response["EnabledServicePrincipals"]) == 0


@mock_aws
def test_disable_aws_service_access_errors():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")

    with pytest.raises(ClientError) as e:
        client.disable_aws_service_access(ServicePrincipal="moto.amazonaws.com")
    ex = e.value
    assert ex.operation_name == "DisableAWSServiceAccess"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "InvalidInputException" in ex.response["Error"]["Code"]
    assert ex.response["Error"]["Message"] == (
        "You specified an unrecognized service principal."
    )


@mock_aws
def test_register_delegated_administrator():
    # given
    client = boto3.client("organizations", region_name="us-east-1")
    org_id = client.create_organization(FeatureSet="ALL")["Organization"]["Id"]
    account_id = client.create_account(AccountName=mockname, Email=mockemail)[
        "CreateAccountStatus"
    ]["AccountId"]

    # when
    client.register_delegated_administrator(
        AccountId=account_id, ServicePrincipal="ssm.amazonaws.com"
    )

    # then
    response = client.list_delegated_administrators()
    assert len(response["DelegatedAdministrators"]) == 1
    admin = response["DelegatedAdministrators"][0]
    assert admin["Id"] == account_id
    assert admin["Arn"] == (
        f"arn:aws:organizations::{ACCOUNT_ID}:account/{org_id}/{account_id}"
    )
    assert admin["Email"] == mockemail
    assert admin["Name"] == mockname
    assert admin["Status"] == "ACTIVE"
    assert admin["JoinedMethod"] == "CREATED"
    assert isinstance(admin["JoinedTimestamp"], datetime)
    assert isinstance(admin["DelegationEnabledDate"], datetime)


@mock_aws
def test_register_delegated_administrator_errors():
    # given
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")
    account_id = client.create_account(AccountName=mockname, Email=mockemail)[
        "CreateAccountStatus"
    ]["AccountId"]
    client.register_delegated_administrator(
        AccountId=account_id, ServicePrincipal="ssm.amazonaws.com"
    )

    # register master Account
    # when
    with pytest.raises(ClientError) as e:
        client.register_delegated_administrator(
            AccountId=ACCOUNT_ID, ServicePrincipal="ssm.amazonaws.com"
        )

    # then
    ex = e.value
    assert ex.operation_name == "RegisterDelegatedAdministrator"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "ConstraintViolationException" in ex.response["Error"]["Code"]
    assert ex.response["Error"]["Message"] == (
        "You cannot register master account/yourself as delegated "
        "administrator for your organization."
    )

    # register not existing Account
    # when
    with pytest.raises(ClientError) as e:
        client.register_delegated_administrator(
            AccountId="000000000000", ServicePrincipal="ssm.amazonaws.com"
        )

    # then
    ex = e.value
    assert ex.operation_name == "RegisterDelegatedAdministrator"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "AccountNotFoundException" in ex.response["Error"]["Code"]
    assert (
        ex.response["Error"]["Message"]
        == "You specified an account that doesn't exist."
    )

    # register not supported service
    # when
    with pytest.raises(ClientError) as e:
        client.register_delegated_administrator(
            AccountId=account_id, ServicePrincipal="moto.amazonaws.com"
        )

    # then
    ex = e.value
    assert ex.operation_name == "RegisterDelegatedAdministrator"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "InvalidInputException" in ex.response["Error"]["Code"]
    assert ex.response["Error"]["Message"] == (
        "You specified an unrecognized service principal."
    )

    # register service again
    # when
    with pytest.raises(ClientError) as e:
        client.register_delegated_administrator(
            AccountId=account_id, ServicePrincipal="ssm.amazonaws.com"
        )

    # then
    ex = e.value
    assert ex.operation_name == "RegisterDelegatedAdministrator"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "AccountAlreadyRegisteredException" in ex.response["Error"]["Code"]
    assert ex.response["Error"]["Message"] == (
        "The provided account is already a delegated administrator for your organization."
    )


@mock_aws
def test_list_delegated_administrators():
    # given
    client = boto3.client("organizations", region_name="us-east-1")
    org_id = client.create_organization(FeatureSet="ALL")["Organization"]["Id"]
    account_id_1 = client.create_account(AccountName=mockname, Email=mockemail)[
        "CreateAccountStatus"
    ]["AccountId"]
    account_id_2 = client.create_account(AccountName=mockname, Email=mockemail)[
        "CreateAccountStatus"
    ]["AccountId"]
    client.register_delegated_administrator(
        AccountId=account_id_1, ServicePrincipal="ssm.amazonaws.com"
    )
    client.register_delegated_administrator(
        AccountId=account_id_2, ServicePrincipal="guardduty.amazonaws.com"
    )

    # when
    response = client.list_delegated_administrators()

    # then
    assert len(response["DelegatedAdministrators"]) == 2
    assert sorted([admin["Id"] for admin in response["DelegatedAdministrators"]]) == (
        sorted([account_id_1, account_id_2])
    )

    # when
    response = client.list_delegated_administrators(
        ServicePrincipal="ssm.amazonaws.com"
    )

    # then
    assert len(response["DelegatedAdministrators"]) == 1
    admin = response["DelegatedAdministrators"][0]
    assert admin["Id"] == account_id_1
    assert admin["Arn"] == (
        f"arn:aws:organizations::{ACCOUNT_ID}:account/{org_id}/{account_id_1}"
    )
    assert admin["Email"] == mockemail
    assert admin["Name"] == mockname
    assert admin["Status"] == "ACTIVE"
    assert admin["JoinedMethod"] == "CREATED"
    assert isinstance(admin["JoinedTimestamp"], datetime)
    assert isinstance(admin["DelegationEnabledDate"], datetime)


@mock_aws
def test_list_delegated_administrators_erros():
    # given
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")

    # list not supported service
    # when
    with pytest.raises(ClientError) as e:
        client.list_delegated_administrators(ServicePrincipal="moto.amazonaws.com")

    # then
    ex = e.value
    assert ex.operation_name == "ListDelegatedAdministrators"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "InvalidInputException" in ex.response["Error"]["Code"]
    assert ex.response["Error"]["Message"] == (
        "You specified an unrecognized service principal."
    )


@mock_aws
def test_list_delegated_services_for_account():
    # given
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")
    account_id = client.create_account(AccountName=mockname, Email=mockemail)[
        "CreateAccountStatus"
    ]["AccountId"]
    client.register_delegated_administrator(
        AccountId=account_id, ServicePrincipal="ssm.amazonaws.com"
    )
    client.register_delegated_administrator(
        AccountId=account_id, ServicePrincipal="guardduty.amazonaws.com"
    )

    # when
    response = client.list_delegated_services_for_account(AccountId=account_id)

    # then
    assert len(response["DelegatedServices"]) == 2
    assert sorted(
        [service["ServicePrincipal"] for service in response["DelegatedServices"]]
    ) == ["guardduty.amazonaws.com", "ssm.amazonaws.com"]


@mock_aws
def test_list_delegated_services_for_account_erros():
    # given
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")

    # list services for not existing Account
    # when
    with pytest.raises(ClientError) as e:
        client.list_delegated_services_for_account(AccountId="000000000000")

    # then
    ex = e.value
    assert ex.operation_name == "ListDelegatedServicesForAccount"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "AWSOrganizationsNotInUseException" in ex.response["Error"]["Code"]
    assert ex.response["Error"]["Message"] == (
        "Your account is not a member of an organization."
    )

    # list services for not registered Account
    # when
    with pytest.raises(ClientError) as e:
        client.list_delegated_services_for_account(AccountId=ACCOUNT_ID)

    # then
    ex = e.value
    assert ex.operation_name == "ListDelegatedServicesForAccount"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "AccountNotRegisteredException" in ex.response["Error"]["Code"]
    assert ex.response["Error"]["Message"] == (
        "The provided account is not a registered delegated administrator for your organization."
    )


@mock_aws
def test_deregister_delegated_administrator():
    # given
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")
    account_id = client.create_account(AccountName=mockname, Email=mockemail)[
        "CreateAccountStatus"
    ]["AccountId"]
    client.register_delegated_administrator(
        AccountId=account_id, ServicePrincipal="ssm.amazonaws.com"
    )

    # when
    client.deregister_delegated_administrator(
        AccountId=account_id, ServicePrincipal="ssm.amazonaws.com"
    )

    # then
    response = client.list_delegated_administrators()
    assert len(response["DelegatedAdministrators"]) == 0


@mock_aws
def test_deregister_delegated_administrator_erros():
    # given
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")
    account_id = client.create_account(AccountName=mockname, Email=mockemail)[
        "CreateAccountStatus"
    ]["AccountId"]

    # deregister master Account
    # when
    with pytest.raises(ClientError) as e:
        client.deregister_delegated_administrator(
            AccountId=ACCOUNT_ID, ServicePrincipal="ssm.amazonaws.com"
        )

    # then
    ex = e.value
    assert ex.operation_name == "DeregisterDelegatedAdministrator"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "ConstraintViolationException" in ex.response["Error"]["Code"]
    assert ex.response["Error"]["Message"] == (
        "You cannot register master account/yourself as delegated "
        "administrator for your organization."
    )

    # deregister not existing Account
    # when
    with pytest.raises(ClientError) as e:
        client.deregister_delegated_administrator(
            AccountId="000000000000", ServicePrincipal="ssm.amazonaws.com"
        )

    # then
    ex = e.value
    assert ex.operation_name == "DeregisterDelegatedAdministrator"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "AccountNotFoundException" in ex.response["Error"]["Code"]
    assert ex.response["Error"]["Message"] == (
        "You specified an account that doesn't exist."
    )

    # deregister not registered Account
    # when
    with pytest.raises(ClientError) as e:
        client.deregister_delegated_administrator(
            AccountId=account_id, ServicePrincipal="ssm.amazonaws.com"
        )

    # then
    ex = e.value
    assert ex.operation_name == "DeregisterDelegatedAdministrator"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "AccountNotRegisteredException" in ex.response["Error"]["Code"]
    assert ex.response["Error"]["Message"] == (
        "The provided account is not a registered delegated administrator for your organization."
    )

    # given
    client.register_delegated_administrator(
        AccountId=account_id, ServicePrincipal="ssm.amazonaws.com"
    )

    # deregister not registered service
    # when
    with pytest.raises(ClientError) as e:
        client.deregister_delegated_administrator(
            AccountId=account_id, ServicePrincipal="guardduty.amazonaws.com"
        )

    # then
    ex = e.value
    assert ex.operation_name == "DeregisterDelegatedAdministrator"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "InvalidInputException" in ex.response["Error"]["Code"]
    assert ex.response["Error"]["Message"] == (
        "You specified an unrecognized service principal."
    )


@mock_aws
@pytest.mark.parametrize(
    "policy_type", ["AISERVICES_OPT_OUT_POLICY", "SERVICE_CONTROL_POLICY"]
)
@pytest.mark.parametrize(
    "region,partition",
    [("us-east-1", "aws"), ("cn-north-1", "aws-cn"), ("us-isob-east-1", "aws-iso-b")],
)
def test_enable_policy_type(policy_type, region, partition):
    # given
    client = boto3.client("organizations", region_name=region)
    org = client.create_organization(FeatureSet="ALL")["Organization"]
    root_id = client.list_roots()["Roots"][0]["Id"]

    # when
    response = client.enable_policy_type(RootId=root_id, PolicyType=policy_type)

    # then
    root = response["Root"]
    assert root["Id"] == root_id
    assert root["Arn"] == (
        utils.ROOT_ARN_FORMAT.format(
            partition, org["MasterAccountId"], org["Id"], root_id
        )
    )
    assert root["Name"] == "Root"
    assert sorted(root["PolicyTypes"], key=lambda x: x["Type"]) == (
        [{"Type": policy_type, "Status": "ENABLED"}]
    )


@mock_aws
def test_enable_policy_type_errors():
    # given
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")
    root_id = client.list_roots()["Roots"][0]["Id"]

    # not existing root
    # when
    with pytest.raises(ClientError) as e:
        client.enable_policy_type(
            RootId="r-0000", PolicyType="AISERVICES_OPT_OUT_POLICY"
        )

    # then
    ex = e.value
    assert ex.operation_name == "EnablePolicyType"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RootNotFoundException" in ex.response["Error"]["Code"]
    assert ex.response["Error"]["Message"] == (
        "You specified a root that doesn't exist."
    )

    # enable policy again
    # given
    client.enable_policy_type(RootId=root_id, PolicyType="SERVICE_CONTROL_POLICY")

    # when
    with pytest.raises(ClientError) as e:
        client.enable_policy_type(RootId=root_id, PolicyType="SERVICE_CONTROL_POLICY")

    # then
    ex = e.value
    assert ex.operation_name == "EnablePolicyType"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "PolicyTypeAlreadyEnabledException" in ex.response["Error"]["Code"]
    assert ex.response["Error"]["Message"] == (
        "The specified policy type is already enabled."
    )

    # invalid policy type
    # when
    with pytest.raises(ClientError) as e:
        client.enable_policy_type(RootId=root_id, PolicyType="MOTO")

    # then
    ex = e.value
    assert ex.operation_name == "EnablePolicyType"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "InvalidInputException" in ex.response["Error"]["Code"]
    assert ex.response["Error"]["Message"] == "You specified an invalid value."


@mock_aws
def test_disable_policy_type():
    # given
    client = boto3.client("organizations", region_name="us-east-1")
    org = client.create_organization(FeatureSet="ALL")["Organization"]
    root_id = client.list_roots()["Roots"][0]["Id"]
    client.enable_policy_type(RootId=root_id, PolicyType="AISERVICES_OPT_OUT_POLICY")

    # when
    response = client.disable_policy_type(
        RootId=root_id, PolicyType="AISERVICES_OPT_OUT_POLICY"
    )

    # then
    root = response["Root"]
    assert root["Id"] == root_id
    assert root["Arn"] == (
        utils.ROOT_ARN_FORMAT.format("aws", org["MasterAccountId"], org["Id"], root_id)
    )
    assert root["Name"] == "Root"
    assert root["PolicyTypes"] == []


@mock_aws
def test_disable_policy_type_errors():
    # given
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")
    root_id = client.list_roots()["Roots"][0]["Id"]

    # not existing root
    # when
    with pytest.raises(ClientError) as e:
        client.disable_policy_type(
            RootId="r-0000", PolicyType="AISERVICES_OPT_OUT_POLICY"
        )

    # then
    ex = e.value
    assert ex.operation_name == "DisablePolicyType"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "RootNotFoundException" in ex.response["Error"]["Code"]
    assert ex.response["Error"]["Message"] == (
        "You specified a root that doesn't exist."
    )

    # disable not enabled policy
    # when
    with pytest.raises(ClientError) as e:
        client.disable_policy_type(
            RootId=root_id, PolicyType="AISERVICES_OPT_OUT_POLICY"
        )

    # then
    ex = e.value
    assert ex.operation_name == "DisablePolicyType"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "PolicyTypeNotEnabledException" in ex.response["Error"]["Code"]
    assert ex.response["Error"]["Message"] == (
        "This operation can be performed only for enabled policy types."
    )

    # invalid policy type
    # when
    with pytest.raises(ClientError) as e:
        client.disable_policy_type(RootId=root_id, PolicyType="MOTO")

    # then
    ex = e.value
    assert ex.operation_name == "DisablePolicyType"
    assert ex.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert "InvalidInputException" in ex.response["Error"]["Code"]
    assert ex.response["Error"]["Message"] == "You specified an invalid value."


@mock_aws
def test_aiservices_opt_out_policy():
    # given
    client = boto3.client("organizations", region_name="us-east-1")
    org = client.create_organization(FeatureSet="ALL")["Organization"]
    root_id = client.list_roots()["Roots"][0]["Id"]
    client.enable_policy_type(RootId=root_id, PolicyType="AISERVICES_OPT_OUT_POLICY")
    ai_policy = {
        "services": {
            "@@operators_allowed_for_child_policies": ["@@none"],
            "default": {
                "@@operators_allowed_for_child_policies": ["@@none"],
                "opt_out_policy": {
                    "@@operators_allowed_for_child_policies": ["@@none"],
                    "@@assign": "optOut",
                },
            },
        }
    }

    # when
    response = client.create_policy(
        Content=json.dumps(ai_policy),
        Description="Opt out of all AI services",
        Name="ai-opt-out",
        Type="AISERVICES_OPT_OUT_POLICY",
    )

    # then
    summary = response["Policy"]["PolicySummary"]
    policy_id = summary["Id"]
    assert re.match(utils.POLICY_ID_REGEX, summary["Id"])
    assert summary["Arn"] == (
        utils.AI_POLICY_ARN_FORMAT.format(
            "aws", org["MasterAccountId"], org["Id"], summary["Id"]
        )
    )
    assert summary["Name"] == "ai-opt-out"
    assert summary["Description"] == "Opt out of all AI services"
    assert summary["Type"] == "AISERVICES_OPT_OUT_POLICY"
    assert summary["AwsManaged"] is False
    assert json.loads(response["Policy"]["Content"]) == ai_policy

    # when
    client.attach_policy(PolicyId=policy_id, TargetId=root_id)

    # then
    response = client.list_policies_for_target(
        TargetId=root_id, Filter="AISERVICES_OPT_OUT_POLICY"
    )
    assert len(response["Policies"]) == 1
    assert response["Policies"][0]["Id"] == policy_id
