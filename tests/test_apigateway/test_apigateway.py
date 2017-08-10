from __future__ import unicode_literals


from datetime import datetime
from dateutil.tz import tzutc
import boto3
from freezegun import freeze_time
import requests
import sure  # noqa
from botocore.exceptions import ClientError

from moto.packages.responses import responses
from moto import mock_apigateway, settings


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
    response.pop('createdDate')
    response.should.equal({
        'id': api_id,
        'name': 'my_api',
        'description': 'this is my api',
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
    root_id = [resource for resource in resources[
        'items'] if resource['path'] == '/'][0]['id']

    root_resource = client.get_resource(
        restApiId=api_id,
        resourceId=root_id,
    )
    # this is hard to match against, so remove it
    root_resource['ResponseMetadata'].pop('HTTPHeaders', None)
    root_resource['ResponseMetadata'].pop('RetryAttempts', None)
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
    non_root_resource = [
        resource for resource in resources if resource['path'] != '/'][0]

    response = client.delete_resource(
        restApiId=api_id,
        resourceId=non_root_resource['id']
    )

    len(client.get_resources(restApiId=api_id)['items']).should.equal(1)


@mock_apigateway
def test_child_resource():
    client = boto3.client('apigateway', region_name='us-west-2')
    response = client.create_rest_api(
        name='my_api',
        description='this is my api',
    )
    api_id = response['id']

    resources = client.get_resources(restApiId=api_id)
    root_id = [resource for resource in resources[
        'items'] if resource['path'] == '/'][0]['id']

    response = client.create_resource(
        restApiId=api_id,
        parentId=root_id,
        pathPart='users',
    )
    users_id = response['id']

    response = client.create_resource(
        restApiId=api_id,
        parentId=users_id,
        pathPart='tags',
    )
    tags_id = response['id']

    child_resource = client.get_resource(
        restApiId=api_id,
        resourceId=tags_id,
    )
    # this is hard to match against, so remove it
    child_resource['ResponseMetadata'].pop('HTTPHeaders', None)
    child_resource['ResponseMetadata'].pop('RetryAttempts', None)
    child_resource.should.equal({
        'path': '/users/tags',
        'pathPart': 'tags',
        'parentId': users_id,
        'id': tags_id,
        'ResponseMetadata': {'HTTPStatusCode': 200},
        'resourceMethods': {'GET': {}},
    })


@mock_apigateway
def test_create_method():
    client = boto3.client('apigateway', region_name='us-west-2')
    response = client.create_rest_api(
        name='my_api',
        description='this is my api',
    )
    api_id = response['id']

    resources = client.get_resources(restApiId=api_id)
    root_id = [resource for resource in resources[
        'items'] if resource['path'] == '/'][0]['id']

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

    # this is hard to match against, so remove it
    response['ResponseMetadata'].pop('HTTPHeaders', None)
    response['ResponseMetadata'].pop('RetryAttempts', None)
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
    root_id = [resource for resource in resources[
        'items'] if resource['path'] == '/'][0]['id']

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
    # this is hard to match against, so remove it
    response['ResponseMetadata'].pop('HTTPHeaders', None)
    response['ResponseMetadata'].pop('RetryAttempts', None)
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
    # this is hard to match against, so remove it
    response['ResponseMetadata'].pop('HTTPHeaders', None)
    response['ResponseMetadata'].pop('RetryAttempts', None)
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
    # this is hard to match against, so remove it
    response['ResponseMetadata'].pop('HTTPHeaders', None)
    response['ResponseMetadata'].pop('RetryAttempts', None)
    response.should.equal({'ResponseMetadata': {'HTTPStatusCode': 200}})


@mock_apigateway
def test_integrations():
    client = boto3.client('apigateway', region_name='us-west-2')
    response = client.create_rest_api(
        name='my_api',
        description='this is my api',
    )
    api_id = response['id']

    resources = client.get_resources(restApiId=api_id)
    root_id = [resource for resource in resources[
        'items'] if resource['path'] == '/'][0]['id']

    client.put_method(
        restApiId=api_id,
        resourceId=root_id,
        httpMethod='GET',
        authorizationType='none',
    )

    client.put_method_response(
        restApiId=api_id,
        resourceId=root_id,
        httpMethod='GET',
        statusCode='200',
    )

    response = client.put_integration(
        restApiId=api_id,
        resourceId=root_id,
        httpMethod='GET',
        type='HTTP',
        uri='http://httpbin.org/robots.txt',
    )
    # this is hard to match against, so remove it
    response['ResponseMetadata'].pop('HTTPHeaders', None)
    response['ResponseMetadata'].pop('RetryAttempts', None)
    response.should.equal({
        'ResponseMetadata': {'HTTPStatusCode': 200},
        'httpMethod': 'GET',
        'integrationResponses': {
            '200': {
                'responseTemplates': {
                    'application/json': None
                },
                'statusCode': 200
            }
        },
        'type': 'HTTP',
        'uri': 'http://httpbin.org/robots.txt'
    })

    response = client.get_integration(
        restApiId=api_id,
        resourceId=root_id,
        httpMethod='GET'
    )
    # this is hard to match against, so remove it
    response['ResponseMetadata'].pop('HTTPHeaders', None)
    response['ResponseMetadata'].pop('RetryAttempts', None)
    response.should.equal({
        'ResponseMetadata': {'HTTPStatusCode': 200},
        'httpMethod': 'GET',
        'integrationResponses': {
            '200': {
                'responseTemplates': {
                    'application/json': None
                },
                'statusCode': 200
            }
        },
        'type': 'HTTP',
        'uri': 'http://httpbin.org/robots.txt'
    })

    response = client.get_resource(
        restApiId=api_id,
        resourceId=root_id,
    )
    # this is hard to match against, so remove it
    response['ResponseMetadata'].pop('HTTPHeaders', None)
    response['ResponseMetadata'].pop('RetryAttempts', None)
    response['resourceMethods']['GET']['methodIntegration'].should.equal({
        'httpMethod': 'GET',
        'integrationResponses': {
            '200': {
                'responseTemplates': {
                    'application/json': None
                },
                'statusCode': 200
            }
        },
        'type': 'HTTP',
        'uri': 'http://httpbin.org/robots.txt'
    })

    client.delete_integration(
        restApiId=api_id,
        resourceId=root_id,
        httpMethod='GET'
    )

    response = client.get_resource(
        restApiId=api_id,
        resourceId=root_id,
    )
    response['resourceMethods']['GET'].shouldnt.contain("methodIntegration")

    # Create a new integration with a requestTemplates config

    client.put_method(
        restApiId=api_id,
        resourceId=root_id,
        httpMethod='POST',
        authorizationType='none',
    )

    templates = {
        # example based on
        # http://docs.aws.amazon.com/apigateway/latest/developerguide/api-as-kinesis-proxy-export-swagger-with-extensions.html
        'application/json': "{\n    \"StreamName\": \"$input.params('stream-name')\",\n    \"Records\": []\n}"
    }
    test_uri = 'http://example.com/foobar.txt'
    response = client.put_integration(
        restApiId=api_id,
        resourceId=root_id,
        httpMethod='POST',
        type='HTTP',
        uri=test_uri,
        requestTemplates=templates
    )
    # this is hard to match against, so remove it
    response['ResponseMetadata'].pop('HTTPHeaders', None)
    response['ResponseMetadata'].pop('RetryAttempts', None)
    response['ResponseMetadata'].should.equal({'HTTPStatusCode': 200})

    response = client.get_integration(
        restApiId=api_id,
        resourceId=root_id,
        httpMethod='POST'
    )
    response['uri'].should.equal(test_uri)
    response['requestTemplates'].should.equal(templates)


@mock_apigateway
def test_integration_response():
    client = boto3.client('apigateway', region_name='us-west-2')
    response = client.create_rest_api(
        name='my_api',
        description='this is my api',
    )
    api_id = response['id']

    resources = client.get_resources(restApiId=api_id)
    root_id = [resource for resource in resources[
        'items'] if resource['path'] == '/'][0]['id']

    client.put_method(
        restApiId=api_id,
        resourceId=root_id,
        httpMethod='GET',
        authorizationType='none',
    )

    client.put_method_response(
        restApiId=api_id,
        resourceId=root_id,
        httpMethod='GET',
        statusCode='200',
    )

    response = client.put_integration(
        restApiId=api_id,
        resourceId=root_id,
        httpMethod='GET',
        type='HTTP',
        uri='http://httpbin.org/robots.txt',
    )

    response = client.put_integration_response(
        restApiId=api_id,
        resourceId=root_id,
        httpMethod='GET',
        statusCode='200',
        selectionPattern='foobar',
    )
    # this is hard to match against, so remove it
    response['ResponseMetadata'].pop('HTTPHeaders', None)
    response['ResponseMetadata'].pop('RetryAttempts', None)
    response.should.equal({
        'statusCode': '200',
        'selectionPattern': 'foobar',
        'ResponseMetadata': {'HTTPStatusCode': 200},
        'responseTemplates': {
            'application/json': None
        }
    })

    response = client.get_integration_response(
        restApiId=api_id,
        resourceId=root_id,
        httpMethod='GET',
        statusCode='200',
    )
    # this is hard to match against, so remove it
    response['ResponseMetadata'].pop('HTTPHeaders', None)
    response['ResponseMetadata'].pop('RetryAttempts', None)
    response.should.equal({
        'statusCode': '200',
        'selectionPattern': 'foobar',
        'ResponseMetadata': {'HTTPStatusCode': 200},
        'responseTemplates': {
            'application/json': None
        }
    })

    response = client.get_method(
        restApiId=api_id,
        resourceId=root_id,
        httpMethod='GET',
    )
    # this is hard to match against, so remove it
    response['ResponseMetadata'].pop('HTTPHeaders', None)
    response['ResponseMetadata'].pop('RetryAttempts', None)
    response['methodIntegration']['integrationResponses'].should.equal({
        '200': {
            'responseTemplates': {
                'application/json': None
            },
            'selectionPattern': 'foobar',
            'statusCode': '200'
        }
    })

    response = client.delete_integration_response(
        restApiId=api_id,
        resourceId=root_id,
        httpMethod='GET',
        statusCode='200',
    )

    response = client.get_method(
        restApiId=api_id,
        resourceId=root_id,
        httpMethod='GET',
    )
    response['methodIntegration']['integrationResponses'].should.equal({})


@mock_apigateway
def test_update_stage_configuration():
    client = boto3.client('apigateway', region_name='us-west-2')
    stage_name = 'staging'
    response = client.create_rest_api(
        name='my_api',
        description='this is my api',
    )
    api_id = response['id']

    response = client.create_deployment(
        restApiId=api_id,
        stageName=stage_name,
        description="1.0.1"
    )
    deployment_id = response['id']

    response = client.get_deployment(
        restApiId=api_id,
        deploymentId=deployment_id,
    )
    # createdDate is hard to match against, remove it
    response.pop('createdDate', None)
    # this is hard to match against, so remove it
    response['ResponseMetadata'].pop('HTTPHeaders', None)
    response['ResponseMetadata'].pop('RetryAttempts', None)
    response.should.equal({
        'id': deployment_id,
        'ResponseMetadata': {'HTTPStatusCode': 200},
        'description': '1.0.1'
    })

    response = client.create_deployment(
        restApiId=api_id,
        stageName=stage_name,
        description="1.0.2"
    )
    deployment_id2 = response['id']

    stage = client.get_stage(
        restApiId=api_id,
        stageName=stage_name
    )
    stage['stageName'].should.equal(stage_name)
    stage['deploymentId'].should.equal(deployment_id2)
    stage.shouldnt.have.key('cacheClusterSize')

    client.update_stage(restApiId=api_id, stageName=stage_name,
                        patchOperations=[
                            {
                                "op": "replace",
                                "path": "/cacheClusterEnabled",
                                "value": "True"
                            }
                        ])

    stage = client.get_stage(
        restApiId=api_id,
        stageName=stage_name
    )

    stage.should.have.key('cacheClusterSize').which.should.equal("0.5")

    client.update_stage(restApiId=api_id, stageName=stage_name,
                        patchOperations=[
                            {
                                "op": "replace",
                                "path": "/cacheClusterSize",
                                "value": "1.6"
                            }
                        ])

    stage = client.get_stage(
        restApiId=api_id,
        stageName=stage_name
    )

    stage.should.have.key('cacheClusterSize').which.should.equal("1.6")

    client.update_stage(restApiId=api_id, stageName=stage_name,
                        patchOperations=[
                            {
                                "op": "replace",
                                "path": "/deploymentId",
                                "value": deployment_id
                            },
                            {
                                "op": "replace",
                                "path": "/variables/environment",
                                "value": "dev"
                            },
                            {
                                "op": "replace",
                                "path": "/variables/region",
                                "value": "eu-west-1"
                            },
                            {
                                "op": "replace",
                                "path": "/*/*/caching/dataEncrypted",
                                "value": "True"
                            },
                            {
                                "op": "replace",
                                "path": "/cacheClusterEnabled",
                                "value": "True"
                            },
                            {
                                "op": "replace",
                                "path": "/description",
                                "value": "stage description update"
                            },
                            {
                                "op": "replace",
                                "path": "/cacheClusterSize",
                                "value": "1.6"
                            }
                        ])

    client.update_stage(restApiId=api_id, stageName=stage_name,
                        patchOperations=[
                            {
                                "op": "remove",
                                "path": "/variables/region",
                                "value": "eu-west-1"
                            }
                        ])

    stage = client.get_stage(restApiId=api_id, stageName=stage_name)

    stage['description'].should.match('stage description update')
    stage['cacheClusterSize'].should.equal("1.6")
    stage['variables']['environment'].should.match('dev')
    stage['variables'].should_not.have.key('region')
    stage['cacheClusterEnabled'].should.be.true
    stage['deploymentId'].should.match(deployment_id)
    stage['methodSettings'].should.have.key('*/*')
    stage['methodSettings'][
        '*/*'].should.have.key('cacheDataEncrypted').which.should.be.true

    try:
        client.update_stage(restApiId=api_id, stageName=stage_name,
                            patchOperations=[
                                {
                                    "op": "add",
                                    "path": "/notasetting",
                                    "value": "eu-west-1"
                                }
                            ])
        assert False.should.be.ok  # Fail, should not be here
    except Exception:
        assert True.should.be.ok


@mock_apigateway
def test_non_existent_stage():
    client = boto3.client('apigateway', region_name='us-west-2')
    response = client.create_rest_api(
        name='my_api',
        description='this is my api',
    )
    api_id = response['id']

    client.get_stage.when.called_with(
        restApiId=api_id, stageName='xxx').should.throw(ClientError)


@mock_apigateway
def test_create_stage():
    client = boto3.client('apigateway', region_name='us-west-2')
    stage_name = 'staging'
    response = client.create_rest_api(
        name='my_api',
        description='this is my api',
    )
    api_id = response['id']

    response = client.create_deployment(
        restApiId=api_id,
        stageName=stage_name,
    )
    deployment_id = response['id']

    response = client.get_deployment(
        restApiId=api_id,
        deploymentId=deployment_id,
    )
    # createdDate is hard to match against, remove it
    response.pop('createdDate', None)
    # this is hard to match against, so remove it
    response['ResponseMetadata'].pop('HTTPHeaders', None)
    response['ResponseMetadata'].pop('RetryAttempts', None)
    response.should.equal({
        'id': deployment_id,
        'ResponseMetadata': {'HTTPStatusCode': 200},
        'description': ''
    })

    response = client.create_deployment(
        restApiId=api_id,
        stageName=stage_name,
    )

    deployment_id2 = response['id']

    response = client.get_deployments(
        restApiId=api_id,
    )

    # this is hard to match against, so remove it
    response['ResponseMetadata'].pop('HTTPHeaders', None)
    response['ResponseMetadata'].pop('RetryAttempts', None)

    response['items'][0].pop('createdDate')
    response['items'][1].pop('createdDate')
    response['items'][0]['id'].should.match(
        r"{0}|{1}".format(deployment_id2, deployment_id))
    response['items'][1]['id'].should.match(
        r"{0}|{1}".format(deployment_id2, deployment_id))

    new_stage_name = 'current'
    response = client.create_stage(
        restApiId=api_id, stageName=new_stage_name, deploymentId=deployment_id2)

    # this is hard to match against, so remove it
    response['ResponseMetadata'].pop('HTTPHeaders', None)
    response['ResponseMetadata'].pop('RetryAttempts', None)

    response.should.equal({
        'stageName': new_stage_name,
        'deploymentId': deployment_id2,
        'methodSettings': {},
        'variables': {},
        'ResponseMetadata': {'HTTPStatusCode': 200},
        'description': '',
        'cacheClusterEnabled': False
    })

    stage = client.get_stage(
        restApiId=api_id,
        stageName=new_stage_name
    )
    stage['stageName'].should.equal(new_stage_name)
    stage['deploymentId'].should.equal(deployment_id2)

    new_stage_name_with_vars = 'stage_with_vars'
    response = client.create_stage(restApiId=api_id, stageName=new_stage_name_with_vars, deploymentId=deployment_id2, variables={
        "env": "dev"
    })

    # this is hard to match against, so remove it
    response['ResponseMetadata'].pop('HTTPHeaders', None)
    response['ResponseMetadata'].pop('RetryAttempts', None)

    response.should.equal({
        'stageName': new_stage_name_with_vars,
        'deploymentId': deployment_id2,
        'methodSettings': {},
        'variables': {"env": "dev"},
        'ResponseMetadata': {'HTTPStatusCode': 200},
        'description': '',
        'cacheClusterEnabled': False
    })

    stage = client.get_stage(
        restApiId=api_id,
        stageName=new_stage_name_with_vars
    )
    stage['stageName'].should.equal(new_stage_name_with_vars)
    stage['deploymentId'].should.equal(deployment_id2)
    stage['variables'].should.have.key('env').which.should.match("dev")

    new_stage_name = 'stage_with_vars_and_cache_settings'
    response = client.create_stage(restApiId=api_id, stageName=new_stage_name, deploymentId=deployment_id2, variables={
        "env": "dev"
    }, cacheClusterEnabled=True, description="hello moto")

    # this is hard to match against, so remove it
    response['ResponseMetadata'].pop('HTTPHeaders', None)
    response['ResponseMetadata'].pop('RetryAttempts', None)

    response.should.equal({
        'stageName': new_stage_name,
        'deploymentId': deployment_id2,
        'methodSettings': {},
        'variables': {"env": "dev"},
        'ResponseMetadata': {'HTTPStatusCode': 200},
        'description': 'hello moto',
        'cacheClusterEnabled': True,
        'cacheClusterSize': "0.5"
    })

    stage = client.get_stage(
        restApiId=api_id,
        stageName=new_stage_name
    )

    stage['cacheClusterSize'].should.equal("0.5")

    new_stage_name = 'stage_with_vars_and_cache_settings_and_size'
    response = client.create_stage(restApiId=api_id, stageName=new_stage_name, deploymentId=deployment_id2, variables={
        "env": "dev"
    }, cacheClusterEnabled=True, cacheClusterSize="1.6", description="hello moto")

    # this is hard to match against, so remove it
    response['ResponseMetadata'].pop('HTTPHeaders', None)
    response['ResponseMetadata'].pop('RetryAttempts', None)

    response.should.equal({
        'stageName': new_stage_name,
        'deploymentId': deployment_id2,
        'methodSettings': {},
        'variables': {"env": "dev"},
        'ResponseMetadata': {'HTTPStatusCode': 200},
        'description': 'hello moto',
        'cacheClusterEnabled': True,
        'cacheClusterSize': "1.6"
    })

    stage = client.get_stage(
        restApiId=api_id,
        stageName=new_stage_name
    )
    stage['stageName'].should.equal(new_stage_name)
    stage['deploymentId'].should.equal(deployment_id2)
    stage['variables'].should.have.key('env').which.should.match("dev")
    stage['cacheClusterSize'].should.equal("1.6")


@mock_apigateway
def test_deployment():
    client = boto3.client('apigateway', region_name='us-west-2')
    stage_name = 'staging'
    response = client.create_rest_api(
        name='my_api',
        description='this is my api',
    )
    api_id = response['id']

    response = client.create_deployment(
        restApiId=api_id,
        stageName=stage_name,
    )
    deployment_id = response['id']

    response = client.get_deployment(
        restApiId=api_id,
        deploymentId=deployment_id,
    )
    # createdDate is hard to match against, remove it
    response.pop('createdDate', None)
    # this is hard to match against, so remove it
    response['ResponseMetadata'].pop('HTTPHeaders', None)
    response['ResponseMetadata'].pop('RetryAttempts', None)
    response.should.equal({
        'id': deployment_id,
        'ResponseMetadata': {'HTTPStatusCode': 200},
        'description': ''
    })

    response = client.get_deployments(
        restApiId=api_id,
    )

    response['items'][0].pop('createdDate')
    response['items'].should.equal([
        {'id': deployment_id, 'description': ''}
    ])

    response = client.delete_deployment(
        restApiId=api_id,
        deploymentId=deployment_id,
    )

    response = client.get_deployments(
        restApiId=api_id,
    )
    len(response['items']).should.equal(0)

    # test deployment stages

    stage = client.get_stage(
        restApiId=api_id,
        stageName=stage_name
    )
    stage['stageName'].should.equal(stage_name)
    stage['deploymentId'].should.equal(deployment_id)

    stage = client.update_stage(
        restApiId=api_id,
        stageName=stage_name,
        patchOperations=[
            {
                'op': 'replace',
                'path': '/description',
                'value': '_new_description_'
            },
        ]
    )

    stage = client.get_stage(
        restApiId=api_id,
        stageName=stage_name
    )
    stage['stageName'].should.equal(stage_name)
    stage['deploymentId'].should.equal(deployment_id)
    stage['description'].should.equal('_new_description_')


@mock_apigateway
def test_http_proxying_integration():
    responses.add(
        responses.GET, "http://httpbin.org/robots.txt", body='a fake response'
    )

    region_name = 'us-west-2'
    client = boto3.client('apigateway', region_name=region_name)
    response = client.create_rest_api(
        name='my_api',
        description='this is my api',
    )
    api_id = response['id']

    resources = client.get_resources(restApiId=api_id)
    root_id = [resource for resource in resources[
        'items'] if resource['path'] == '/'][0]['id']

    client.put_method(
        restApiId=api_id,
        resourceId=root_id,
        httpMethod='GET',
        authorizationType='none',
    )

    client.put_method_response(
        restApiId=api_id,
        resourceId=root_id,
        httpMethod='GET',
        statusCode='200',
    )

    response = client.put_integration(
        restApiId=api_id,
        resourceId=root_id,
        httpMethod='GET',
        type='HTTP',
        uri='http://httpbin.org/robots.txt',
    )

    stage_name = 'staging'
    client.create_deployment(
        restApiId=api_id,
        stageName=stage_name,
    )

    deploy_url = "https://{api_id}.execute-api.{region_name}.amazonaws.com/{stage_name}".format(
        api_id=api_id, region_name=region_name, stage_name=stage_name)

    if not settings.TEST_SERVER_MODE:
        requests.get(deploy_url).content.should.equal(b"a fake response")
