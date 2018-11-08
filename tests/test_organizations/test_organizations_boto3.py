from __future__ import unicode_literals

import boto3
import sure   # noqa
from botocore.exceptions import ClientError
from nose.tools import assert_raises

from moto import mock_organizations
from moto.organizations import utils
from .organizations_test_utils import (
    validate_organization,
    validate_roots,
    validate_organizational_unit,
    validate_account,
    validate_create_account_status,
)


@mock_organizations
def test_create_organization():
    client = boto3.client('organizations', region_name='us-east-1')
    response = client.create_organization(FeatureSet='ALL')
    validate_organization(response)
    response['Organization']['FeatureSet'].should.equal('ALL')


@mock_organizations
def test_describe_organization():
    client = boto3.client('organizations', region_name='us-east-1')
    client.create_organization(FeatureSet='ALL')
    response = client.describe_organization()
    validate_organization(response)


@mock_organizations
def test_describe_organization_exception():
    client = boto3.client('organizations', region_name='us-east-1')
    with assert_raises(ClientError) as e:
        response = client.describe_organization()
    ex = e.exception
    ex.operation_name.should.equal('DescribeOrganization')
    ex.response['Error']['Code'].should.equal('400')
    ex.response['Error']['Message'].should.contain('AWSOrganizationsNotInUseException')


# Organizational Units

@mock_organizations
def test_list_roots():
    client = boto3.client('organizations', region_name='us-east-1')
    org = client.create_organization(FeatureSet='ALL')['Organization']
    response = client.list_roots()
    validate_roots(org, response)


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
    validate_organizational_unit(org, response)
    response['OrganizationalUnit']['Name'].should.equal(ou_name)


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
    validate_organizational_unit(org, response)


@mock_organizations
def test_describe_organizational_unit_exception():
    client = boto3.client('organizations', region_name='us-east-1')
    org = client.create_organization(FeatureSet='ALL')['Organization']
    with assert_raises(ClientError) as e:
        response = client.describe_organizational_unit(
            OrganizationalUnitId=utils.make_random_root_id()
        )
    ex = e.exception
    ex.operation_name.should.equal('DescribeOrganizationalUnit')
    ex.response['Error']['Code'].should.equal('400')
    ex.response['Error']['Message'].should.contain('OrganizationalUnitNotFoundException')


@mock_organizations
def test_list_organizational_units_for_parent():
    client = boto3.client('organizations', region_name='us-east-1')
    org = client.create_organization(FeatureSet='ALL')['Organization']
    root_id = client.list_roots()['Roots'][0]['Id']
    client.create_organizational_unit(ParentId=root_id, Name='ou01')
    client.create_organizational_unit(ParentId=root_id, Name='ou02')
    client.create_organizational_unit(ParentId=root_id, Name='ou03')
    response = client.list_organizational_units_for_parent(ParentId=root_id)
    response.should.have.key('OrganizationalUnits').should.be.a(list)
    for ou in response['OrganizationalUnits']:
        validate_organizational_unit(org, dict(OrganizationalUnit=ou))


@mock_organizations
def test_list_organizational_units_for_parent_exception():
    client = boto3.client('organizations', region_name='us-east-1')
    with assert_raises(ClientError) as e:
        response = client.list_organizational_units_for_parent(
            ParentId=utils.make_random_root_id()
        )
    ex = e.exception
    ex.operation_name.should.equal('ListOrganizationalUnitsForParent')
    ex.response['Error']['Code'].should.equal('400')
    ex.response['Error']['Message'].should.contain('ParentNotFoundException')


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
    validate_create_account_status(create_status)
    create_status['AccountName'].should.equal(mockname)


@mock_organizations
def test_describe_account():
    client = boto3.client('organizations', region_name='us-east-1')
    org = client.create_organization(FeatureSet='ALL')['Organization']
    account_id = client.create_account(
        AccountName=mockname, Email=mockemail
    )['CreateAccountStatus']['AccountId']
    response = client.describe_account(AccountId=account_id)
    validate_account(org, response['Account'])
    response['Account']['Name'].should.equal(mockname)
    response['Account']['Email'].should.equal(mockemail)


@mock_organizations
def test_describe_account_exception():
    client = boto3.client('organizations', region_name='us-east-1')
    with assert_raises(ClientError) as e:
        response = client.describe_account(AccountId=utils.make_random_account_id())
    ex = e.exception
    ex.operation_name.should.equal('DescribeAccount')
    ex.response['Error']['Code'].should.equal('400')
    ex.response['Error']['Message'].should.contain('AccountNotFoundException')


@mock_organizations
def test_list_accounts():
    client = boto3.client('organizations', region_name='us-east-1')
    org = client.create_organization(FeatureSet='ALL')['Organization']
    for i in range(5):
        name = mockname + str(i)
        email = name + '@' + mockdomain
        client.create_account(AccountName=name, Email=email)
    response = client.list_accounts()
    response.should.have.key('Accounts')
    accounts = response['Accounts']
    len(accounts).should.equal(5)
    for account in accounts:
        validate_account(org, account)
    accounts[3]['Name'].should.equal(mockname + '3')
    accounts[2]['Email'].should.equal(mockname + '2' + '@' + mockdomain)


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
    account_id.should.be.within([account['Id'] for account in response['Accounts']])


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
    account_id.should.be.within([account['Id'] for account in response['Accounts']])


@mock_organizations
def test_list_parents_for_ou():
    client = boto3.client('organizations', region_name='us-east-1')
    org = client.create_organization(FeatureSet='ALL')['Organization']
    root_id = client.list_roots()['Roots'][0]['Id']
    ou01 = client.create_organizational_unit(ParentId=root_id, Name='ou01')
    ou01_id = ou01['OrganizationalUnit']['Id']
    response01 = client.list_parents(ChildId=ou01_id)
    response01.should.have.key('Parents').should.be.a(list)
    response01['Parents'][0].should.have.key('Id').should.equal(root_id)
    response01['Parents'][0].should.have.key('Type').should.equal('ROOT')
    ou02 = client.create_organizational_unit(ParentId=ou01_id, Name='ou02')
    ou02_id = ou02['OrganizationalUnit']['Id']
    response02 = client.list_parents(ChildId=ou02_id)
    response02.should.have.key('Parents').should.be.a(list)
    response02['Parents'][0].should.have.key('Id').should.equal(ou01_id)
    response02['Parents'][0].should.have.key('Type').should.equal('ORGANIZATIONAL_UNIT')


@mock_organizations
def test_list_parents_for_accounts():
    client = boto3.client('organizations', region_name='us-east-1')
    org = client.create_organization(FeatureSet='ALL')['Organization']
    root_id = client.list_roots()['Roots'][0]['Id']
    ou01 = client.create_organizational_unit(ParentId=root_id, Name='ou01')
    ou01_id = ou01['OrganizationalUnit']['Id']
    account01_id = client.create_account(
        AccountName='account01',
        Email='account01@moto-example.org'
    )['CreateAccountStatus']['AccountId']
    account02_id = client.create_account(
        AccountName='account02',
        Email='account02@moto-example.org'
    )['CreateAccountStatus']['AccountId']
    client.move_account(
        AccountId=account02_id,
        SourceParentId=root_id,
        DestinationParentId=ou01_id,
    )
    response01 = client.list_parents(ChildId=account01_id)
    response01.should.have.key('Parents').should.be.a(list)
    response01['Parents'][0].should.have.key('Id').should.equal(root_id)
    response01['Parents'][0].should.have.key('Type').should.equal('ROOT')
    response02 = client.list_parents(ChildId=account02_id)
    response02.should.have.key('Parents').should.be.a(list)
    response02['Parents'][0].should.have.key('Id').should.equal(ou01_id)
    response02['Parents'][0].should.have.key('Type').should.equal('ORGANIZATIONAL_UNIT')


@mock_organizations
def test_list_children():
    client = boto3.client('organizations', region_name='us-east-1')
    org = client.create_organization(FeatureSet='ALL')['Organization']
    root_id = client.list_roots()['Roots'][0]['Id']
    ou01 = client.create_organizational_unit(ParentId=root_id, Name='ou01')
    ou01_id = ou01['OrganizationalUnit']['Id']
    ou02 = client.create_organizational_unit(ParentId=ou01_id, Name='ou02')
    ou02_id = ou02['OrganizationalUnit']['Id']
    account01_id = client.create_account(
        AccountName='account01',
        Email='account01@moto-example.org'
    )['CreateAccountStatus']['AccountId']
    account02_id = client.create_account(
        AccountName='account02',
        Email='account02@moto-example.org'
    )['CreateAccountStatus']['AccountId']
    client.move_account(
        AccountId=account02_id,
        SourceParentId=root_id,
        DestinationParentId=ou01_id,
    )
    response01 = client.list_children(ParentId=root_id, ChildType='ACCOUNT')
    response02 = client.list_children(ParentId=root_id, ChildType='ORGANIZATIONAL_UNIT')
    response03 = client.list_children(ParentId=ou01_id, ChildType='ACCOUNT')
    response04 = client.list_children(ParentId=ou01_id, ChildType='ORGANIZATIONAL_UNIT')
    response01['Children'][0]['Id'].should.equal(account01_id)
    response01['Children'][0]['Type'].should.equal('ACCOUNT')
    response02['Children'][0]['Id'].should.equal(ou01_id)
    response02['Children'][0]['Type'].should.equal('ORGANIZATIONAL_UNIT')
    response03['Children'][0]['Id'].should.equal(account02_id)
    response03['Children'][0]['Type'].should.equal('ACCOUNT')
    response04['Children'][0]['Id'].should.equal(ou02_id)
    response04['Children'][0]['Type'].should.equal('ORGANIZATIONAL_UNIT')


@mock_organizations
def test_list_children_exception():
    client = boto3.client('organizations', region_name='us-east-1')
    org = client.create_organization(FeatureSet='ALL')['Organization']
    root_id = client.list_roots()['Roots'][0]['Id']
    with assert_raises(ClientError) as e:
        response = client.list_children(
            ParentId=utils.make_random_root_id(),
            ChildType='ACCOUNT'
        )
    ex = e.exception
    ex.operation_name.should.equal('ListChildren')
    ex.response['Error']['Code'].should.equal('400')
    ex.response['Error']['Message'].should.contain('ParentNotFoundException')
    with assert_raises(ClientError) as e:
        response = client.list_children(
            ParentId=root_id,
            ChildType='BLEE'
        )
    ex = e.exception
    ex.operation_name.should.equal('ListChildren')
    ex.response['Error']['Code'].should.equal('400')
    ex.response['Error']['Message'].should.contain('InvalidInputException')
