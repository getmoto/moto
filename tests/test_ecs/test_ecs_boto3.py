from __future__ import unicode_literals
import boto3
import sure  # noqa
import json
from moto.ec2 import utils as ec2_utils
from uuid import UUID

from moto import mock_ecs
from moto import mock_ec2


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

@mock_ec2
@mock_ecs
def test_register_container_instance():
    ecs_client = boto3.client('ecs', region_name='us-east-1')
    ec2 = boto3.resource('ec2', region_name='us-east-1')

    test_cluster_name = 'test_ecs_cluster'

    _ = ecs_client.create_cluster(
        clusterName=test_cluster_name
    )

    test_instance = ec2.create_instances(
        ImageId="ami-1234abcd",
        MinCount=1,
        MaxCount=1,
    )[0]

    instance_id_document = json.dumps(
        ec2_utils.generate_instance_identity_document(test_instance)
    )

    response = ecs_client.register_container_instance(
        cluster=test_cluster_name,
        instanceIdentityDocument=instance_id_document
    )

    response['containerInstance']['ec2InstanceId'].should.equal(test_instance.id)
    full_arn = response['containerInstance']['containerInstanceArn']
    arn_part = full_arn.split('/')
    arn_part[0].should.equal('arn:aws:ecs:us-east-1:012345678910:container-instance')
    arn_part[1].should.equal(str(UUID(arn_part[1])))
    response['containerInstance']['status'].should.equal('ACTIVE')
    len(response['containerInstance']['registeredResources']).should.equal(0)
    len(response['containerInstance']['remainingResources']).should.equal(0)
    response['containerInstance']['agentConnected'].should.equal(True)
    response['containerInstance']['versionInfo']['agentVersion'].should.equal('1.0.0')
    response['containerInstance']['versionInfo']['agentHash'].should.equal('4023248')
    response['containerInstance']['versionInfo']['dockerVersion'].should.equal('DockerVersion: 1.5.0')


@mock_ec2
@mock_ecs
def test_list_container_instances():
    ecs_client = boto3.client('ecs', region_name='us-east-1')
    ec2 = boto3.resource('ec2', region_name='us-east-1')

    test_cluster_name = 'test_ecs_cluster'
    _ = ecs_client.create_cluster(
        clusterName=test_cluster_name
    )

    instance_to_create = 3
    test_instance_arns = []
    for i in range(0, instance_to_create):
        test_instance = ec2.create_instances(
            ImageId="ami-1234abcd",
            MinCount=1,
            MaxCount=1,
        )[0]

        instance_id_document = json.dumps(
            ec2_utils.generate_instance_identity_document(test_instance)
        )

        response = ecs_client.register_container_instance(
            cluster=test_cluster_name,
            instanceIdentityDocument=instance_id_document)

        test_instance_arns.append(response['containerInstance']['containerInstanceArn'])

    response = ecs_client.list_container_instances(cluster=test_cluster_name)

    len(response['containerInstanceArns']).should.equal(instance_to_create)
    for arn in test_instance_arns:
        response['containerInstanceArns'].should.contain(arn)


@mock_ec2
@mock_ecs
def test_describe_container_instances():
    ecs_client = boto3.client('ecs', region_name='us-east-1')
    ec2 = boto3.resource('ec2', region_name='us-east-1')

    test_cluster_name = 'test_ecs_cluster'
    _ = ecs_client.create_cluster(
        clusterName=test_cluster_name
    )

    instance_to_create = 3
    test_instance_arns = []
    for i in range(0, instance_to_create):
        test_instance = ec2.create_instances(
            ImageId="ami-1234abcd",
            MinCount=1,
            MaxCount=1,
        )[0]

        instance_id_document = json.dumps(
            ec2_utils.generate_instance_identity_document(test_instance)
        )

        response = ecs_client.register_container_instance(
            cluster=test_cluster_name,
            instanceIdentityDocument=instance_id_document)

        test_instance_arns.append(response['containerInstance']['containerInstanceArn'])

    test_instance_ids = list(map((lambda x: x.split('/')[1]), test_instance_arns))
    response = ecs_client.describe_container_instances(cluster=test_cluster_name, containerInstances=test_instance_ids)
    len(response['failures']).should.equal(0)
    len(response['containerInstances']).should.equal(instance_to_create)
    response_arns = [ci['containerInstanceArn'] for ci in response['containerInstances']]
    for arn in test_instance_arns:
        response_arns.should.contain(arn)


@mock_ec2
@mock_ecs
def test_run_task():
    client = boto3.client('ecs', region_name='us-east-1')
    ec2 = boto3.resource('ec2', region_name='us-east-1')

    test_cluster_name = 'test_ecs_cluster'

    _ = client.create_cluster(
        clusterName=test_cluster_name
    )

    test_instance = ec2.create_instances(
        ImageId="ami-1234abcd",
        MinCount=1,
        MaxCount=1,
    )[0]

    instance_id_document = json.dumps(
        ec2_utils.generate_instance_identity_document(test_instance)
    )

    response = client.register_container_instance(
        cluster=test_cluster_name,
        instanceIdentityDocument=instance_id_document
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
    response = client.run_task(
        cluster='test_ecs_cluster',
        overrides={},
        taskDefinition='test_ecs_task',
        count=2,
        startedBy='moto'
    )
    len(response['tasks']).should.equal(2)
    response['tasks'][0]['taskArn'].should.contain('arn:aws:ecs:us-east-1:012345678910:task/')
    response['tasks'][0]['clusterArn'].should.equal('arn:aws:ecs:us-east-1:012345678910:cluster/test_ecs_cluster')
    response['tasks'][0]['taskDefinitionArn'].should.equal('arn:aws:ecs:us-east-1:012345678910:task-definition/test_ecs_task:1')
    response['tasks'][0]['containerInstanceArn'].should.contain('arn:aws:ecs:us-east-1:012345678910:container-instance/')
    response['tasks'][0]['overrides'].should.equal({})
    response['tasks'][0]['lastStatus'].should.equal("RUNNING")
    response['tasks'][0]['desiredStatus'].should.equal("RUNNING")
    response['tasks'][0]['startedBy'].should.equal("moto")
    response['tasks'][0]['stoppedReason'].should.equal("")


@mock_ec2
@mock_ecs
def test_start_task():
    client = boto3.client('ecs', region_name='us-east-1')
    ec2 = boto3.resource('ec2', region_name='us-east-1')

    test_cluster_name = 'test_ecs_cluster'

    _ = client.create_cluster(
        clusterName=test_cluster_name
    )

    test_instance = ec2.create_instances(
        ImageId="ami-1234abcd",
        MinCount=1,
        MaxCount=1,
    )[0]

    instance_id_document = json.dumps(
        ec2_utils.generate_instance_identity_document(test_instance)
    )

    response = client.register_container_instance(
        cluster=test_cluster_name,
        instanceIdentityDocument=instance_id_document
    )

    container_instances = client.list_container_instances(cluster=test_cluster_name)
    container_instance_id = container_instances['containerInstanceArns'][0].split('/')[-1]

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

    response = client.start_task(
        cluster='test_ecs_cluster',
        taskDefinition='test_ecs_task',
        overrides={},
        containerInstances=[container_instance_id],
        startedBy='moto'
    )

    len(response['tasks']).should.equal(1)
    response['tasks'][0]['taskArn'].should.contain('arn:aws:ecs:us-east-1:012345678910:task/')
    response['tasks'][0]['clusterArn'].should.equal('arn:aws:ecs:us-east-1:012345678910:cluster/test_ecs_cluster')
    response['tasks'][0]['taskDefinitionArn'].should.equal('arn:aws:ecs:us-east-1:012345678910:task-definition/test_ecs_task:1')
    response['tasks'][0]['containerInstanceArn'].should.equal('arn:aws:ecs:us-east-1:012345678910:container-instance/{0}'.format(container_instance_id))
    response['tasks'][0]['overrides'].should.equal({})
    response['tasks'][0]['lastStatus'].should.equal("RUNNING")
    response['tasks'][0]['desiredStatus'].should.equal("RUNNING")
    response['tasks'][0]['startedBy'].should.equal("moto")
    response['tasks'][0]['stoppedReason'].should.equal("")


@mock_ec2
@mock_ecs
def test_list_tasks():
    client = boto3.client('ecs', region_name='us-east-1')
    ec2 = boto3.resource('ec2', region_name='us-east-1')

    test_cluster_name = 'test_ecs_cluster'

    _ = client.create_cluster(
        clusterName=test_cluster_name
    )

    test_instance = ec2.create_instances(
        ImageId="ami-1234abcd",
        MinCount=1,
        MaxCount=1,
    )[0]

    instance_id_document = json.dumps(
        ec2_utils.generate_instance_identity_document(test_instance)
    )

    response = client.register_container_instance(
        cluster=test_cluster_name,
        instanceIdentityDocument=instance_id_document
    )

    container_instances = client.list_container_instances(cluster=test_cluster_name)
    container_instance_id = container_instances['containerInstanceArns'][0].split('/')[-1]

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

    _ = client.start_task(
        cluster='test_ecs_cluster',
        taskDefinition='test_ecs_task',
        overrides={},
        containerInstances=[container_instance_id],
        startedBy='foo'
    )

    _ = client.start_task(
        cluster='test_ecs_cluster',
        taskDefinition='test_ecs_task',
        overrides={},
        containerInstances=[container_instance_id],
        startedBy='bar'
    )

    assert len(client.list_tasks()['taskArns']).should.equal(2)
    assert len(client.list_tasks(cluster='test_ecs_cluster')['taskArns']).should.equal(2)
    assert len(client.list_tasks(startedBy='foo')['taskArns']).should.equal(1)


@mock_ec2
@mock_ecs
def test_describe_tasks():
    client = boto3.client('ecs', region_name='us-east-1')
    ec2 = boto3.resource('ec2', region_name='us-east-1')

    test_cluster_name = 'test_ecs_cluster'

    _ = client.create_cluster(
        clusterName=test_cluster_name
    )

    test_instance = ec2.create_instances(
        ImageId="ami-1234abcd",
        MinCount=1,
        MaxCount=1,
    )[0]

    instance_id_document = json.dumps(
        ec2_utils.generate_instance_identity_document(test_instance)
    )

    response = client.register_container_instance(
        cluster=test_cluster_name,
        instanceIdentityDocument=instance_id_document
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
    tasks_arns = [
        task['taskArn'] for task  in client.run_task(
            cluster='test_ecs_cluster',
            overrides={},
            taskDefinition='test_ecs_task',
            count=2,
            startedBy='moto'
        )['tasks']
    ]
    response = client.describe_tasks(
        cluster='test_ecs_cluster',
        tasks=tasks_arns
    )

    len(response['tasks']).should.equal(2)
    set([response['tasks'][0]['taskArn'], response['tasks'][1]['taskArn']]).should.equal(set(tasks_arns))


@mock_ec2
@mock_ecs
def test_stop_task():
    client = boto3.client('ecs', region_name='us-east-1')
    ec2 = boto3.resource('ec2', region_name='us-east-1')

    test_cluster_name = 'test_ecs_cluster'

    _ = client.create_cluster(
        clusterName=test_cluster_name
    )

    test_instance = ec2.create_instances(
        ImageId="ami-1234abcd",
        MinCount=1,
        MaxCount=1,
    )[0]

    instance_id_document = json.dumps(
        ec2_utils.generate_instance_identity_document(test_instance)
    )

    _ = client.register_container_instance(
        cluster=test_cluster_name,
        instanceIdentityDocument=instance_id_document
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
    run_response = client.run_task(
        cluster='test_ecs_cluster',
        overrides={},
        taskDefinition='test_ecs_task',
        count=1,
        startedBy='moto'
    )
    stop_response = client.stop_task(
        cluster='test_ecs_cluster',
        task=run_response['tasks'][0].get('taskArn'),
        reason='moto testing'
    )

    stop_response['task']['taskArn'].should.equal(run_response['tasks'][0].get('taskArn'))
    stop_response['task']['lastStatus'].should.equal('STOPPED')
    stop_response['task']['desiredStatus'].should.equal('STOPPED')
    stop_response['task']['stoppedReason'].should.equal('moto testing')
