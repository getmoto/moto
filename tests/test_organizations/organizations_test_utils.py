from __future__ import unicode_literals

import datetime
from moto.organizations import utils


def test_make_random_org_id():
    org_id = utils.make_random_org_id()
    org_id.should.match(utils.ORG_ID_REGEX)


def test_make_random_root_id():
    root_id = utils.make_random_root_id()
    root_id.should.match(utils.ROOT_ID_REGEX)


def test_make_random_ou_id():
    root_id = utils.make_random_root_id()
    ou_id = utils.make_random_ou_id(root_id)
    ou_id.should.match(utils.OU_ID_REGEX)


def test_make_random_account_id():
    account_id = utils.make_random_account_id()
    account_id.should.match(utils.ACCOUNT_ID_REGEX)


def test_make_random_create_account_status_id():
    create_account_status_id = utils.make_random_create_account_status_id()
    create_account_status_id.should.match(utils.CREATE_ACCOUNT_STATUS_ID_REGEX)


def test_make_random_policy_id():
    policy_id = utils.make_random_policy_id()
    policy_id.should.match(utils.POLICY_ID_REGEX)


def validate_organization(response):
    org = response["Organization"]
    sorted(org.keys()).should.equal(
        [
            "Arn",
            "AvailablePolicyTypes",
            "FeatureSet",
            "Id",
            "MasterAccountArn",
            "MasterAccountEmail",
            "MasterAccountId",
        ]
    )
    org["Id"].should.match(utils.ORG_ID_REGEX)
    org["MasterAccountId"].should.equal(utils.MASTER_ACCOUNT_ID)
    org["MasterAccountArn"].should.equal(
        utils.MASTER_ACCOUNT_ARN_FORMAT.format(org["MasterAccountId"], org["Id"])
    )
    org["Arn"].should.equal(
        utils.ORGANIZATION_ARN_FORMAT.format(org["MasterAccountId"], org["Id"])
    )
    org["MasterAccountEmail"].should.equal(utils.MASTER_ACCOUNT_EMAIL)
    org["FeatureSet"].should.be.within(["ALL", "CONSOLIDATED_BILLING"])
    org["AvailablePolicyTypes"].should.equal(
        [{"Type": "SERVICE_CONTROL_POLICY", "Status": "ENABLED"}]
    )


def validate_roots(org, response):
    response.should.have.key("Roots").should.be.a(list)
    response["Roots"].should_not.be.empty
    root = response["Roots"][0]
    root.should.have.key("Id").should.match(utils.ROOT_ID_REGEX)
    root.should.have.key("Arn").should.equal(
        utils.ROOT_ARN_FORMAT.format(org["MasterAccountId"], org["Id"], root["Id"])
    )
    root.should.have.key("Name").should.be.a(str)
    root.should.have.key("PolicyTypes").should.be.a(list)
    root["PolicyTypes"][0].should.have.key("Type").should.equal(
        "SERVICE_CONTROL_POLICY"
    )
    root["PolicyTypes"][0].should.have.key("Status").should.equal("ENABLED")


def validate_organizational_unit(org, response):
    response.should.have.key("OrganizationalUnit").should.be.a(dict)
    ou = response["OrganizationalUnit"]
    ou.should.have.key("Id").should.match(utils.OU_ID_REGEX)
    ou.should.have.key("Arn").should.equal(
        utils.OU_ARN_FORMAT.format(org["MasterAccountId"], org["Id"], ou["Id"])
    )
    ou.should.have.key("Name").should.be.a(str)


def validate_account(org, account):
    sorted(account.keys()).should.equal(
        ["Arn", "Email", "Id", "JoinedMethod", "JoinedTimestamp", "Name", "Status"]
    )
    account["Id"].should.match(utils.ACCOUNT_ID_REGEX)
    account["Arn"].should.equal(
        utils.ACCOUNT_ARN_FORMAT.format(
            org["MasterAccountId"], org["Id"], account["Id"]
        )
    )
    account["Email"].should.match(utils.EMAIL_REGEX)
    account["JoinedMethod"].should.be.within(["INVITED", "CREATED"])
    account["Status"].should.be.within(["ACTIVE", "SUSPENDED"])
    account["Name"].should.be.a(str)
    account["JoinedTimestamp"].should.be.a(datetime.datetime)


def validate_create_account_status(create_status):
    sorted(create_status.keys()).should.equal(
        [
            "AccountId",
            "AccountName",
            "CompletedTimestamp",
            "Id",
            "RequestedTimestamp",
            "State",
        ]
    )
    create_status["Id"].should.match(utils.CREATE_ACCOUNT_STATUS_ID_REGEX)
    create_status["AccountId"].should.match(utils.ACCOUNT_ID_REGEX)
    create_status["AccountName"].should.be.a(str)
    create_status["State"].should.equal("SUCCEEDED")
    create_status["RequestedTimestamp"].should.be.a(datetime.datetime)
    create_status["CompletedTimestamp"].should.be.a(datetime.datetime)


def validate_policy_summary(org, summary):
    summary.should.be.a(dict)
    summary.should.have.key("Id").should.match(utils.POLICY_ID_REGEX)
    summary.should.have.key("Arn").should.equal(
        utils.SCP_ARN_FORMAT.format(org["MasterAccountId"], org["Id"], summary["Id"])
    )
    summary.should.have.key("Name").should.be.a(str)
    summary.should.have.key("Description").should.be.a(str)
    summary.should.have.key("Type").should.equal("SERVICE_CONTROL_POLICY")
    summary.should.have.key("AwsManaged").should.be.a(bool)


def validate_service_control_policy(org, response):
    response.should.have.key("PolicySummary").should.be.a(dict)
    response.should.have.key("Content").should.be.a(str)
    validate_policy_summary(org, response["PolicySummary"])
