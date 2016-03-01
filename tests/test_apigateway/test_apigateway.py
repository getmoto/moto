from __future__ import unicode_literals

from datetime import datetime
from dateutil.tz import tzutc
import boto3
from freezegun import freeze_time
import sure  # noqa

from moto import mock_apigateway


@freeze_time("2015-01-01")
@mock_apigateway
def test_create_and_get_rest_api():
    client = boto3.client('apigateway', region_name='us-west-2')

    response = client.create_rest_api(
        name='my_api',
        description='this is my api',
    )
    api_id = response['id']

    response = client.get_rest_api(
        restApiId=api_id
    )

    response.pop('ResponseMetadata')
    response.should.equal({
        'id': api_id,
        'name': 'my_api',
        'description': 'this is my api',
        'createdDate': datetime(2015, 1, 1, tzinfo=tzutc())
    })


@mock_apigateway
def test_list_and_delete_apis():
    client = boto3.client('apigateway', region_name='us-west-2')

    response = client.create_rest_api(
        name='my_api',
        description='this is my api',
    )
    api_id = response['id']
    client.create_rest_api(
        name='my_api2',
        description='this is my api2',
    )

    response = client.get_rest_apis()
    len(response['items']).should.equal(2)

    client.delete_rest_api(
        restApiId=api_id
    )

    response = client.get_rest_apis()
    len(response['items']).should.equal(1)
