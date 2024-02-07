import boto3

from moto import mock_aws, settings


@mock_aws
def test_route53domains_register_domain():  # pylint: disable=too-many-locals
    """Test good register domain API calls."""
    client = boto3.client("route53domains", region_name='us-east-1')
    res = client.register_domain(
        DomainName='test.com',
        IdnLangCode='code',
        DurationInYears=3,
        AutoRenew=True,
        AdminContact={
            'FirstName': 'First',
            'LastName': 'Last',
            'ContactType': 'PERSON',
            'OrganizationName': 'United States Government',
            'AddressLine1': 'address 1',
            'AddressLine2': 'address 2',
            'City': 'New York City',
            'CountryCode': 'US',
            'ZipCode': '123123123',
            'Email': 'email@gmail.com',
            'Fax': 'some-fax-number',
            },
        RegistrantContact={
            'FirstName': 'First',
            'LastName': 'Last',
            'ContactType': 'PERSON',
            'OrganizationName': 'United States Government',
            'AddressLine1': 'address 1',
            'AddressLine2': 'address 2',
            'City': 'New York City',
            'CountryCode': 'US',
            'ZipCode': '123123123',
            'Email': 'email@gmail.com',
            'Fax': 'some-fax-number',
        },
        TechContact={
            'FirstName': 'First',
            'LastName': 'Last',
            'ContactType': 'PERSON',
            'OrganizationName': 'United States Government',
            'AddressLine1': 'address 1',
            'AddressLine2': 'address 2',
            'City': 'New York City',
            'CountryCode': 'US',
            'ZipCode': '123123123',
            'Email': 'email@gmail.com',
            'Fax': 'some-fax-number',
        },
        PrivacyProtectAdminContact=True,
        PrivacyProtectRegistrantContact=True,
        PrivacyProtectTechContact=True,
    )

    print(res)
