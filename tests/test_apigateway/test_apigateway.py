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


@mock_apigateway
def test_create_resource():
    client = boto3.client('apigateway', region_name='us-west-2')
    response = client.create_rest_api(
        name='my_api',
        description='this is my api',
    )
    api_id = response['id']

    resources = client.get_resources(restApiId=api_id)
    root_id = [resource for resource in resources['items'] if resource['path'] == '/'][0]['id']

    root_resource = client.get_resource(
        restApiId=api_id,
        resourceId=root_id,
    )
    root_resource.should.equal({
        'path': '/',
        'id': root_id,
        'ResponseMetadata': {'HTTPStatusCode': 200},
        'resourceMethods': {
            'GET': {}
        }
    })

    response = client.create_resource(
        restApiId=api_id,
        parentId=root_id,
        pathPart='/users',
    )

    resources = client.get_resources(restApiId=api_id)['items']
    len(resources).should.equal(2)
    non_root_resource = [resource for resource in resources if resource['path'] != '/'][0]

    response = client.delete_resource(
        restApiId=api_id,
        resourceId=non_root_resource['id']
    )

    len(client.get_resources(restApiId=api_id)['items']).should.equal(1)


@mock_apigateway
def test_create_method():
    client = boto3.client('apigateway', region_name='us-west-2')
    response = client.create_rest_api(
        name='my_api',
        description='this is my api',
    )
    api_id = response['id']

    resources = client.get_resources(restApiId=api_id)
    root_id = [resource for resource in resources['items'] if resource['path'] == '/'][0]['id']

    client.put_method(
        restApiId=api_id,
        resourceId=root_id,
        httpMethod='GET',
        authorizationType='none',
    )

    response = client.get_method(
        restApiId=api_id,
        resourceId=root_id,
        httpMethod='GET'
    )

    response.should.equal({
        'httpMethod': 'GET',
        'authorizationType': 'none',
        'ResponseMetadata': {'HTTPStatusCode': 200}
    })


@mock_apigateway
def test_create_method_response():
    client = boto3.client('apigateway', region_name='us-west-2')
    response = client.create_rest_api(
        name='my_api',
        description='this is my api',
    )
    api_id = response['id']

    resources = client.get_resources(restApiId=api_id)
    root_id = [resource for resource in resources['items'] if resource['path'] == '/'][0]['id']

    client.put_method(
        restApiId=api_id,
        resourceId=root_id,
        httpMethod='GET',
        authorizationType='none',
    )

    response = client.get_method(
        restApiId=api_id,
        resourceId=root_id,
        httpMethod='GET'
    )

    response = client.put_method_response(
        restApiId=api_id,
        resourceId=root_id,
        httpMethod='GET',
        statusCode='200',
    )
    response.should.equal({
        'ResponseMetadata': {'HTTPStatusCode': 200},
        'statusCode': '200'
    })

    response = client.get_method_response(
        restApiId=api_id,
        resourceId=root_id,
        httpMethod='GET',
        statusCode='200',
    )
    response.should.equal({
        'ResponseMetadata': {'HTTPStatusCode': 200},
        'statusCode': '200'
    })

    response = client.delete_method_response(
        restApiId=api_id,
        resourceId=root_id,
        httpMethod='GET',
        statusCode='200',
    )
    response.should.equal({'ResponseMetadata': {'HTTPStatusCode': 200}})
