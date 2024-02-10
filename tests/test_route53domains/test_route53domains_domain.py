import boto3

from moto import mock_aws


@mock_aws
def test_route53domains_register_domain():  # pylint: disable=too-many-locals
    """Test good register domain API calls."""
    route53domains_client = boto3.client('route53domains', region_name='global')
    res = route53domains_client.register_domain(
        DomainName='domain.com',
        DurationInYears=3,
        AutoRenew=True,
        AdminContact={
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
        RegistrantContact={
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
        TechContact={
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
        PrivacyProtectAdminContact=True,
        PrivacyProtectRegistrantContact=True,
        PrivacyProtectTechContact=True,
    )

    operation_id = res['OperationId']

    operations = route53domains_client.list_operations()['Operations']
    for operation in operations:
        if operation['OperationId'] == operation_id:
            return

    assert False, 'Could not find expected operation id returned from `register_domain` in operation list'


@mock_aws
def test_route53domains_register_domain_creates_hosted_zone():  # pylint: disable=too-many-locals
    """Test good register domain API calls."""
    route53domains_client = boto3.client('route53domains', region_name='global')
    route53_client = boto3.client('route53', region_name='global')
    route53domains_client.register_domain(
        DomainName='test.com',
        DurationInYears=3,
        AutoRenew=True,
        AdminContact={
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
        RegistrantContact={
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
        TechContact={
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
        PrivacyProtectAdminContact=True,
        PrivacyProtectRegistrantContact=True,
        PrivacyProtectTechContact=True,
    )

    res = route53_client.list_hosted_zones()
    for zone in res['HostedZones']:
        if zone['Name'] == 'test.com':
            return

    assert False, '`register_domain` did not create a new hosted zone with the same name'
