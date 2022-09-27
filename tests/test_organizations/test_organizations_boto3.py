from datetime import datetime

from moto.organizations.exceptions import InvalidInputException, TargetNotFoundException
from moto.organizations.models import (
    FakeAccount,
    FakeOrganization,
    FakeOrganizationalUnit,
    FakePolicy,
    FakeRoot,
    OrganizationsBackend,
)

import boto3
import json
import sure  # noqa # pylint: disable=unused-import
from botocore.exceptions import ClientError
import pytest

from moto import mock_organizations
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from moto.organizations import utils
from .organizations_test_utils import (
    validate_organization,
    validate_roots,
    validate_organizational_unit,
    validate_account,
    validate_create_account_status,
    validate_service_control_policy,
    validate_policy_summary,
)


@mock_organizations
def test_create_organization():
    client = boto3.client("organizations", region_name="us-east-1")
    response = client.create_organization(FeatureSet="ALL")
    validate_organization(response)
    response["Organization"]["FeatureSet"].should.equal("ALL")

    response = client.list_accounts()
    len(response["Accounts"]).should.equal(1)
    response["Accounts"][0]["Name"].should.equal("master")
    response["Accounts"][0]["Id"].should.equal(ACCOUNT_ID)
    response["Accounts"][0]["Email"].should.equal(utils.MASTER_ACCOUNT_EMAIL)

    response = client.list_policies(Filter="SERVICE_CONTROL_POLICY")
    len(response["Policies"]).should.equal(1)
    response["Policies"][0]["Name"].should.equal("FullAWSAccess")
    response["Policies"][0]["Id"].should.equal(utils.DEFAULT_POLICY_ID)
    response["Policies"][0]["AwsManaged"].should.equal(True)

    response = client.list_targets_for_policy(PolicyId=utils.DEFAULT_POLICY_ID)
    len(response["Targets"]).should.equal(2)
    root_ou = [t for t in response["Targets"] if t["Type"] == "ROOT"][0]
    root_ou["Name"].should.equal("Root")
    master_account = [t for t in response["Targets"] if t["Type"] == "ACCOUNT"][0]
    master_account["Name"].should.equal("master")


@mock_organizations
def test_create_organization_without_feature_set():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization()
    response = client.describe_organization()
    validate_organization(response)
    response["Organization"]["FeatureSet"].should.equal("ALL")


@mock_organizations
def test_describe_organization():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")
    response = client.describe_organization()
    validate_organization(response)


@mock_organizations
def test_describe_organization_exception():
    client = boto3.client("organizations", region_name="us-east-1")
    with pytest.raises(ClientError) as e:
        client.describe_organization()
    ex = e.value
    ex.operation_name.should.equal("DescribeOrganization")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("AWSOrganizationsNotInUseException")
    ex.response["Error"]["Message"].should.equal(
        "Your account is not a member of an organization."
    )


# Organizational Units


@mock_organizations
def test_list_roots():
    client = boto3.client("organizations", region_name="us-east-1")
    org = client.create_organization(FeatureSet="ALL")["Organization"]
    response = client.list_roots()
    validate_roots(org, response)


@mock_organizations
def test_create_organizational_unit():
    client = boto3.client("organizations", region_name="us-east-1")
    org = client.create_organization(FeatureSet="ALL")["Organization"]
    root_id = client.list_roots()["Roots"][0]["Id"]
    ou_name = "ou01"
    response = client.create_organizational_unit(ParentId=root_id, Name=ou_name)
    validate_organizational_unit(org, response)
    response["OrganizationalUnit"]["Name"].should.equal(ou_name)


@mock_organizations
def test_describe_organizational_unit():
    client = boto3.client("organizations", region_name="us-east-1")
    org = client.create_organization(FeatureSet="ALL")["Organization"]
    root_id = client.list_roots()["Roots"][0]["Id"]
    ou_id = client.create_organizational_unit(ParentId=root_id, Name="ou01")[
        "OrganizationalUnit"
    ]["Id"]
    response = client.describe_organizational_unit(OrganizationalUnitId=ou_id)
    validate_organizational_unit(org, response)


@mock_organizations
def test_describe_organizational_unit_exception():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")["Organization"]
    with pytest.raises(ClientError) as e:
        client.describe_organizational_unit(
            OrganizationalUnitId=utils.make_random_root_id()
        )
    ex = e.value
    ex.operation_name.should.equal("DescribeOrganizationalUnit")
    ex.response["Error"]["Code"].should.equal("400")
    ex.response["Error"]["Message"].should.contain(
        "OrganizationalUnitNotFoundException"
    )


@mock_organizations
def test_list_organizational_units_for_parent():
    client = boto3.client("organizations", region_name="us-east-1")
    org = client.create_organization(FeatureSet="ALL")["Organization"]
    root_id = client.list_roots()["Roots"][0]["Id"]
    client.create_organizational_unit(ParentId=root_id, Name="ou01")
    client.create_organizational_unit(ParentId=root_id, Name="ou02")
    client.create_organizational_unit(ParentId=root_id, Name="ou03")
    response = client.list_organizational_units_for_parent(ParentId=root_id)
    response.should.have.key("OrganizationalUnits").should.be.a(list)
    for ou in response["OrganizationalUnits"]:
        validate_organizational_unit(org, dict(OrganizationalUnit=ou))


@mock_organizations
def test_list_organizational_units_pagination():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")
    root_id = client.list_roots()["Roots"][0]["Id"]
    for i in range(20):
        name = "ou" + str(i)
        client.create_organizational_unit(ParentId=root_id, Name=name)
    response = client.list_organizational_units_for_parent(ParentId=root_id)
    response.should_not.have.key("NextToken")
    len(response["OrganizationalUnits"]).should.be.greater_than_or_equal_to(i)

    paginator = client.get_paginator("list_organizational_units_for_parent")
    page_iterator = paginator.paginate(MaxResults=5, ParentId=root_id)
    for page in page_iterator:
        len(page["OrganizationalUnits"]).should.be.lower_than_or_equal_to(5)
    page["OrganizationalUnits"][-1]["Name"].should.contain("19")


@mock_organizations
def test_list_organizational_units_for_parent_exception():
    client = boto3.client("organizations", region_name="us-east-1")
    with pytest.raises(ClientError) as e:
        client.list_organizational_units_for_parent(
            ParentId=utils.make_random_root_id()
        )
    ex = e.value
    ex.operation_name.should.equal("ListOrganizationalUnitsForParent")
    ex.response["Error"]["Code"].should.equal("400")
    ex.response["Error"]["Message"].should.contain("ParentNotFoundException")


# Accounts
mockname = "mock-account"
mockdomain = "moto-example.org"
mockemail = "@".join([mockname, mockdomain])


@mock_organizations
def test_create_account():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")
    create_status = client.create_account(AccountName=mockname, Email=mockemail)[
        "CreateAccountStatus"
    ]
    validate_create_account_status(create_status)
    create_status["AccountName"].should.equal(mockname)


@mock_organizations
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


@mock_organizations
def test_close_account_puts_account_in_suspended_status():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")
    create_status = client.create_account(AccountName=mockname, Email=mockemail)[
        "CreateAccountStatus"
    ]
    created_account_id = create_status["AccountId"]

    client.close_account(AccountId=created_account_id)

    account = client.describe_account(AccountId=created_account_id)["Account"]
    account["Status"].should.equal("SUSPENDED")


@mock_organizations
def test_close_account_id_not_in_org_raises_exception():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")
    uncreated_fake_account_id = "123456789101"

    with pytest.raises(ClientError) as e:
        client.close_account(AccountId=uncreated_fake_account_id)
    ex = e.value
    ex.operation_name.should.equal("CloseAccount")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("AccountNotFoundException")
    ex.response["Error"]["Message"].should.equal(
        "You specified an account that doesn't exist."
    )


@mock_organizations
def test_describe_create_account_status():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")["Organization"]
    request_id = client.create_account(AccountName=mockname, Email=mockemail)[
        "CreateAccountStatus"
    ]["Id"]
    response = client.describe_create_account_status(CreateAccountRequestId=request_id)
    validate_create_account_status(response["CreateAccountStatus"])


@mock_organizations
def test_describe_account():
    client = boto3.client("organizations", region_name="us-east-1")
    org = client.create_organization(FeatureSet="ALL")["Organization"]
    account_id = client.create_account(AccountName=mockname, Email=mockemail)[
        "CreateAccountStatus"
    ]["AccountId"]
    response = client.describe_account(AccountId=account_id)
    validate_account(org, response["Account"])
    response["Account"]["Name"].should.equal(mockname)
    response["Account"]["Email"].should.equal(mockemail)


@mock_organizations
def test_describe_account_exception():
    client = boto3.client("organizations", region_name="us-east-1")
    with pytest.raises(ClientError) as e:
        client.describe_account(AccountId=utils.make_random_account_id())
    ex = e.value
    ex.operation_name.should.equal("DescribeAccount")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("AccountNotFoundException")
    ex.response["Error"]["Message"].should.equal(
        "You specified an account that doesn't exist."
    )


@mock_organizations
def test_list_accounts():
    client = boto3.client("organizations", region_name="us-east-1")
    org = client.create_organization(FeatureSet="ALL")["Organization"]
    for i in range(5):
        name = mockname + str(i)
        email = name + "@" + mockdomain
        client.create_account(AccountName=name, Email=email)
    response = client.list_accounts()
    response.should.have.key("Accounts")
    accounts = response["Accounts"]
    len(accounts).should.equal(6)
    for account in accounts:
        validate_account(org, account)
    accounts[4]["Name"].should.equal(mockname + "3")
    accounts[3]["Email"].should.equal(mockname + "2" + "@" + mockdomain)


@mock_organizations
def test_list_accounts_pagination():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")
    for i in range(25):
        name = mockname + str(i)
        email = name + "@" + mockdomain
        client.create_account(AccountName=name, Email=email)
    response = client.list_accounts()
    response.should_not.have.key("NextToken")
    len(response["Accounts"]).should.be.greater_than_or_equal_to(i)

    paginator = client.get_paginator("list_accounts")
    page_iterator = paginator.paginate(MaxResults=5)
    for page in page_iterator:
        len(page["Accounts"]).should.be.lower_than_or_equal_to(5)
    page["Accounts"][-1]["Name"].should.contain("24")


@mock_organizations
def test_list_accounts_for_parent():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")["Organization"]
    root_id = client.list_roots()["Roots"][0]["Id"]
    account_id = client.create_account(AccountName=mockname, Email=mockemail)[
        "CreateAccountStatus"
    ]["AccountId"]
    response = client.list_accounts_for_parent(ParentId=root_id)
    account_id.should.be.within([account["Id"] for account in response["Accounts"]])


@mock_organizations
def test_list_accounts_for_parent_pagination():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")
    root_id = client.list_roots()["Roots"][0]["Id"]
    response = client.list_accounts_for_parent(ParentId=root_id)
    response.should_not.have.key("NextToken")
    num_existing_accounts = len(response["Accounts"])
    for i in range(num_existing_accounts, 21):
        name = mockname + str(i)
        email = name + "@" + mockdomain
        client.create_account(AccountName=name, Email=email)
    response = client.list_accounts_for_parent(ParentId=root_id)
    len(response["Accounts"]).should.be.greater_than_or_equal_to(i)

    paginator = client.get_paginator("list_accounts_for_parent")
    page_iterator = paginator.paginate(MaxResults=5, ParentId=root_id)
    for page in page_iterator:
        len(page["Accounts"]).should.be.lower_than_or_equal_to(5)
    page["Accounts"][-1]["Name"].should.contain("20")


@mock_organizations
def test_move_account():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")["Organization"]
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
    account_id.should.be.within([account["Id"] for account in response["Accounts"]])


@mock_organizations
def test_list_parents_for_ou():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")["Organization"]
    root_id = client.list_roots()["Roots"][0]["Id"]
    ou01 = client.create_organizational_unit(ParentId=root_id, Name="ou01")
    ou01_id = ou01["OrganizationalUnit"]["Id"]
    response01 = client.list_parents(ChildId=ou01_id)
    response01.should.have.key("Parents").should.be.a(list)
    response01["Parents"][0].should.have.key("Id").should.equal(root_id)
    response01["Parents"][0].should.have.key("Type").should.equal("ROOT")
    ou02 = client.create_organizational_unit(ParentId=ou01_id, Name="ou02")
    ou02_id = ou02["OrganizationalUnit"]["Id"]
    response02 = client.list_parents(ChildId=ou02_id)
    response02.should.have.key("Parents").should.be.a(list)
    response02["Parents"][0].should.have.key("Id").should.equal(ou01_id)
    response02["Parents"][0].should.have.key("Type").should.equal("ORGANIZATIONAL_UNIT")


@mock_organizations
def test_list_parents_for_accounts():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")["Organization"]
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
    response01.should.have.key("Parents").should.be.a(list)
    response01["Parents"][0].should.have.key("Id").should.equal(root_id)
    response01["Parents"][0].should.have.key("Type").should.equal("ROOT")
    response02 = client.list_parents(ChildId=account02_id)
    response02.should.have.key("Parents").should.be.a(list)
    response02["Parents"][0].should.have.key("Id").should.equal(ou01_id)
    response02["Parents"][0].should.have.key("Type").should.equal("ORGANIZATIONAL_UNIT")


@mock_organizations
def test_list_children():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")["Organization"]
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
    response01["Children"][0]["Id"].should.equal(ACCOUNT_ID)
    response01["Children"][0]["Type"].should.equal("ACCOUNT")
    response01["Children"][1]["Id"].should.equal(account01_id)
    response01["Children"][1]["Type"].should.equal("ACCOUNT")
    response02["Children"][0]["Id"].should.equal(ou01_id)
    response02["Children"][0]["Type"].should.equal("ORGANIZATIONAL_UNIT")
    response03["Children"][0]["Id"].should.equal(account02_id)
    response03["Children"][0]["Type"].should.equal("ACCOUNT")
    response04["Children"][0]["Id"].should.equal(ou02_id)
    response04["Children"][0]["Type"].should.equal("ORGANIZATIONAL_UNIT")


@mock_organizations
def test_list_children_exception():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")["Organization"]
    root_id = client.list_roots()["Roots"][0]["Id"]
    with pytest.raises(ClientError) as e:
        client.list_children(ParentId=utils.make_random_root_id(), ChildType="ACCOUNT")
    ex = e.value
    ex.operation_name.should.equal("ListChildren")
    ex.response["Error"]["Code"].should.equal("400")
    ex.response["Error"]["Message"].should.contain("ParentNotFoundException")
    with pytest.raises(ClientError) as e:
        client.list_children(ParentId=root_id, ChildType="BLEE")
    ex = e.value
    ex.operation_name.should.equal("ListChildren")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("InvalidInputException")
    ex.response["Error"]["Message"].should.equal("You specified an invalid value.")


@mock_organizations
def test_list_create_account_status():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")["Organization"]
    response = client.list_create_account_status()
    createAccountStatuses = response["CreateAccountStatuses"]
    createAccountStatuses.should.have.length_of(1)
    validate_create_account_status(createAccountStatuses[0])

    client.create_account(AccountName=mockname, Email=mockemail)["CreateAccountStatus"][
        "Id"
    ]
    response = client.list_create_account_status()
    createAccountStatuses = response["CreateAccountStatuses"]
    createAccountStatuses.should.have.length_of(2)
    for createAccountStatus in createAccountStatuses:
        validate_create_account_status(createAccountStatus)


@mock_organizations
def test_list_create_account_status_succeeded():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")["Organization"]
    requiredStates = ["SUCCEEDED"]
    response = client.list_create_account_status(States=requiredStates)
    createAccountStatuses = response["CreateAccountStatuses"]
    createAccountStatuses.should.have.length_of(1)
    validate_create_account_status(createAccountStatuses[0])


@mock_organizations
def test_list_create_account_status_in_progress():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")["Organization"]
    requiredStates = ["IN_PROGRESS"]
    response = client.list_create_account_status(States=requiredStates)
    createAccountStatuses = response["CreateAccountStatuses"]
    createAccountStatuses.should.have.length_of(0)


@mock_organizations
def test_get_paginated_list_create_account_status():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")["Organization"]
    for _ in range(5):
        client.create_account(AccountName=mockname, Email=mockemail)[
            "CreateAccountStatus"
        ]["Id"]
    response = client.list_create_account_status(MaxResults=2)
    createAccountStatuses = response["CreateAccountStatuses"]
    createAccountStatuses.should.have.length_of(2)
    for createAccountStatus in createAccountStatuses:
        validate_create_account_status(createAccountStatus)
    next_token = response["NextToken"]
    next_token.should_not.equal(None)
    response2 = client.list_create_account_status(NextToken=next_token)
    createAccountStatuses.extend(response2["CreateAccountStatuses"])
    createAccountStatuses.should.have.length_of(6)
    assert "NextToken" not in response2.keys()
    for createAccountStatus in createAccountStatuses:
        validate_create_account_status(createAccountStatus)


@mock_organizations
def test_remove_account_from_organization():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")["Organization"]
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


@mock_organizations
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
policy_doc01 = dict(
    Version="2012-10-17",
    Statement=[
        dict(Sid="MockPolicyStatement", Effect="Allow", Action="s3:*", Resource="*")
    ],
)


@mock_organizations
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
    policy["PolicySummary"]["Name"].should.equal("MockServiceControlPolicy")
    policy["PolicySummary"]["Description"].should.equal(
        "A dummy service control policy"
    )
    policy["Content"].should.equal(json.dumps(policy_doc01))


@mock_organizations
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
    ex.operation_name.should.equal("CreatePolicy")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("InvalidInputException")
    ex.response["Error"]["Message"].should.equal("You specified an invalid value.")


@mock_organizations
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
    policy["PolicySummary"]["Name"].should.equal("MockServiceControlPolicy")
    policy["PolicySummary"]["Description"].should.equal(
        "A dummy service control policy"
    )
    policy["Content"].should.equal(json.dumps(policy_doc01))


@mock_organizations
def test_describe_policy_exception():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")["Organization"]
    policy_id = "p-47fhe9s3"
    with pytest.raises(ClientError) as e:
        client.describe_policy(PolicyId=policy_id)
    ex = e.value
    ex.operation_name.should.equal("DescribePolicy")
    ex.response["Error"]["Code"].should.equal("400")
    ex.response["Error"]["Message"].should.contain("PolicyNotFoundException")
    with pytest.raises(ClientError) as e:
        client.describe_policy(PolicyId="meaninglessstring")
    ex = e.value
    ex.operation_name.should.equal("DescribePolicy")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("InvalidInputException")
    ex.response["Error"]["Message"].should.equal("You specified an invalid value.")


@mock_organizations
def test_attach_policy():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")["Organization"]
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
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    response = client.attach_policy(PolicyId=policy_id, TargetId=ou_id)
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    response = client.attach_policy(PolicyId=policy_id, TargetId=account_id)
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)


@mock_organizations
def test_detach_policy():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")["Organization"]
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
        with sure.ensure("We should start with 0 policies"):
            get_nonaws_policies(target, client).should.have.length_of(0)
        #
        client.attach_policy(PolicyId=policy_id, TargetId=target)
        with sure.ensure("Expecting 1 policy after creation of target={0}", name):
            get_nonaws_policies(target, client).should.have.length_of(1)
        #
        response = client.detach_policy(PolicyId=policy_id, TargetId=target)
        response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
        with sure.ensure("Expecting 0 policies after deletion of target={0}", name):
            get_nonaws_policies(target, client).should.have.length_of(0)


def get_nonaws_policies(account_id, client):
    return [
        p
        for p in client.list_policies_for_target(
            TargetId=account_id, Filter="SERVICE_CONTROL_POLICY"
        )["Policies"]
        if not p["AwsManaged"]
    ]


@mock_organizations
def test_detach_policy_root_ou_not_found_exception():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")["Organization"]
    root_id = client.list_roots()["Roots"][0]["Id"]
    client.create_organizational_unit(ParentId=root_id, Name="ou01")[
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
    ex.operation_name.should.equal("DetachPolicy")
    ex.response["Error"]["Code"].should.equal("400")
    ex.response["Error"]["Message"].should.contain(
        "OrganizationalUnitNotFoundException"
    )


@mock_organizations
def test_detach_policy_ou_not_found_exception():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")["Organization"]
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
    ex.operation_name.should.equal("DetachPolicy")
    ex.response["Error"]["Code"].should.equal("400")
    ex.response["Error"]["Message"].should.contain(
        "OrganizationalUnitNotFoundException"
    )


@mock_organizations
def test_detach_policy_account_id_not_found_exception():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")["Organization"]
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
    ex.operation_name.should.equal("DetachPolicy")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("AccountNotFoundException")
    ex.response["Error"]["Message"].should.equal(
        "You specified an account that doesn't exist."
    )


@mock_organizations
def test_detach_policy_invalid_target_exception():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")["Organization"]
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
    ex.operation_name.should.equal("DetachPolicy")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("InvalidInputException")
    ex.response["Error"]["Message"].should.equal("You specified an invalid value.")


@mock_organizations
def test_delete_policy():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")["Organization"]
    base_policies = client.list_policies(Filter="SERVICE_CONTROL_POLICY")["Policies"]
    base_policies.should.have.length_of(1)
    policy_id = client.create_policy(
        Content=json.dumps(policy_doc01),
        Description="A dummy service control policy",
        Name="MockServiceControlPolicy",
        Type="SERVICE_CONTROL_POLICY",
    )["Policy"]["PolicySummary"]["Id"]
    new_policies = client.list_policies(Filter="SERVICE_CONTROL_POLICY")["Policies"]
    new_policies.should.have.length_of(2)
    response = client.delete_policy(PolicyId=policy_id)
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    new_policies = client.list_policies(Filter="SERVICE_CONTROL_POLICY")["Policies"]
    new_policies.should.equal(base_policies)
    new_policies.should.have.length_of(1)


@mock_organizations
def test_delete_policy_exception():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")["Organization"]
    non_existent_policy_id = utils.make_random_policy_id()
    with pytest.raises(ClientError) as e:
        client.delete_policy(PolicyId=non_existent_policy_id)
    ex = e.value
    ex.operation_name.should.equal("DeletePolicy")
    ex.response["Error"]["Code"].should.equal("400")
    ex.response["Error"]["Message"].should.contain("PolicyNotFoundException")

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
    ex.operation_name.should.equal("DeletePolicy")
    ex.response["Error"]["Code"].should.equal("400")
    ex.response["Error"]["Message"].should.contain("PolicyInUseException")


@mock_organizations
def test_attach_policy_exception():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")["Organization"]
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
    ex.operation_name.should.equal("AttachPolicy")
    ex.response["Error"]["Code"].should.equal("400")
    ex.response["Error"]["Message"].should.contain(
        "OrganizationalUnitNotFoundException"
    )
    with pytest.raises(ClientError) as e:
        client.attach_policy(PolicyId=policy_id, TargetId=ou_id)
    ex = e.value
    ex.operation_name.should.equal("AttachPolicy")
    ex.response["Error"]["Code"].should.equal("400")
    ex.response["Error"]["Message"].should.contain(
        "OrganizationalUnitNotFoundException"
    )
    with pytest.raises(ClientError) as e:
        client.attach_policy(PolicyId=policy_id, TargetId=account_id)
    ex = e.value
    ex.operation_name.should.equal("AttachPolicy")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("AccountNotFoundException")
    ex.response["Error"]["Message"].should.equal(
        "You specified an account that doesn't exist."
    )
    with pytest.raises(ClientError) as e:
        client.attach_policy(PolicyId=policy_id, TargetId="meaninglessstring")
    ex = e.value
    ex.operation_name.should.equal("AttachPolicy")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("InvalidInputException")
    ex.response["Error"]["Message"].should.equal("You specified an invalid value.")


@mock_organizations
def test_update_policy():
    client = boto3.client("organizations", region_name="us-east-1")
    org = client.create_organization(FeatureSet="ALL")["Organization"]

    policy_dict = dict(
        Content=json.dumps(policy_doc01),
        Description="A dummy service control policy",
        Name="MockServiceControlPolicy",
        Type="SERVICE_CONTROL_POLICY",
    )
    policy_id = client.create_policy(**policy_dict)["Policy"]["PolicySummary"]["Id"]

    for key in ("Description", "Name"):
        response = client.update_policy(**{"PolicyId": policy_id, key: "foobar"})
        policy = client.describe_policy(PolicyId=policy_id)
        policy["Policy"]["PolicySummary"][key].should.equal("foobar")
        validate_service_control_policy(org, response["Policy"])

    response = client.update_policy(PolicyId=policy_id, Content="foobar")
    policy = client.describe_policy(PolicyId=policy_id)
    policy["Policy"]["Content"].should.equal("foobar")
    validate_service_control_policy(org, response["Policy"])


@mock_organizations
def test_update_policy_exception():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")["Organization"]
    non_existent_policy_id = utils.make_random_policy_id()
    with pytest.raises(ClientError) as e:
        client.update_policy(PolicyId=non_existent_policy_id)
    ex = e.value
    ex.operation_name.should.equal("UpdatePolicy")
    ex.response["Error"]["Code"].should.equal("400")
    ex.response["Error"]["Message"].should.contain("PolicyNotFoundException")


@mock_organizations
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


@mock_organizations
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


@mock_organizations
def test_list_policies_for_target_exception():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")["Organization"]
    root_id = client.list_roots()["Roots"][0]["Id"]
    ou_id = "ou-gi99-i7r8eh2i2"
    account_id = "126644886543"
    with pytest.raises(ClientError) as e:
        client.list_policies_for_target(TargetId=ou_id, Filter="SERVICE_CONTROL_POLICY")
    ex = e.value
    ex.operation_name.should.equal("ListPoliciesForTarget")
    ex.response["Error"]["Code"].should.equal("400")
    ex.response["Error"]["Message"].should.contain(
        "OrganizationalUnitNotFoundException"
    )
    with pytest.raises(ClientError) as e:
        client.list_policies_for_target(
            TargetId=account_id, Filter="SERVICE_CONTROL_POLICY"
        )
    ex = e.value
    ex.operation_name.should.equal("ListPoliciesForTarget")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("AccountNotFoundException")
    ex.response["Error"]["Message"].should.equal(
        "You specified an account that doesn't exist."
    )
    with pytest.raises(ClientError) as e:
        client.list_policies_for_target(
            TargetId="meaninglessstring", Filter="SERVICE_CONTROL_POLICY"
        )
    ex = e.value
    ex.operation_name.should.equal("ListPoliciesForTarget")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("InvalidInputException")
    ex.response["Error"]["Message"].should.equal("You specified an invalid value.")

    # not existing root
    # when
    with pytest.raises(ClientError) as e:
        client.list_policies_for_target(
            TargetId="r-0000", Filter="SERVICE_CONTROL_POLICY"
        )

    # then
    ex = e.value
    ex.operation_name.should.equal("ListPoliciesForTarget")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("TargetNotFoundException")
    ex.response["Error"]["Message"].should.equal(
        "You specified a target that doesn't exist."
    )

    # invalid policy type
    # when
    with pytest.raises(ClientError) as e:
        client.list_policies_for_target(TargetId=root_id, Filter="MOTO")

    # then
    ex = e.value
    ex.operation_name.should.equal("ListPoliciesForTarget")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("InvalidInputException")
    ex.response["Error"]["Message"].should.equal("You specified an invalid value.")


@mock_organizations
def test_list_targets_for_policy():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")["Organization"]
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
        target.should.be.a(dict)
        target.should.have.key("Name").should.be.a(str)
        target.should.have.key("Arn").should.be.a(str)
        target.should.have.key("TargetId").should.be.a(str)
        target.should.have.key("Type").should.be.within(
            ["ROOT", "ORGANIZATIONAL_UNIT", "ACCOUNT"]
        )


@mock_organizations
def test_list_targets_for_policy_exception():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")["Organization"]
    policy_id = "p-47fhe9s3"
    with pytest.raises(ClientError) as e:
        client.list_targets_for_policy(PolicyId=policy_id)
    ex = e.value
    ex.operation_name.should.equal("ListTargetsForPolicy")
    ex.response["Error"]["Code"].should.equal("400")
    ex.response["Error"]["Message"].should.contain("PolicyNotFoundException")
    with pytest.raises(ClientError) as e:
        client.list_targets_for_policy(PolicyId="meaninglessstring")
    ex = e.value
    ex.operation_name.should.equal("ListTargetsForPolicy")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("InvalidInputException")
    ex.response["Error"]["Message"].should.equal("You specified an invalid value.")


@mock_organizations
def test_tag_resource_account():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")
    resource_id = client.create_account(AccountName=mockname, Email=mockemail)[
        "CreateAccountStatus"
    ]["AccountId"]

    client.tag_resource(ResourceId=resource_id, Tags=[{"Key": "key", "Value": "value"}])

    response = client.list_tags_for_resource(ResourceId=resource_id)
    response["Tags"].should.equal([{"Key": "key", "Value": "value"}])

    # adding a tag with an existing key, will update the value
    client.tag_resource(
        ResourceId=resource_id, Tags=[{"Key": "key", "Value": "new-value"}]
    )

    response = client.list_tags_for_resource(ResourceId=resource_id)
    response["Tags"].should.equal([{"Key": "key", "Value": "new-value"}])

    client.untag_resource(ResourceId=resource_id, TagKeys=["key"])

    response = client.list_tags_for_resource(ResourceId=resource_id)
    response["Tags"].should.equal([])


@mock_organizations
def test_tag_resource_organization_organization_root():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")

    resource_id = client.list_roots()["Roots"][0]["Id"]
    client.tag_resource(ResourceId=resource_id, Tags=[{"Key": "key", "Value": "value"}])

    response = client.list_tags_for_resource(ResourceId=resource_id)
    response["Tags"].should.equal([{"Key": "key", "Value": "value"}])

    # adding a tag with an existing key, will update the value
    client.tag_resource(
        ResourceId=resource_id, Tags=[{"Key": "key", "Value": "new-value"}]
    )

    response = client.list_tags_for_resource(ResourceId=resource_id)
    response["Tags"].should.equal([{"Key": "key", "Value": "new-value"}])

    client.untag_resource(ResourceId=resource_id, TagKeys=["key"])

    response = client.list_tags_for_resource(ResourceId=resource_id)
    response["Tags"].should.equal([])


@mock_organizations
def test_tag_resource_organization_organizational_unit():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")
    root_id = client.list_roots()["Roots"][0]["Id"]
    resource_id = client.create_organizational_unit(ParentId=root_id, Name="ou01")[
        "OrganizationalUnit"
    ]["Id"]

    client.tag_resource(ResourceId=resource_id, Tags=[{"Key": "key", "Value": "value"}])

    response = client.list_tags_for_resource(ResourceId=resource_id)
    response["Tags"].should.equal([{"Key": "key", "Value": "value"}])

    # adding a tag with an existing key, will update the value
    client.tag_resource(
        ResourceId=resource_id, Tags=[{"Key": "key", "Value": "new-value"}]
    )

    response = client.list_tags_for_resource(ResourceId=resource_id)
    response["Tags"].should.equal([{"Key": "key", "Value": "new-value"}])

    client.untag_resource(ResourceId=resource_id, TagKeys=["key"])

    response = client.list_tags_for_resource(ResourceId=resource_id)
    response["Tags"].should.equal([])


@mock_organizations
def test_tag_resource_errors():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")

    with pytest.raises(ClientError) as e:
        client.tag_resource(
            ResourceId="0A000000X000", Tags=[{"Key": "key", "Value": "value"}]
        )
    ex = e.value
    ex.operation_name.should.equal("TagResource")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("InvalidInputException")
    ex.response["Error"]["Message"].should.equal(
        "You provided a value that does not match the required pattern."
    )
    with pytest.raises(ClientError) as e:
        client.tag_resource(
            ResourceId="000000000000", Tags=[{"Key": "key", "Value": "value"}]
        )
    ex = e.value
    ex.operation_name.should.equal("TagResource")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("TargetNotFoundException")
    ex.response["Error"]["Message"].should.equal(
        "You specified a target that doesn't exist."
    )


def test__get_resource_for_tagging_existing_root():
    org = FakeOrganization(ACCOUNT_ID, "ALL")
    root = FakeRoot(org)

    org_backend = OrganizationsBackend(region_name="N/A", account_id="N/A")
    org_backend.ou.append(root)
    response = org_backend._get_resource_for_tagging(root.id)
    response.id.should.equal(root.id)


def test__get_resource_for_tagging_existing_non_root():
    org_backend = OrganizationsBackend(region_name="N/A", account_id="N/A")
    with pytest.raises(TargetNotFoundException) as e:
        org_backend._get_resource_for_tagging("r-abcd")
    ex = e.value
    ex.code.should.equal(400)
    ex.description.should.contain("TargetNotFoundException")
    ex.message.should.equal("You specified a target that doesn't exist.")


def test__get_resource_for_tagging_existing_ou():
    org = FakeOrganization(ACCOUNT_ID, "ALL")
    ou = FakeOrganizationalUnit(org)
    org_backend = OrganizationsBackend(region_name="N/A", account_id="N/A")

    org_backend.ou.append(ou)
    response = org_backend._get_resource_for_tagging(ou.id)
    response.id.should.equal(ou.id)


def test__get_resource_for_tagging_non_existing_ou():
    org_backend = OrganizationsBackend(region_name="N/A", account_id="N/A")
    with pytest.raises(TargetNotFoundException) as e:
        org_backend._get_resource_for_tagging("ou-9oyc-lv2q36ln")
    ex = e.value
    ex.code.should.equal(400)
    ex.description.should.contain("TargetNotFoundException")
    ex.message.should.equal("You specified a target that doesn't exist.")


def test__get_resource_for_tagging_existing_account():
    org = FakeOrganization(ACCOUNT_ID, "ALL")
    org_backend = OrganizationsBackend(region_name="N/A", account_id="N/A")
    account = FakeAccount(org, AccountName="test", Email="test@test.test")

    org_backend.accounts.append(account)
    response = org_backend._get_resource_for_tagging(account.id)
    response.id.should.equal(account.id)


def test__get_resource_for_tagging_non_existing_account():
    org_backend = OrganizationsBackend(region_name="N/A", account_id="N/A")
    with pytest.raises(TargetNotFoundException) as e:
        org_backend._get_resource_for_tagging("100326223992")
    ex = e.value
    ex.code.should.equal(400)
    ex.description.should.contain("TargetNotFoundException")
    ex.message.should.equal("You specified a target that doesn't exist.")


def test__get_resource_for_tagging_existing_policy():
    org = FakeOrganization(ACCOUNT_ID, "ALL")
    org_backend = OrganizationsBackend(region_name="N/A", account_id="N/A")
    policy = FakePolicy(org, Type="SERVICE_CONTROL_POLICY")

    org_backend.policies.append(policy)
    response = org_backend._get_resource_for_tagging(policy.id)
    response.id.should.equal(policy.id)


def test__get_resource_for_tagging_non_existing_policy():
    org_backend = OrganizationsBackend(region_name="N/A", account_id="N/A")
    with pytest.raises(TargetNotFoundException) as e:
        org_backend._get_resource_for_tagging("p-y1vas4da")
    ex = e.value
    ex.code.should.equal(400)
    ex.description.should.contain("TargetNotFoundException")
    ex.message.should.equal("You specified a target that doesn't exist.")


def test__get_resource_to_tag_incorrect_resource():
    org_backend = OrganizationsBackend(region_name="N/A", account_id="N/A")
    with pytest.raises(InvalidInputException) as e:
        org_backend._get_resource_for_tagging("10032622399200")
    ex = e.value
    ex.code.should.equal(400)
    ex.description.should.contain("InvalidInputException")
    ex.message.should.equal(
        "You provided a value that does not match the required pattern."
    )


@mock_organizations
def test_list_tags_for_resource():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")
    account_id = client.create_account(AccountName=mockname, Email=mockemail)[
        "CreateAccountStatus"
    ]["AccountId"]
    client.tag_resource(ResourceId=account_id, Tags=[{"Key": "key", "Value": "value"}])

    response = client.list_tags_for_resource(ResourceId=account_id)

    response["Tags"].should.equal([{"Key": "key", "Value": "value"}])


@mock_organizations
def test_list_tags_for_resource_errors():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")

    with pytest.raises(ClientError) as e:
        client.list_tags_for_resource(ResourceId="000x00000A00")
    ex = e.value
    ex.operation_name.should.equal("ListTagsForResource")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("InvalidInputException")
    ex.response["Error"]["Message"].should.equal(
        "You provided a value that does not match the required pattern."
    )
    with pytest.raises(ClientError) as e:
        client.list_tags_for_resource(ResourceId="000000000000")
    ex = e.value
    ex.operation_name.should.equal("ListTagsForResource")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("TargetNotFoundException")
    ex.response["Error"]["Message"].should.equal(
        "You specified a target that doesn't exist."
    )


@mock_organizations
def test_untag_resource():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")
    account_id = client.create_account(AccountName=mockname, Email=mockemail)[
        "CreateAccountStatus"
    ]["AccountId"]
    client.tag_resource(ResourceId=account_id, Tags=[{"Key": "key", "Value": "value"}])
    response = client.list_tags_for_resource(ResourceId=account_id)
    response["Tags"].should.equal([{"Key": "key", "Value": "value"}])

    # removing a non existing tag should not raise any error
    client.untag_resource(ResourceId=account_id, TagKeys=["not-existing"])
    response = client.list_tags_for_resource(ResourceId=account_id)
    response["Tags"].should.equal([{"Key": "key", "Value": "value"}])

    client.untag_resource(ResourceId=account_id, TagKeys=["key"])
    response = client.list_tags_for_resource(ResourceId=account_id)
    response["Tags"].should.have.length_of(0)


@mock_organizations
def test_untag_resource_errors():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")

    with pytest.raises(ClientError) as e:
        client.untag_resource(ResourceId="0X00000000A0", TagKeys=["key"])
    ex = e.value
    ex.operation_name.should.equal("UntagResource")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("InvalidInputException")
    ex.response["Error"]["Message"].should.equal(
        "You provided a value that does not match the required pattern."
    )
    with pytest.raises(ClientError) as e:
        client.untag_resource(ResourceId="000000000000", TagKeys=["key"])
    ex = e.value
    ex.operation_name.should.equal("UntagResource")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("TargetNotFoundException")
    ex.response["Error"]["Message"].should.equal(
        "You specified a target that doesn't exist."
    )


@mock_organizations
def test_update_organizational_unit():
    client = boto3.client("organizations", region_name="us-east-1")
    org = client.create_organization(FeatureSet="ALL")["Organization"]
    root_id = client.list_roots()["Roots"][0]["Id"]
    ou_name = "ou01"
    response = client.create_organizational_unit(ParentId=root_id, Name=ou_name)
    validate_organizational_unit(org, response)
    response["OrganizationalUnit"]["Name"].should.equal(ou_name)
    new_ou_name = "ou02"
    response = client.update_organizational_unit(
        OrganizationalUnitId=response["OrganizationalUnit"]["Id"], Name=new_ou_name
    )
    validate_organizational_unit(org, response)
    response["OrganizationalUnit"]["Name"].should.equal(new_ou_name)


@mock_organizations
def test_update_organizational_unit_duplicate_error():
    client = boto3.client("organizations", region_name="us-east-1")
    org = client.create_organization(FeatureSet="ALL")["Organization"]
    root_id = client.list_roots()["Roots"][0]["Id"]
    ou_name = "ou01"
    response = client.create_organizational_unit(ParentId=root_id, Name=ou_name)
    validate_organizational_unit(org, response)
    response["OrganizationalUnit"]["Name"].should.equal(ou_name)
    with pytest.raises(ClientError) as e:
        client.update_organizational_unit(
            OrganizationalUnitId=response["OrganizationalUnit"]["Id"], Name=ou_name
        )
    exc = e.value
    exc.operation_name.should.equal("UpdateOrganizationalUnit")
    exc.response["Error"]["Code"].should.contain("DuplicateOrganizationalUnitException")
    exc.response["Error"]["Message"].should.equal(
        "An OU with the same name already exists."
    )


@mock_organizations
def test_enable_aws_service_access():
    # given
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")

    # when
    client.enable_aws_service_access(ServicePrincipal="config.amazonaws.com")

    # then
    response = client.list_aws_service_access_for_organization()
    response["EnabledServicePrincipals"].should.have.length_of(1)
    service = response["EnabledServicePrincipals"][0]
    service["ServicePrincipal"].should.equal("config.amazonaws.com")
    date_enabled = service["DateEnabled"]
    date_enabled.should.be.a(datetime)

    # enabling the same service again should not result in any error or change
    # when
    client.enable_aws_service_access(ServicePrincipal="config.amazonaws.com")

    # then
    response = client.list_aws_service_access_for_organization()
    response["EnabledServicePrincipals"].should.have.length_of(1)
    service = response["EnabledServicePrincipals"][0]
    service["ServicePrincipal"].should.equal("config.amazonaws.com")
    service["DateEnabled"].should.equal(date_enabled)


@mock_organizations
def test_enable_aws_service_access_error():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")

    with pytest.raises(ClientError) as e:
        client.enable_aws_service_access(ServicePrincipal="moto.amazonaws.com")
    ex = e.value
    ex.operation_name.should.equal("EnableAWSServiceAccess")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("InvalidInputException")
    ex.response["Error"]["Message"].should.equal(
        "You specified an unrecognized service principal."
    )


@mock_organizations
def test_enable_multiple_aws_service_access():
    # given
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")
    client.enable_aws_service_access(ServicePrincipal="config.amazonaws.com")
    client.enable_aws_service_access(ServicePrincipal="ram.amazonaws.com")

    # when
    response = client.list_aws_service_access_for_organization()

    # then
    response["EnabledServicePrincipals"].should.have.length_of(2)
    services = sorted(
        response["EnabledServicePrincipals"], key=lambda i: i["ServicePrincipal"]
    )
    services[0]["ServicePrincipal"].should.equal("config.amazonaws.com")
    services[0]["DateEnabled"].should.be.a(datetime)
    services[1]["ServicePrincipal"].should.equal("ram.amazonaws.com")
    services[1]["DateEnabled"].should.be.a(datetime)


@mock_organizations
def test_disable_aws_service_access():
    # given
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")
    client.enable_aws_service_access(ServicePrincipal="config.amazonaws.com")

    # when
    client.disable_aws_service_access(ServicePrincipal="config.amazonaws.com")

    # then
    response = client.list_aws_service_access_for_organization()
    response["EnabledServicePrincipals"].should.have.length_of(0)

    # disabling the same service again should not result in any error
    # when
    client.disable_aws_service_access(ServicePrincipal="config.amazonaws.com")

    # then
    response = client.list_aws_service_access_for_organization()
    response["EnabledServicePrincipals"].should.have.length_of(0)


@mock_organizations
def test_disable_aws_service_access_errors():
    client = boto3.client("organizations", region_name="us-east-1")
    client.create_organization(FeatureSet="ALL")

    with pytest.raises(ClientError) as e:
        client.disable_aws_service_access(ServicePrincipal="moto.amazonaws.com")
    ex = e.value
    ex.operation_name.should.equal("DisableAWSServiceAccess")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("InvalidInputException")
    ex.response["Error"]["Message"].should.equal(
        "You specified an unrecognized service principal."
    )


@mock_organizations
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
    response["DelegatedAdministrators"].should.have.length_of(1)
    admin = response["DelegatedAdministrators"][0]
    admin["Id"].should.equal(account_id)
    admin["Arn"].should.equal(
        "arn:aws:organizations::{0}:account/{1}/{2}".format(
            ACCOUNT_ID, org_id, account_id
        )
    )
    admin["Email"].should.equal(mockemail)
    admin["Name"].should.equal(mockname)
    admin["Status"].should.equal("ACTIVE")
    admin["JoinedMethod"].should.equal("CREATED")
    admin["JoinedTimestamp"].should.be.a(datetime)
    admin["DelegationEnabledDate"].should.be.a(datetime)


@mock_organizations
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
    ex.operation_name.should.equal("RegisterDelegatedAdministrator")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("ConstraintViolationException")
    ex.response["Error"]["Message"].should.equal(
        "You cannot register master account/yourself as delegated administrator for your organization."
    )

    # register not existing Account
    # when
    with pytest.raises(ClientError) as e:
        client.register_delegated_administrator(
            AccountId="000000000000", ServicePrincipal="ssm.amazonaws.com"
        )

    # then
    ex = e.value
    ex.operation_name.should.equal("RegisterDelegatedAdministrator")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("AccountNotFoundException")
    ex.response["Error"]["Message"].should.equal(
        "You specified an account that doesn't exist."
    )

    # register not supported service
    # when
    with pytest.raises(ClientError) as e:
        client.register_delegated_administrator(
            AccountId=account_id, ServicePrincipal="moto.amazonaws.com"
        )

    # then
    ex = e.value
    ex.operation_name.should.equal("RegisterDelegatedAdministrator")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("InvalidInputException")
    ex.response["Error"]["Message"].should.equal(
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
    ex.operation_name.should.equal("RegisterDelegatedAdministrator")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("AccountAlreadyRegisteredException")
    ex.response["Error"]["Message"].should.equal(
        "The provided account is already a delegated administrator for your organization."
    )


@mock_organizations
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
    response["DelegatedAdministrators"].should.have.length_of(2)
    sorted([admin["Id"] for admin in response["DelegatedAdministrators"]]).should.equal(
        sorted([account_id_1, account_id_2])
    )

    # when
    response = client.list_delegated_administrators(
        ServicePrincipal="ssm.amazonaws.com"
    )

    # then
    response["DelegatedAdministrators"].should.have.length_of(1)
    admin = response["DelegatedAdministrators"][0]
    admin["Id"].should.equal(account_id_1)
    admin["Arn"].should.equal(
        "arn:aws:organizations::{0}:account/{1}/{2}".format(
            ACCOUNT_ID, org_id, account_id_1
        )
    )
    admin["Email"].should.equal(mockemail)
    admin["Name"].should.equal(mockname)
    admin["Status"].should.equal("ACTIVE")
    admin["JoinedMethod"].should.equal("CREATED")
    admin["JoinedTimestamp"].should.be.a(datetime)
    admin["DelegationEnabledDate"].should.be.a(datetime)


@mock_organizations
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
    ex.operation_name.should.equal("ListDelegatedAdministrators")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("InvalidInputException")
    ex.response["Error"]["Message"].should.equal(
        "You specified an unrecognized service principal."
    )


@mock_organizations
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
    response["DelegatedServices"].should.have.length_of(2)
    sorted(
        [service["ServicePrincipal"] for service in response["DelegatedServices"]]
    ).should.equal(["guardduty.amazonaws.com", "ssm.amazonaws.com"])


@mock_organizations
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
    ex.operation_name.should.equal("ListDelegatedServicesForAccount")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("AWSOrganizationsNotInUseException")
    ex.response["Error"]["Message"].should.equal(
        "Your account is not a member of an organization."
    )

    # list services for not registered Account
    # when
    with pytest.raises(ClientError) as e:
        client.list_delegated_services_for_account(AccountId=ACCOUNT_ID)

    # then
    ex = e.value
    ex.operation_name.should.equal("ListDelegatedServicesForAccount")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("AccountNotRegisteredException")
    ex.response["Error"]["Message"].should.equal(
        "The provided account is not a registered delegated administrator for your organization."
    )


@mock_organizations
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
    response["DelegatedAdministrators"].should.have.length_of(0)


@mock_organizations
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
    ex.operation_name.should.equal("DeregisterDelegatedAdministrator")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("ConstraintViolationException")
    ex.response["Error"]["Message"].should.equal(
        "You cannot register master account/yourself as delegated administrator for your organization."
    )

    # deregister not existing Account
    # when
    with pytest.raises(ClientError) as e:
        client.deregister_delegated_administrator(
            AccountId="000000000000", ServicePrincipal="ssm.amazonaws.com"
        )

    # then
    ex = e.value
    ex.operation_name.should.equal("DeregisterDelegatedAdministrator")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("AccountNotFoundException")
    ex.response["Error"]["Message"].should.equal(
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
    ex.operation_name.should.equal("DeregisterDelegatedAdministrator")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("AccountNotRegisteredException")
    ex.response["Error"]["Message"].should.equal(
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
    ex.operation_name.should.equal("DeregisterDelegatedAdministrator")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("InvalidInputException")
    ex.response["Error"]["Message"].should.equal(
        "You specified an unrecognized service principal."
    )


@mock_organizations
def test_enable_policy_type():
    # given
    client = boto3.client("organizations", region_name="us-east-1")
    org = client.create_organization(FeatureSet="ALL")["Organization"]
    root_id = client.list_roots()["Roots"][0]["Id"]

    # when
    response = client.enable_policy_type(
        RootId=root_id, PolicyType="AISERVICES_OPT_OUT_POLICY"
    )

    # then
    root = response["Root"]
    root["Id"].should.equal(root_id)
    root["Arn"].should.equal(
        utils.ROOT_ARN_FORMAT.format(org["MasterAccountId"], org["Id"], root_id)
    )
    root["Name"].should.equal("Root")
    sorted(root["PolicyTypes"], key=lambda x: x["Type"]).should.equal(
        [{"Type": "AISERVICES_OPT_OUT_POLICY", "Status": "ENABLED"}]
    )


@mock_organizations
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
    ex.operation_name.should.equal("EnablePolicyType")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("RootNotFoundException")
    ex.response["Error"]["Message"].should.equal(
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
    ex.operation_name.should.equal("EnablePolicyType")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("PolicyTypeAlreadyEnabledException")
    ex.response["Error"]["Message"].should.equal(
        "The specified policy type is already enabled."
    )

    # invalid policy type
    # when
    with pytest.raises(ClientError) as e:
        client.enable_policy_type(RootId=root_id, PolicyType="MOTO")

    # then
    ex = e.value
    ex.operation_name.should.equal("EnablePolicyType")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("InvalidInputException")
    ex.response["Error"]["Message"].should.equal("You specified an invalid value.")


@mock_organizations
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
    root["Id"].should.equal(root_id)
    root["Arn"].should.equal(
        utils.ROOT_ARN_FORMAT.format(org["MasterAccountId"], org["Id"], root_id)
    )
    root["Name"].should.equal("Root")
    root["PolicyTypes"].should.equal([])


@mock_organizations
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
    ex.operation_name.should.equal("DisablePolicyType")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("RootNotFoundException")
    ex.response["Error"]["Message"].should.equal(
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
    ex.operation_name.should.equal("DisablePolicyType")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("PolicyTypeNotEnabledException")
    ex.response["Error"]["Message"].should.equal(
        "This operation can be performed only for enabled policy types."
    )

    # invalid policy type
    # when
    with pytest.raises(ClientError) as e:
        client.disable_policy_type(RootId=root_id, PolicyType="MOTO")

    # then
    ex = e.value
    ex.operation_name.should.equal("DisablePolicyType")
    ex.response["ResponseMetadata"]["HTTPStatusCode"].should.equal(400)
    ex.response["Error"]["Code"].should.contain("InvalidInputException")
    ex.response["Error"]["Message"].should.equal("You specified an invalid value.")


@mock_organizations
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
    summary["Id"].should.match(utils.POLICY_ID_REGEX)
    summary["Arn"].should.equal(
        utils.AI_POLICY_ARN_FORMAT.format(
            org["MasterAccountId"], org["Id"], summary["Id"]
        )
    )
    summary["Name"].should.equal("ai-opt-out")
    summary["Description"].should.equal("Opt out of all AI services")
    summary["Type"].should.equal("AISERVICES_OPT_OUT_POLICY")
    summary["AwsManaged"].should.equal(False)
    json.loads(response["Policy"]["Content"]).should.equal(ai_policy)

    # when
    client.attach_policy(PolicyId=policy_id, TargetId=root_id)

    # then
    response = client.list_policies_for_target(
        TargetId=root_id, Filter="AISERVICES_OPT_OUT_POLICY"
    )
    response["Policies"].should.have.length_of(1)
    response["Policies"][0]["Id"].should.equal(policy_id)
