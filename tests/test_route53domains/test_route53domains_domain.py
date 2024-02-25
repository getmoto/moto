from datetime import datetime, timezone, timedelta
from typing import Dict

import boto3
from botocore.exceptions import ClientError
import pytest

from moto import mock_aws


@pytest.fixture(scope='function')
def register_domain_parameters() -> Dict:
    return {
        'DomainName': 'domain.com',
        'DurationInYears': 3,
        'AutoRenew': True,
        'AdminContact': {
            'FirstName': 'First',
            'LastName': 'Last',
            'ContactType': 'PERSON',
            'AddressLine1': 'address 1',
            'AddressLine2': 'address 2',
            'City': 'New York City',
            'CountryCode': 'US',
            'ZipCode': '123123123',
            'Email': 'email@gmail.com',
            'Fax': '+1.1234567890',
        },
        'RegistrantContact': {
            'FirstName': 'First',
            'LastName': 'Last',
            'ContactType': 'PERSON',
            'AddressLine1': 'address 1',
            'AddressLine2': 'address 2',
            'City': 'New York City',
            'CountryCode': 'US',
            'ZipCode': '123123123',
            'Email': 'email@gmail.com',
            'Fax': '+1.1234567890',
        },
        'TechContact': {
            'FirstName': 'First',
            'LastName': 'Last',
            'ContactType': 'PERSON',
            'AddressLine1': 'address 1',
            'AddressLine2': 'address 2',
            'City': 'New York City',
            'CountryCode': 'US',
            'ZipCode': '123123123',
            'Email': 'email@gmail.com',
            'Fax': '+1.1234567890',
        },
        'PrivacyProtectAdminContact': True,
        'PrivacyProtectRegistrantContact': True,
        'PrivacyProtectTechContact': True,
    }


@pytest.fixture(scope='function')
def invalid_register_domain_parameters(register_domain_parameters: Dict) -> Dict:
    register_domain_parameters['DomainName'] = 'a'
    register_domain_parameters['DurationInYears'] = 500
    return register_domain_parameters


@mock_aws
def test_route53domains_register_domain(register_domain_parameters: Dict):
    route53domains_client = boto3.client('route53domains', region_name='global')
    res = route53domains_client.register_domain(**register_domain_parameters)

    operation_id = res['OperationId']

    operations = route53domains_client.list_operations()['Operations']
    for operation in operations:
        if operation['OperationId'] == operation_id:
            return

    assert False, 'Could not find expected operation id returned from `register_domain` in operation list'


@mock_aws
def test_route53domains_register_domain_creates_hosted_zone(register_domain_parameters: Dict):
    """Test good register domain API calls."""
    route53domains_client = boto3.client('route53domains', region_name='global')
    route53_client = boto3.client('route53', region_name='global')
    route53domains_client.register_domain(**register_domain_parameters)

    res = route53_client.list_hosted_zones()
    for zone in res['HostedZones']:
        if zone['Name'] == 'domain.com':
            return

    assert False, '`register_domain` did not create a new hosted zone with the same name'


@mock_aws
def test_route53domains_register_domain_fails_on_invalid_input(invalid_register_domain_parameters: Dict):
    route53domains_client = boto3.client('route53domains', region_name='global')
    route53_client = boto3.client('route53', region_name='global')
    with pytest.raises(ClientError):
        route53domains_client.register_domain(**invalid_register_domain_parameters)

    res = route53_client.list_hosted_zones()
    assert len(res['HostedZones']) == 0


@mock_aws
def test_route53domains_register_domain_fails_on_invalid_tld(register_domain_parameters: Dict):
    route53domains_client = boto3.client('route53domains', region_name='global')
    route53_client = boto3.client('route53', region_name='global')

    register_domain_parameters['DomainName'] = 'test.non-existing-tld'
    with pytest.raises(ClientError):
        route53domains_client.register_domain(**register_domain_parameters)

    res = route53_client.list_hosted_zones()
    assert len(res['HostedZones']) == 0


@mock_aws
def test_route53domains_list_operations(register_domain_parameters: Dict):
    route53domains_client = boto3.client('route53domains', region_name='global')
    route53domains_client.register_domain(**register_domain_parameters)

    operations = route53domains_client.list_operations()['Operations']
    assert len(operations) == 1

    future_time = datetime.now(timezone.utc) + timedelta(minutes=1)
    operations = route53domains_client.list_operations(SubmittedSince=future_time.timestamp())['Operations']
    assert len(operations) == 0

    operations = route53domains_client.list_operations(Status=['SUCCESSFUL'])['Operations']
    assert len(operations) == 1

    operations = route53domains_client.list_operations(Status=['IN_PROGRESS'])['Operations']
    assert len(operations) == 0

    operations = route53domains_client.list_operations(Type=['REGISTER_DOMAIN'])['Operations']
    assert len(operations) == 1

    operations = route53domains_client.list_operations(Type=['DELETE_DOMAIN'])['Operations']
    assert len(operations) == 0


@mock_aws
def test_list_operations_invalid_input():
    route53domains_client = boto3.client('route53domains', region_name='global')
    with pytest.raises(ClientError):
        _ = route53domains_client.list_operations(Type=['INVALID_TYPE'])['Operations']

    with pytest.raises(ClientError):
        _ = route53domains_client.list_operations(Status=['INVALID_STATUS'])['Operations']
