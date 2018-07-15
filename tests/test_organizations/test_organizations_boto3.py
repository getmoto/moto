from __future__ import unicode_literals

import boto3
import sure   # noqa
import datetime
import yaml

from moto import mock_organizations
from moto.organizations.models import (
    MASTER_ACCOUNT_ID,
    MASTER_ACCOUNT_EMAIL,
    ORGANIZATION_ARN_FORMAT,
    MASTER_ACCOUNT_ARN_FORMAT,
    ACCOUNT_ARN_FORMAT,
    ROOT_ARN_FORMAT,
    OU_ARN_FORMAT,
)
from .test_organizations_utils import (
    ORG_ID_REGEX,
    ROOT_ID_REGEX,
    OU_ID_REGEX,
    ACCOUNT_ID_REGEX,
    CREATE_ACCOUNT_STATUS_ID_REGEX,
)

EMAIL_REGEX = "^.+@[a-zA-Z0-9-.]+.[a-zA-Z]{2,3}|[0-9]{1,3}$"


def validate_organization(response):
    org = response['Organization']
    sorted(org.keys()).should.equal([
        'Arn',
        'AvailablePolicyTypes',
        'FeatureSet',
        'Id',
        'MasterAccountArn',
        'MasterAccountEmail',
        'MasterAccountId',
    ])
    org['Id'].should.match(ORG_ID_REGEX)
    org['MasterAccountId'].should.equal(MASTER_ACCOUNT_ID)
    org['MasterAccountArn'].should.equal(MASTER_ACCOUNT_ARN_FORMAT.format(
        org['MasterAccountId'],
        org['Id'],
    ))
    org['Arn'].should.equal(ORGANIZATION_ARN_FORMAT.format(
        org['MasterAccountId'],
        org['Id'],
    ))
    org['MasterAccountEmail'].should.equal(MASTER_ACCOUNT_EMAIL)
    org['FeatureSet'].should.be.within(['ALL', 'CONSOLIDATED_BILLING'])
    org['AvailablePolicyTypes'].should.equal([{
        'Type': 'SERVICE_CONTROL_POLICY',
        'Status': 'ENABLED'
    }])


def validate_organizational_unit(org, response):
    response.should.have.key('OrganizationalUnit').should.be.a(dict)
    ou = response['OrganizationalUnit']
    ou.should.have.key('Id').should.match(OU_ID_REGEX)
    ou.should.have.key('Arn').should.equal(OU_ARN_FORMAT.format(
        org['MasterAccountId'],
        org['Id'],
        ou['Id'],
    ))
    ou.should.have.key('Name').should.be.a(str)


def validate_account(org, account):
    sorted(account.keys()).should.equal([
        'Arn',
        'Email',
        'Id',
        'JoinedMethod',
        'JoinedTimestamp',
        'Name',
        'Status',
    ])
    account['Id'].should.match(ACCOUNT_ID_REGEX)
    account['Arn'].should.equal(ACCOUNT_ARN_FORMAT.format(
        org['MasterAccountId'],
        org['Id'],
        account['Id'],
    ))
    account['Email'].should.match(EMAIL_REGEX)
    account['JoinedMethod'].should.be.within(['INVITED', 'CREATED'])
    account['Status'].should.be.within(['ACTIVE', 'SUSPENDED'])
    account['Name'].should.be.a(str)
    account['JoinedTimestamp'].should.be.a(datetime.datetime)


def validate_create_account_status(create_status):
    sorted(create_status.keys()).should.equal([
        'AccountId',
        'AccountName',
        'CompletedTimestamp',
        'Id',
        'RequestedTimestamp',
        'State',
    ])
    create_status['Id'].should.match(CREATE_ACCOUNT_STATUS_ID_REGEX)
    create_status['AccountId'].should.match(ACCOUNT_ID_REGEX)
    create_status['AccountName'].should.be.a(str)
    create_status['State'].should.equal('SUCCEEDED')
    create_status['RequestedTimestamp'].should.be.a(datetime.datetime)
    create_status['CompletedTimestamp'].should.be.a(datetime.datetime)


@mock_organizations
def test_create_organization():
    client = boto3.client('organizations', region_name='us-east-1')
    response = client.create_organization(FeatureSet='ALL')
    #print(yaml.dump(response))
    validate_organization(response)
    response['Organization']['FeatureSet'].should.equal('ALL')
    #assert False


@mock_organizations
def test_describe_organization():
    client = boto3.client('organizations', region_name='us-east-1')
    client.create_organization(FeatureSet='ALL')
    response = client.describe_organization()
    #print(yaml.dump(response))
    validate_organization(response)
    #assert False


# Organizational Units

@mock_organizations
def test_list_roots():
    client = boto3.client('organizations', region_name='us-east-1')
    org = client.create_organization(FeatureSet='ALL')['Organization']
    response = client.list_roots()
    #print(yaml.dump(response, default_flow_style=False))
    response.should.have.key('Roots').should.be.a(list)
    response['Roots'].should_not.be.empty
    root = response['Roots'][0]
    root.should.have.key('Id').should.match(ROOT_ID_REGEX)
    root.should.have.key('Arn').should.equal(ROOT_ARN_FORMAT.format(
        org['MasterAccountId'],
        org['Id'],
        root['Id'],
    ))
    root.should.have.key('Name').should.be.a(str)
    root.should.have.key('PolicyTypes').should.be.a(list)
    root['PolicyTypes'][0].should.have.key('Type').should.equal('SERVICE_CONTROL_POLICY')
    root['PolicyTypes'][0].should.have.key('Status').should.equal('ENABLED')
    #assert False


@mock_organizations
def test_create_organizational_unit():
    client = boto3.client('organizations', region_name='us-east-1')
    org = client.create_organization(FeatureSet='ALL')['Organization']
    root_id = client.list_roots()['Roots'][0]['Id']
    ou_name = 'ou01'
    response = client.create_organizational_unit(
        ParentId=root_id,
        Name=ou_name,
    )
    #print(yaml.dump(response, default_flow_style=False))
    validate_organizational_unit(org, response)
    response['OrganizationalUnit']['Name'].should.equal(ou_name)
    #assert False


@mock_organizations
def test_describe_organizational_unit():
    client = boto3.client('organizations', region_name='us-east-1')
    org = client.create_organization(FeatureSet='ALL')['Organization']
    root_id = client.list_roots()['Roots'][0]['Id']
    ou_id = client.create_organizational_unit(
        ParentId=root_id,
        Name='ou01',
    )['OrganizationalUnit']['Id']
    response = client.describe_organizational_unit(OrganizationalUnitId=ou_id)
    print(yaml.dump(response, default_flow_style=False))
    validate_organizational_unit(org, response)
    #assert False


@mock_organizations
def test_list_organizational_units_for_parent():
    client = boto3.client('organizations', region_name='us-east-1')
    org = client.create_organization(FeatureSet='ALL')['Organization']
    root_id = client.list_roots()['Roots'][0]['Id']
    client.create_organizational_unit(ParentId=root_id, Name='ou01')
    client.create_organizational_unit(ParentId=root_id, Name='ou02')
    client.create_organizational_unit(ParentId=root_id, Name='ou03')
    response = client.list_organizational_units_for_parent(ParentId=root_id)
    print(yaml.dump(response, default_flow_style=False))
    response.should.have.key('OrganizationalUnits').should.be.a(list)
    for ou in response['OrganizationalUnits']:
        validate_organizational_unit(org, dict(OrganizationalUnit=ou))
    #assert False


@mock_organizations
def test_list_parents():
    client = boto3.client('organizations', region_name='us-east-1')
    org = client.create_organization(FeatureSet='ALL')['Organization']
    root_id = client.list_roots()['Roots'][0]['Id']

    ou01 = client.create_organizational_unit(ParentId=root_id, Name='ou01')
    ou01_id = ou01['OrganizationalUnit']['Id']
    response01 = client.list_parents(ChildId=ou01_id)
    #print(yaml.dump(response01, default_flow_style=False))
    response01.should.have.key('Parents').should.be.a(list)
    response01['Parents'][0].should.have.key('Id').should.equal(root_id)
    response01['Parents'][0].should.have.key('Type').should.equal('ROOT')

    ou02 = client.create_organizational_unit(ParentId=ou01_id, Name='ou02')
    ou02_id = ou02['OrganizationalUnit']['Id']
    response02 = client.list_parents(ChildId=ou02_id)
    #print(yaml.dump(response02, default_flow_style=False))
    response02.should.have.key('Parents').should.be.a(list)
    response02['Parents'][0].should.have.key('Id').should.equal(ou01_id)
    response02['Parents'][0].should.have.key('Type').should.equal('ORGANIZATIONAL_UNIT')
    #assert False


# Accounts
mockname = 'mock-account'
mockdomain = 'moto-example.org'
mockemail = '@'.join([mockname, mockdomain])


@mock_organizations
def test_create_account():
    client = boto3.client('organizations', region_name='us-east-1')
    client.create_organization(FeatureSet='ALL')
    create_status = client.create_account(
        AccountName=mockname, Email=mockemail
    )['CreateAccountStatus']
    #print(yaml.dump(create_status, default_flow_style=False))
    validate_create_account_status(create_status)
    create_status['AccountName'].should.equal(mockname)
    #assert False


@mock_organizations
def test_describe_account():
    client = boto3.client('organizations', region_name='us-east-1')
    org = client.create_organization(FeatureSet='ALL')['Organization']
    account_id = client.create_account(
        AccountName=mockname, Email=mockemail
    )['CreateAccountStatus']['AccountId']
    response = client.describe_account(AccountId=account_id)
    #print(yaml.dump(response, default_flow_style=False))
    validate_account(org, response['Account'])
    response['Account']['Name'].should.equal(mockname)
    response['Account']['Email'].should.equal(mockemail)
    #assert False


@mock_organizations
def test_list_accounts():
    client = boto3.client('organizations', region_name='us-east-1')
    org = client.create_organization(FeatureSet='ALL')['Organization']
    for i in range(5):
        name = mockname + str(i)
        email = name + '@' + mockdomain
        client.create_account(AccountName=name, Email=email)
    response = client.list_accounts()
    #print(yaml.dump(response, default_flow_style=False))
    response.should.have.key('Accounts')
    accounts = response['Accounts']
    len(accounts).should.equal(5)
    for account in accounts:
        validate_account(org, account)
    accounts[3]['Name'].should.equal(mockname + '3')
    accounts[2]['Email'].should.equal(mockname + '2' + '@' + mockdomain)
    #assert False


@mock_organizations
def test_list_accounts_for_parent():
    client = boto3.client('organizations', region_name='us-east-1')
    org = client.create_organization(FeatureSet='ALL')['Organization']
    root_id = client.list_roots()['Roots'][0]['Id']
    account_id = client.create_account(
        AccountName=mockname,
        Email=mockemail,
    )['CreateAccountStatus']['AccountId']
    response = client.list_accounts_for_parent(ParentId=root_id)
    #print(yaml.dump(response, default_flow_style=False))
    account_id.should.be.within([account['Id'] for account in response['Accounts']])
    #assert False


@mock_organizations
def test_move_account():
    client = boto3.client('organizations', region_name='us-east-1')
    org = client.create_organization(FeatureSet='ALL')['Organization']
    root_id = client.list_roots()['Roots'][0]['Id']
    account_id = client.create_account(
        AccountName=mockname, Email=mockemail
    )['CreateAccountStatus']['AccountId']
    ou01 = client.create_organizational_unit(ParentId=root_id, Name='ou01')
    ou01_id = ou01['OrganizationalUnit']['Id']
    client.move_account(
        AccountId=account_id,
        SourceParentId=root_id,
        DestinationParentId=ou01_id,
    )
    response = client.list_accounts_for_parent(ParentId=ou01_id)
    #print(yaml.dump(response, default_flow_style=False))
    account_id.should.be.within([account['Id'] for account in response['Accounts']])
    #assert False
