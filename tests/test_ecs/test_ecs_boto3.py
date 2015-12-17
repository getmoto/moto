from __future__ import unicode_literals
import boto3
import sure  # noqa

from moto import mock_ecs


@mock_ecs
def test_create_cluster():
    client = boto3.client('ecs', region_name='us-east-1')
    response = client.create_cluster(
        clusterName='test_ecs_cluster'
    )
    response['cluster']['clusterName'].should.equal('test_ecs_cluster')
    response['cluster']['clusterArn'].should.equal('arn:aws:ecs:us-east-1:012345678910:cluster/test_ecs_cluster')
    response['cluster']['status'].should.equal('ACTIVE')
    response['cluster']['registeredContainerInstancesCount'].should.equal(0)
    response['cluster']['runningTasksCount'].should.equal(0)
    response['cluster']['pendingTasksCount'].should.equal(0)
    response['cluster']['activeServicesCount'].should.equal(0)


@mock_ecs
def test_list_clusters():
    client = boto3.client('ecs', region_name='us-east-1')
    _ = client.create_cluster(
        clusterName='test_cluster0'
    )
    _ = client.create_cluster(
        clusterName='test_cluster1'
    )
    response = client.list_clusters()
    response['clusterArns'].should.contain('arn:aws:ecs:us-east-1:012345678910:cluster/test_cluster0')
    response['clusterArns'].should.contain('arn:aws:ecs:us-east-1:012345678910:cluster/test_cluster1')


@mock_ecs
def test_delete_cluster():
    client = boto3.client('ecs', region_name='us-east-1')
    _ = client.create_cluster(
        clusterName='test_ecs_cluster'
    )
    response = client.delete_cluster(cluster='test_ecs_cluster')
    response['cluster']['clusterName'].should.equal('test_ecs_cluster')
    response['cluster']['clusterArn'].should.equal('arn:aws:ecs:us-east-1:012345678910:cluster/test_ecs_cluster')
    response['cluster']['status'].should.equal('ACTIVE')
    response['cluster']['registeredContainerInstancesCount'].should.equal(0)
    response['cluster']['runningTasksCount'].should.equal(0)
    response['cluster']['pendingTasksCount'].should.equal(0)
    response['cluster']['activeServicesCount'].should.equal(0)

    response = client.list_clusters()
    len(response['clusterArns']).should.equal(0)


@mock_ecs
def test_register_task_definition():
    client = boto3.client('ecs', region_name='us-east-1')
    response = client.register_task_definition(
        family='test_ecs_task',
        containerDefinitions=[
            {
                'name': 'hello_world',
                'image': 'docker/hello-world:latest',
                'cpu': 1024,
                'memory': 400,
                'essential': True,
                'environment': [{
                    'name': 'AWS_ACCESS_KEY_ID',
                    'value': 'SOME_ACCESS_KEY'
                }],
                'logConfiguration': {'logDriver': 'json-file'}
            }
        ]
    )
    type(response['taskDefinition']).should.be(dict)
    response['taskDefinition']['taskDefinitionArn'].should.equal('arn:aws:ecs:us-east-1:012345678910:task-definition/test_ecs_task:1')
    response['taskDefinition']['containerDefinitions'][0]['name'].should.equal('hello_world')
    response['taskDefinition']['containerDefinitions'][0]['image'].should.equal('docker/hello-world:latest')
    response['taskDefinition']['containerDefinitions'][0]['cpu'].should.equal(1024)
    response['taskDefinition']['containerDefinitions'][0]['memory'].should.equal(400)
    response['taskDefinition']['containerDefinitions'][0]['essential'].should.equal(True)
    response['taskDefinition']['containerDefinitions'][0]['environment'][0]['name'].should.equal('AWS_ACCESS_KEY_ID')
    response['taskDefinition']['containerDefinitions'][0]['environment'][0]['value'].should.equal('SOME_ACCESS_KEY')
    response['taskDefinition']['containerDefinitions'][0]['logConfiguration']['logDriver'].should.equal('json-file')


@mock_ecs
def test_list_task_definitions():
    client = boto3.client('ecs', region_name='us-east-1')
    _ = client.register_task_definition(
        family='test_ecs_task',
        containerDefinitions=[
            {
                'name': 'hello_world',
                'image': 'docker/hello-world:latest',
                'cpu': 1024,
                'memory': 400,
                'essential': True,
                'environment': [{
                    'name': 'AWS_ACCESS_KEY_ID',
                    'value': 'SOME_ACCESS_KEY'
                }],
                'logConfiguration': {'logDriver': 'json-file'}
            }
        ]
    )
    _ = client.register_task_definition(
        family='test_ecs_task',
        containerDefinitions=[
            {
                'name': 'hello_world2',
                'image': 'docker/hello-world2:latest',
                'cpu': 1024,
                'memory': 400,
                'essential': True,
                'environment': [{
                    'name': 'AWS_ACCESS_KEY_ID',
                    'value': 'SOME_ACCESS_KEY2'
                }],
                'logConfiguration': {'logDriver': 'json-file'}
            }
        ]
    )
    response = client.list_task_definitions()
    len(response['taskDefinitionArns']).should.equal(2)
    response['taskDefinitionArns'][0].should.equal('arn:aws:ecs:us-east-1:012345678910:task-definition/test_ecs_task:1')
    response['taskDefinitionArns'][1].should.equal('arn:aws:ecs:us-east-1:012345678910:task-definition/test_ecs_task:2')


@mock_ecs
def test_deregister_task_definition():
    client = boto3.client('ecs', region_name='us-east-1')
    _ = client.register_task_definition(
        family='test_ecs_task',
        containerDefinitions=[
            {
                'name': 'hello_world',
                'image': 'docker/hello-world:latest',
                'cpu': 1024,
                'memory': 400,
                'essential': True,
                'environment': [{
                    'name': 'AWS_ACCESS_KEY_ID',
                    'value': 'SOME_ACCESS_KEY'
                }],
                'logConfiguration': {'logDriver': 'json-file'}
            }
        ]
    )
    response = client.deregister_task_definition(
        taskDefinition='test_ecs_task:1'
    )
    type(response['taskDefinition']).should.be(dict)
    response['taskDefinition']['taskDefinitionArn'].should.equal('arn:aws:ecs:us-east-1:012345678910:task-definition/test_ecs_task:1')
    response['taskDefinition']['containerDefinitions'][0]['name'].should.equal('hello_world')
    response['taskDefinition']['containerDefinitions'][0]['image'].should.equal('docker/hello-world:latest')
    response['taskDefinition']['containerDefinitions'][0]['cpu'].should.equal(1024)
    response['taskDefinition']['containerDefinitions'][0]['memory'].should.equal(400)
    response['taskDefinition']['containerDefinitions'][0]['essential'].should.equal(True)
    response['taskDefinition']['containerDefinitions'][0]['environment'][0]['name'].should.equal('AWS_ACCESS_KEY_ID')
    response['taskDefinition']['containerDefinitions'][0]['environment'][0]['value'].should.equal('SOME_ACCESS_KEY')
    response['taskDefinition']['containerDefinitions'][0]['logConfiguration']['logDriver'].should.equal('json-file')


@mock_ecs
def test_create_service():
    client = boto3.client('ecs', region_name='us-east-1')
    _ = client.create_cluster(
        clusterName='test_ecs_cluster'
    )
    _ = client.register_task_definition(
        family='test_ecs_task',
        containerDefinitions=[
            {
                'name': 'hello_world',
                'image': 'docker/hello-world:latest',
                'cpu': 1024,
                'memory': 400,
                'essential': True,
                'environment': [{
                    'name': 'AWS_ACCESS_KEY_ID',
                    'value': 'SOME_ACCESS_KEY'
                }],
                'logConfiguration': {'logDriver': 'json-file'}
            }
        ]
    )
    response = client.create_service(
        cluster='test_ecs_cluster',
        serviceName='test_ecs_service',
        taskDefinition='test_ecs_task',
        desiredCount=2
    )
    response['service']['clusterArn'].should.equal('arn:aws:ecs:us-east-1:012345678910:cluster/test_ecs_cluster')
    response['service']['desiredCount'].should.equal(2)
    len(response['service']['events']).should.equal(0)
    len(response['service']['loadBalancers']).should.equal(0)
    response['service']['pendingCount'].should.equal(0)
    response['service']['runningCount'].should.equal(0)
    response['service']['serviceArn'].should.equal('arn:aws:ecs:us-east-1:012345678910:service/test_ecs_service')
    response['service']['serviceName'].should.equal('test_ecs_service')
    response['service']['status'].should.equal('ACTIVE')
    response['service']['taskDefinition'].should.equal('arn:aws:ecs:us-east-1:012345678910:task-definition/test_ecs_task:1')


@mock_ecs
def test_list_services():
    client = boto3.client('ecs', region_name='us-east-1')
    _ = client.create_cluster(
        clusterName='test_ecs_cluster'
    )
    _ = client.register_task_definition(
        family='test_ecs_task',
        containerDefinitions=[
            {
                'name': 'hello_world',
                'image': 'docker/hello-world:latest',
                'cpu': 1024,
                'memory': 400,
                'essential': True,
                'environment': [{
                    'name': 'AWS_ACCESS_KEY_ID',
                    'value': 'SOME_ACCESS_KEY'
                }],
                'logConfiguration': {'logDriver': 'json-file'}
            }
        ]
    )
    _ = client.create_service(
        cluster='test_ecs_cluster',
        serviceName='test_ecs_service1',
        taskDefinition='test_ecs_task',
        desiredCount=2
    )
    _ = client.create_service(
        cluster='test_ecs_cluster',
        serviceName='test_ecs_service2',
        taskDefinition='test_ecs_task',
        desiredCount=2
    )
    response = client.list_services(
        cluster='test_ecs_cluster'
    )
    len(response['serviceArns']).should.equal(2)
    response['serviceArns'][0].should.equal('arn:aws:ecs:us-east-1:012345678910:service/test_ecs_service1')
    response['serviceArns'][1].should.equal('arn:aws:ecs:us-east-1:012345678910:service/test_ecs_service2')


@mock_ecs
def test_update_service():
    client = boto3.client('ecs', region_name='us-east-1')
    _ = client.create_cluster(
        clusterName='test_ecs_cluster'
    )
    _ = client.register_task_definition(
        family='test_ecs_task',
        containerDefinitions=[
            {
                'name': 'hello_world',
                'image': 'docker/hello-world:latest',
                'cpu': 1024,
                'memory': 400,
                'essential': True,
                'environment': [{
                    'name': 'AWS_ACCESS_KEY_ID',
                    'value': 'SOME_ACCESS_KEY'
                }],
                'logConfiguration': {'logDriver': 'json-file'}
            }
        ]
    )
    response = client.create_service(
        cluster='test_ecs_cluster',
        serviceName='test_ecs_service',
        taskDefinition='test_ecs_task',
        desiredCount=2
    )
    response['service']['desiredCount'].should.equal(2)

    response = client.update_service(
        cluster='test_ecs_cluster',
        service='test_ecs_service',
        desiredCount=0
    )
    response['service']['desiredCount'].should.equal(0)


@mock_ecs
def test_delete_service():
    client = boto3.client('ecs', region_name='us-east-1')
    _ = client.create_cluster(
        clusterName='test_ecs_cluster'
    )
    _ = client.register_task_definition(
        family='test_ecs_task',
        containerDefinitions=[
            {
                'name': 'hello_world',
                'image': 'docker/hello-world:latest',
                'cpu': 1024,
                'memory': 400,
                'essential': True,
                'environment': [{
                    'name': 'AWS_ACCESS_KEY_ID',
                    'value': 'SOME_ACCESS_KEY'
                }],
                'logConfiguration': {'logDriver': 'json-file'}
            }
        ]
    )
    _ = client.create_service(
        cluster='test_ecs_cluster',
        serviceName='test_ecs_service',
        taskDefinition='test_ecs_task',
        desiredCount=2
    )
    _ = client.update_service(
        cluster='test_ecs_cluster',
        service='test_ecs_service',
        desiredCount=0
    )
    response = client.delete_service(
        cluster='test_ecs_cluster',
        service='test_ecs_service'
    )
    response['service']['clusterArn'].should.equal('arn:aws:ecs:us-east-1:012345678910:cluster/test_ecs_cluster')
    response['service']['desiredCount'].should.equal(0)
    len(response['service']['events']).should.equal(0)
    len(response['service']['loadBalancers']).should.equal(0)
    response['service']['pendingCount'].should.equal(0)
    response['service']['runningCount'].should.equal(0)
    response['service']['serviceArn'].should.equal('arn:aws:ecs:us-east-1:012345678910:service/test_ecs_service')
    response['service']['serviceName'].should.equal('test_ecs_service')
    response['service']['status'].should.equal('ACTIVE')
    response['service']['taskDefinition'].should.equal('arn:aws:ecs:us-east-1:012345678910:task-definition/test_ecs_task:1')