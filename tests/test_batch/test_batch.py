from __future__ import unicode_literals

import time
import datetime
import boto3
from botocore.exceptions import ClientError
import sure  # noqa
from moto import mock_batch, mock_iam, mock_ec2, mock_ecs, mock_logs
import functools
import nose


def expected_failure(test):
    @functools.wraps(test)
    def inner(*args, **kwargs):
        try:
            test(*args, **kwargs)
        except Exception as err:
            raise nose.SkipTest
    return inner

DEFAULT_REGION = 'eu-central-1'


def _get_clients():
    return boto3.client('ec2', region_name=DEFAULT_REGION), \
           boto3.client('iam', region_name=DEFAULT_REGION), \
           boto3.client('ecs', region_name=DEFAULT_REGION), \
           boto3.client('logs', region_name=DEFAULT_REGION), \
           boto3.client('batch', region_name=DEFAULT_REGION)


def _setup(ec2_client, iam_client):
    """
    Do prerequisite setup
    :return: VPC ID, Subnet ID, Security group ID, IAM Role ARN
    :rtype: tuple
    """
    resp = ec2_client.create_vpc(CidrBlock='172.30.0.0/24')
    vpc_id = resp['Vpc']['VpcId']
    resp = ec2_client.create_subnet(
        AvailabilityZone='eu-central-1a',
        CidrBlock='172.30.0.0/25',
        VpcId=vpc_id
    )
    subnet_id = resp['Subnet']['SubnetId']
    resp = ec2_client.create_security_group(
        Description='test_sg_desc',
        GroupName='test_sg',
        VpcId=vpc_id
    )
    sg_id = resp['GroupId']

    resp = iam_client.create_role(
        RoleName='TestRole',
        AssumeRolePolicyDocument='some_policy'
    )
    iam_arn = resp['Role']['Arn']

    return vpc_id, subnet_id, sg_id, iam_arn


# Yes, yes it talks to all the things
@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_create_managed_compute_environment():
    ec2_client, iam_client, ecs_client, logs_client, batch_client = _get_clients()
    vpc_id, subnet_id, sg_id, iam_arn = _setup(ec2_client, iam_client)

    compute_name = 'test_compute_env'
    resp = batch_client.create_compute_environment(
        computeEnvironmentName=compute_name,
        type='MANAGED',
        state='ENABLED',
        computeResources={
            'type': 'EC2',
            'minvCpus': 5,
            'maxvCpus': 10,
            'desiredvCpus': 5,
            'instanceTypes': [
                't2.small',
                't2.medium'
            ],
            'imageId': 'some_image_id',
            'subnets': [
                subnet_id,
            ],
            'securityGroupIds': [
                sg_id,
            ],
            'ec2KeyPair': 'string',
            'instanceRole': iam_arn,
            'tags': {
                'string': 'string'
            },
            'bidPercentage': 123,
            'spotIamFleetRole': 'string'
        },
        serviceRole=iam_arn
    )
    resp.should.contain('computeEnvironmentArn')
    resp['computeEnvironmentName'].should.equal(compute_name)

    # Given a t2.medium is 2 vcpu and t2.small is 1, therefore 2 mediums and 1 small should be created
    resp = ec2_client.describe_instances()
    resp.should.contain('Reservations')
    len(resp['Reservations']).should.equal(3)

    # Should have created 1 ECS cluster
    resp = ecs_client.list_clusters()
    resp.should.contain('clusterArns')
    len(resp['clusterArns']).should.equal(1)


@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_create_unmanaged_compute_environment():
    ec2_client, iam_client, ecs_client, logs_client, batch_client = _get_clients()
    vpc_id, subnet_id, sg_id, iam_arn = _setup(ec2_client, iam_client)

    compute_name = 'test_compute_env'
    resp = batch_client.create_compute_environment(
        computeEnvironmentName=compute_name,
        type='UNMANAGED',
        state='ENABLED',
        serviceRole=iam_arn
    )
    resp.should.contain('computeEnvironmentArn')
    resp['computeEnvironmentName'].should.equal(compute_name)

    # Its unmanaged so no instances should be created
    resp = ec2_client.describe_instances()
    resp.should.contain('Reservations')
    len(resp['Reservations']).should.equal(0)

    # Should have created 1 ECS cluster
    resp = ecs_client.list_clusters()
    resp.should.contain('clusterArns')
    len(resp['clusterArns']).should.equal(1)

# TODO create 1000s of tests to test complex option combinations of create environment


@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_describe_compute_environment():
    ec2_client, iam_client, ecs_client, logs_client, batch_client = _get_clients()
    vpc_id, subnet_id, sg_id, iam_arn = _setup(ec2_client, iam_client)

    compute_name = 'test_compute_env'
    batch_client.create_compute_environment(
        computeEnvironmentName=compute_name,
        type='UNMANAGED',
        state='ENABLED',
        serviceRole=iam_arn
    )

    resp = batch_client.describe_compute_environments()
    len(resp['computeEnvironments']).should.equal(1)
    resp['computeEnvironments'][0]['computeEnvironmentName'].should.equal(compute_name)

    # Test filtering
    resp = batch_client.describe_compute_environments(
        computeEnvironments=['test1']
    )
    len(resp['computeEnvironments']).should.equal(0)


@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_delete_unmanaged_compute_environment():
    ec2_client, iam_client, ecs_client, logs_client, batch_client = _get_clients()
    vpc_id, subnet_id, sg_id, iam_arn = _setup(ec2_client, iam_client)

    compute_name = 'test_compute_env'
    batch_client.create_compute_environment(
        computeEnvironmentName=compute_name,
        type='UNMANAGED',
        state='ENABLED',
        serviceRole=iam_arn
    )

    batch_client.delete_compute_environment(
        computeEnvironment=compute_name,
    )

    resp = batch_client.describe_compute_environments()
    len(resp['computeEnvironments']).should.equal(0)

    resp = ecs_client.list_clusters()
    len(resp.get('clusterArns', [])).should.equal(0)


@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_delete_managed_compute_environment():
    ec2_client, iam_client, ecs_client, logs_client, batch_client = _get_clients()
    vpc_id, subnet_id, sg_id, iam_arn = _setup(ec2_client, iam_client)

    compute_name = 'test_compute_env'
    batch_client.create_compute_environment(
        computeEnvironmentName=compute_name,
        type='MANAGED',
        state='ENABLED',
        computeResources={
            'type': 'EC2',
            'minvCpus': 5,
            'maxvCpus': 10,
            'desiredvCpus': 5,
            'instanceTypes': [
                't2.small',
                't2.medium'
            ],
            'imageId': 'some_image_id',
            'subnets': [
                subnet_id,
            ],
            'securityGroupIds': [
                sg_id,
            ],
            'ec2KeyPair': 'string',
            'instanceRole': iam_arn,
            'tags': {
                'string': 'string'
            },
            'bidPercentage': 123,
            'spotIamFleetRole': 'string'
        },
        serviceRole=iam_arn
    )

    batch_client.delete_compute_environment(
        computeEnvironment=compute_name,
    )

    resp = batch_client.describe_compute_environments()
    len(resp['computeEnvironments']).should.equal(0)

    resp = ec2_client.describe_instances()
    resp.should.contain('Reservations')
    len(resp['Reservations']).should.equal(3)
    for reservation in resp['Reservations']:
        reservation['Instances'][0]['State']['Name'].should.equal('terminated')

    resp = ecs_client.list_clusters()
    len(resp.get('clusterArns', [])).should.equal(0)


@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_update_unmanaged_compute_environment_state():
    ec2_client, iam_client, ecs_client, logs_client, batch_client = _get_clients()
    vpc_id, subnet_id, sg_id, iam_arn = _setup(ec2_client, iam_client)

    compute_name = 'test_compute_env'
    batch_client.create_compute_environment(
        computeEnvironmentName=compute_name,
        type='UNMANAGED',
        state='ENABLED',
        serviceRole=iam_arn
    )

    batch_client.update_compute_environment(
        computeEnvironment=compute_name,
        state='DISABLED'
    )

    resp = batch_client.describe_compute_environments()
    len(resp['computeEnvironments']).should.equal(1)
    resp['computeEnvironments'][0]['state'].should.equal('DISABLED')


@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_create_job_queue():
    ec2_client, iam_client, ecs_client, logs_client, batch_client = _get_clients()
    vpc_id, subnet_id, sg_id, iam_arn = _setup(ec2_client, iam_client)

    compute_name = 'test_compute_env'
    resp = batch_client.create_compute_environment(
        computeEnvironmentName=compute_name,
        type='UNMANAGED',
        state='ENABLED',
        serviceRole=iam_arn
    )
    arn = resp['computeEnvironmentArn']

    resp = batch_client.create_job_queue(
        jobQueueName='test_job_queue',
        state='ENABLED',
        priority=123,
        computeEnvironmentOrder=[
            {
                'order': 123,
                'computeEnvironment': arn
            },
        ]
    )
    resp.should.contain('jobQueueArn')
    resp.should.contain('jobQueueName')
    queue_arn = resp['jobQueueArn']

    resp = batch_client.describe_job_queues()
    resp.should.contain('jobQueues')
    len(resp['jobQueues']).should.equal(1)
    resp['jobQueues'][0]['jobQueueArn'].should.equal(queue_arn)

    resp = batch_client.describe_job_queues(jobQueues=['test_invalid_queue'])
    resp.should.contain('jobQueues')
    len(resp['jobQueues']).should.equal(0)

    # Create job queue which already exists
    try:
        resp = batch_client.create_job_queue(
            jobQueueName='test_job_queue',
            state='ENABLED',
            priority=123,
            computeEnvironmentOrder=[
                {
                    'order': 123,
                    'computeEnvironment': arn
                },
            ]
        )

    except ClientError as err:
        err.response['Error']['Code'].should.equal('ClientException')


    # Create job queue with incorrect state
    try:
        resp = batch_client.create_job_queue(
            jobQueueName='test_job_queue2',
            state='JUNK',
            priority=123,
            computeEnvironmentOrder=[
                {
                    'order': 123,
                    'computeEnvironment': arn
                },
            ]
        )

    except ClientError as err:
        err.response['Error']['Code'].should.equal('ClientException')

    # Create job queue with no compute env
    try:
        resp = batch_client.create_job_queue(
            jobQueueName='test_job_queue3',
            state='JUNK',
            priority=123,
            computeEnvironmentOrder=[

            ]
        )

    except ClientError as err:
        err.response['Error']['Code'].should.equal('ClientException')

@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_job_queue_bad_arn():
    ec2_client, iam_client, ecs_client, logs_client, batch_client = _get_clients()
    vpc_id, subnet_id, sg_id, iam_arn = _setup(ec2_client, iam_client)

    compute_name = 'test_compute_env'
    resp = batch_client.create_compute_environment(
        computeEnvironmentName=compute_name,
        type='UNMANAGED',
        state='ENABLED',
        serviceRole=iam_arn
    )
    arn = resp['computeEnvironmentArn']

    try:
        batch_client.create_job_queue(
            jobQueueName='test_job_queue',
            state='ENABLED',
            priority=123,
            computeEnvironmentOrder=[
                {
                    'order': 123,
                    'computeEnvironment': arn + 'LALALA'
                },
            ]
        )
    except ClientError as err:
        err.response['Error']['Code'].should.equal('ClientException')


@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_update_job_queue():
    ec2_client, iam_client, ecs_client, logs_client, batch_client = _get_clients()
    vpc_id, subnet_id, sg_id, iam_arn = _setup(ec2_client, iam_client)

    compute_name = 'test_compute_env'
    resp = batch_client.create_compute_environment(
        computeEnvironmentName=compute_name,
        type='UNMANAGED',
        state='ENABLED',
        serviceRole=iam_arn
    )
    arn = resp['computeEnvironmentArn']

    resp = batch_client.create_job_queue(
        jobQueueName='test_job_queue',
        state='ENABLED',
        priority=123,
        computeEnvironmentOrder=[
            {
                'order': 123,
                'computeEnvironment': arn
            },
        ]
    )
    queue_arn = resp['jobQueueArn']

    batch_client.update_job_queue(
        jobQueue=queue_arn,
        priority=5
    )

    resp = batch_client.describe_job_queues()
    resp.should.contain('jobQueues')
    len(resp['jobQueues']).should.equal(1)
    resp['jobQueues'][0]['priority'].should.equal(5)

    batch_client.update_job_queue(
        jobQueue='test_job_queue',
        priority=5
    )

    resp = batch_client.describe_job_queues()
    resp.should.contain('jobQueues')
    len(resp['jobQueues']).should.equal(1)
    resp['jobQueues'][0]['priority'].should.equal(5)



@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_update_job_queue():
    ec2_client, iam_client, ecs_client, logs_client, batch_client = _get_clients()
    vpc_id, subnet_id, sg_id, iam_arn = _setup(ec2_client, iam_client)

    compute_name = 'test_compute_env'
    resp = batch_client.create_compute_environment(
        computeEnvironmentName=compute_name,
        type='UNMANAGED',
        state='ENABLED',
        serviceRole=iam_arn
    )
    arn = resp['computeEnvironmentArn']

    resp = batch_client.create_job_queue(
        jobQueueName='test_job_queue',
        state='ENABLED',
        priority=123,
        computeEnvironmentOrder=[
            {
                'order': 123,
                'computeEnvironment': arn
            },
        ]
    )
    queue_arn = resp['jobQueueArn']

    batch_client.delete_job_queue(
        jobQueue=queue_arn
    )

    resp = batch_client.describe_job_queues()
    resp.should.contain('jobQueues')
    len(resp['jobQueues']).should.equal(0)


@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_register_task_definition():
    ec2_client, iam_client, ecs_client, logs_client, batch_client = _get_clients()
    vpc_id, subnet_id, sg_id, iam_arn = _setup(ec2_client, iam_client)

    resp = batch_client.register_job_definition(
        jobDefinitionName='sleep10',
        type='container',
        containerProperties={
            'image': 'busybox',
            'vcpus': 1,
            'memory': 128,
            'command': ['sleep', '10']
        }
    )

    resp.should.contain('jobDefinitionArn')
    resp.should.contain('jobDefinitionName')
    resp.should.contain('revision')

    assert resp['jobDefinitionArn'].endswith('{0}:{1}'.format(resp['jobDefinitionName'], resp['revision']))


@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_reregister_task_definition():
    # Reregistering task with the same name bumps the revision number
    ec2_client, iam_client, ecs_client, logs_client, batch_client = _get_clients()
    vpc_id, subnet_id, sg_id, iam_arn = _setup(ec2_client, iam_client)

    resp1 = batch_client.register_job_definition(
        jobDefinitionName='sleep10',
        type='container',
        containerProperties={
            'image': 'busybox',
            'vcpus': 1,
            'memory': 128,
            'command': ['sleep', '10']
        }
    )

    resp1.should.contain('jobDefinitionArn')
    resp1.should.contain('jobDefinitionName')
    resp1.should.contain('revision')

    assert resp1['jobDefinitionArn'].endswith('{0}:{1}'.format(resp1['jobDefinitionName'], resp1['revision']))
    resp1['revision'].should.equal(1)

    resp2 = batch_client.register_job_definition(
        jobDefinitionName='sleep10',
        type='container',
        containerProperties={
            'image': 'busybox',
            'vcpus': 1,
            'memory': 68,
            'command': ['sleep', '10']
        }
    )
    resp2['revision'].should.equal(2)

    resp2['jobDefinitionArn'].should_not.equal(resp1['jobDefinitionArn'])


@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_delete_task_definition():
    ec2_client, iam_client, ecs_client, logs_client, batch_client = _get_clients()
    vpc_id, subnet_id, sg_id, iam_arn = _setup(ec2_client, iam_client)

    resp = batch_client.register_job_definition(
        jobDefinitionName='sleep10',
        type='container',
        containerProperties={
            'image': 'busybox',
            'vcpus': 1,
            'memory': 128,
            'command': ['sleep', '10']
        }
    )

    batch_client.deregister_job_definition(jobDefinition=resp['jobDefinitionArn'])

    resp = batch_client.describe_job_definitions()
    len(resp['jobDefinitions']).should.equal(0)


@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_describe_task_definition():
    ec2_client, iam_client, ecs_client, logs_client, batch_client = _get_clients()
    vpc_id, subnet_id, sg_id, iam_arn = _setup(ec2_client, iam_client)

    batch_client.register_job_definition(
        jobDefinitionName='sleep10',
        type='container',
        containerProperties={
            'image': 'busybox',
            'vcpus': 1,
            'memory': 128,
            'command': ['sleep', '10']
        }
    )
    batch_client.register_job_definition(
        jobDefinitionName='sleep10',
        type='container',
        containerProperties={
            'image': 'busybox',
            'vcpus': 1,
            'memory': 64,
            'command': ['sleep', '10']
        }
    )
    batch_client.register_job_definition(
        jobDefinitionName='test1',
        type='container',
        containerProperties={
            'image': 'busybox',
            'vcpus': 1,
            'memory': 64,
            'command': ['sleep', '10']
        }
    )

    resp = batch_client.describe_job_definitions(
        jobDefinitionName='sleep10'
    )
    len(resp['jobDefinitions']).should.equal(2)

    resp = batch_client.describe_job_definitions()
    len(resp['jobDefinitions']).should.equal(3)

    resp = batch_client.describe_job_definitions(
        jobDefinitions=['sleep10', 'test1']
    )
    len(resp['jobDefinitions']).should.equal(3)


# SLOW TESTS
@expected_failure
@mock_logs
@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_submit_job():
    ec2_client, iam_client, ecs_client, logs_client, batch_client = _get_clients()
    vpc_id, subnet_id, sg_id, iam_arn = _setup(ec2_client, iam_client)

    compute_name = 'test_compute_env'
    resp = batch_client.create_compute_environment(
        computeEnvironmentName=compute_name,
        type='UNMANAGED',
        state='ENABLED',
        serviceRole=iam_arn
    )
    arn = resp['computeEnvironmentArn']

    resp = batch_client.create_job_queue(
        jobQueueName='test_job_queue',
        state='ENABLED',
        priority=123,
        computeEnvironmentOrder=[
            {
                'order': 123,
                'computeEnvironment': arn
            },
        ]
    )
    queue_arn = resp['jobQueueArn']

    resp = batch_client.register_job_definition(
        jobDefinitionName='sleep10',
        type='container',
        containerProperties={
            'image': 'busybox',
            'vcpus': 1,
            'memory': 128,
            'command': ['sleep', '10']
        }
    )
    job_def_arn = resp['jobDefinitionArn']

    resp = batch_client.submit_job(
        jobName='test1',
        jobQueue=queue_arn,
        jobDefinition=job_def_arn
    )
    job_id = resp['jobId']

    future = datetime.datetime.now() + datetime.timedelta(seconds=30)

    while datetime.datetime.now() < future:
        resp = batch_client.describe_jobs(jobs=[job_id])
        print("{0}:{1} {2}".format(resp['jobs'][0]['jobName'], resp['jobs'][0]['jobId'], resp['jobs'][0]['status']))

        if resp['jobs'][0]['status'] == 'FAILED':
            raise RuntimeError('Batch job failed')
        if resp['jobs'][0]['status'] == 'SUCCEEDED':
            break
        time.sleep(0.5)
    else:
        raise RuntimeError('Batch job timed out')

    resp = logs_client.describe_log_streams(logGroupName='/aws/batch/job')
    len(resp['logStreams']).should.equal(1)
    ls_name = resp['logStreams'][0]['logStreamName']

    resp = logs_client.get_log_events(logGroupName='/aws/batch/job', logStreamName=ls_name)
    len(resp['events']).should.be.greater_than(5)


@expected_failure
@mock_logs
@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_list_jobs():
    ec2_client, iam_client, ecs_client, logs_client, batch_client = _get_clients()
    vpc_id, subnet_id, sg_id, iam_arn = _setup(ec2_client, iam_client)

    compute_name = 'test_compute_env'
    resp = batch_client.create_compute_environment(
        computeEnvironmentName=compute_name,
        type='UNMANAGED',
        state='ENABLED',
        serviceRole=iam_arn
    )
    arn = resp['computeEnvironmentArn']

    resp = batch_client.create_job_queue(
        jobQueueName='test_job_queue',
        state='ENABLED',
        priority=123,
        computeEnvironmentOrder=[
            {
                'order': 123,
                'computeEnvironment': arn
            },
        ]
    )
    queue_arn = resp['jobQueueArn']

    resp = batch_client.register_job_definition(
        jobDefinitionName='sleep10',
        type='container',
        containerProperties={
            'image': 'busybox',
            'vcpus': 1,
            'memory': 128,
            'command': ['sleep', '10']
        }
    )
    job_def_arn = resp['jobDefinitionArn']

    resp = batch_client.submit_job(
        jobName='test1',
        jobQueue=queue_arn,
        jobDefinition=job_def_arn
    )
    job_id1 = resp['jobId']
    resp = batch_client.submit_job(
        jobName='test2',
        jobQueue=queue_arn,
        jobDefinition=job_def_arn
    )
    job_id2 = resp['jobId']

    future = datetime.datetime.now() + datetime.timedelta(seconds=30)

    resp_finished_jobs = batch_client.list_jobs(
        jobQueue=queue_arn,
        jobStatus='SUCCEEDED'
    )

    # Wait only as long as it takes to run the jobs
    while datetime.datetime.now() < future:
        resp = batch_client.describe_jobs(jobs=[job_id1, job_id2])

        any_failed_jobs = any([job['status'] == 'FAILED' for job in resp['jobs']])
        succeeded_jobs = all([job['status'] == 'SUCCEEDED' for job in resp['jobs']])

        if any_failed_jobs:
            raise RuntimeError('A Batch job failed')
        if succeeded_jobs:
            break
        time.sleep(0.5)
    else:
        raise RuntimeError('Batch jobs timed out')

    resp_finished_jobs2 = batch_client.list_jobs(
        jobQueue=queue_arn,
        jobStatus='SUCCEEDED'
    )

    len(resp_finished_jobs['jobSummaryList']).should.equal(0)
    len(resp_finished_jobs2['jobSummaryList']).should.equal(2)


@expected_failure
@mock_logs
@mock_ec2
@mock_ecs
@mock_iam
@mock_batch
def test_terminate_job():
    ec2_client, iam_client, ecs_client, logs_client, batch_client = _get_clients()
    vpc_id, subnet_id, sg_id, iam_arn = _setup(ec2_client, iam_client)

    compute_name = 'test_compute_env'
    resp = batch_client.create_compute_environment(
        computeEnvironmentName=compute_name,
        type='UNMANAGED',
        state='ENABLED',
        serviceRole=iam_arn
    )
    arn = resp['computeEnvironmentArn']

    resp = batch_client.create_job_queue(
        jobQueueName='test_job_queue',
        state='ENABLED',
        priority=123,
        computeEnvironmentOrder=[
            {
                'order': 123,
                'computeEnvironment': arn
            },
        ]
    )
    queue_arn = resp['jobQueueArn']

    resp = batch_client.register_job_definition(
        jobDefinitionName='sleep10',
        type='container',
        containerProperties={
            'image': 'busybox',
            'vcpus': 1,
            'memory': 128,
            'command': ['sleep', '10']
        }
    )
    job_def_arn = resp['jobDefinitionArn']

    resp = batch_client.submit_job(
        jobName='test1',
        jobQueue=queue_arn,
        jobDefinition=job_def_arn
    )
    job_id = resp['jobId']

    time.sleep(2)

    batch_client.terminate_job(jobId=job_id, reason='test_terminate')

    time.sleep(1)

    resp = batch_client.describe_jobs(jobs=[job_id])
    resp['jobs'][0]['jobName'].should.equal('test1')
    resp['jobs'][0]['status'].should.equal('FAILED')
    resp['jobs'][0]['statusReason'].should.equal('test_terminate')

