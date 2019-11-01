import logging

import boto
import boto3
from moto import mock_datasync


'''
Endpoints I need to test:
start_task_execution
cancel_task_execution
describe_task_execution
'''



@mock_datasync
def test_create_location_smb():
    client = boto3.client("datasync", region_name="us-east-1")
    response = client.create_location_smb(ServerHostname='host',
                                          Subdirectory='somewhere',
                                          User='',
                                          Password='',
                                          AgentArns=['stuff'])
    assert 'LocationArn' in response


@mock_datasync
def test_create_location_s3():
    client = boto3.client("datasync", region_name="us-east-1")
    response = client.create_location_s3(S3BucketArn='arn:aws:s3:::my_bucket',
                                         Subdirectory='dir',
                                         S3Config={'BucketAccessRoleArn':'role'})
    assert 'LocationArn' in response

@mock_datasync
def test_list_locations():
    client = boto3.client("datasync", region_name="us-east-1")
    response = client.list_locations()
    # TODO BJORN check if Locations exists when there are none
    assert len(response['Locations']) == 0

    response = client.create_location_smb(ServerHostname='host',
                                          Subdirectory='somewhere',
                                          User='',
                                          Password='',
                                          AgentArns=['stuff'])
    response = client.list_locations()
    assert len(response['Locations']) == 1
    assert response['Locations'][0]['LocationUri'] == 'smb://host/somewhere'

    response = client.create_location_s3(S3BucketArn='arn:aws:s3:::my_bucket',
                                         S3Config={'BucketAccessRoleArn':'role'})

    response = client.list_locations()
    assert len(response['Locations']) == 2
    assert response['Locations'][1]['LocationUri'] == 's3://my_bucket'

    response = client.create_location_s3(S3BucketArn='arn:aws:s3:::my_bucket',
                                         Subdirectory='subdir',
                                         S3Config={'BucketAccessRoleArn':'role'})

    response = client.list_locations()
    assert len(response['Locations']) == 3
    assert response['Locations'][2]['LocationUri'] == 's3://my_bucket/subdir'

@mock_datasync
def test_create_task():
    client = boto3.client("datasync", region_name="us-east-1")
    # TODO BJORN check if task can be created when there are no locations
    response = client.create_task(
        SourceLocationArn='1',
        DestinationLocationArn='2'
    )
    assert 'TaskArn' in response

@mock_datasync
def test_list_tasks():
    client = boto3.client("datasync", region_name="us-east-1")
    response = client.create_task(
        SourceLocationArn='1',
        DestinationLocationArn='2',
    )
    response = client.create_task(
        SourceLocationArn='3',
        DestinationLocationArn='4',
        Name='task_name'
    )
    response = client.list_tasks()
    tasks = response['Tasks']
    assert len(tasks) == 2

    task = tasks[0]
    assert task['Status'] == 'AVAILABLE'
    assert 'Name' not in task

    task = tasks[1]
    assert task['Status'] == 'AVAILABLE'
    assert task['Name'] == 'task_name'

@mock_datasync
def test_describe_task():
    client = boto3.client("datasync", region_name="us-east-1")
    
    response = client.create_task(
            SourceLocationArn='3',
            DestinationLocationArn='4',
            Name='task_name'
        )
    task_arn = response['TaskArn']    

    response = client.describe_task(
        TaskArn=task_arn
    )
    
    assert 'TaskArn' in response
    assert 'Status' in response
    assert 'SourceLocationArn' in response
    assert 'DestinationLocationArn' in response

@mock_datasync
def test_start_task_execution():
    client = boto3.client("datasync", region_name="us-east-1")
    
    response = client.create_task(
            SourceLocationArn='3',
            DestinationLocationArn='4',
            Name='task_name'
        )
    task_arn = response['TaskArn']    
    
    response = client.start_task_execution(
        TaskArn=task_arn
    )
    assert 'TaskExecutionArn' in response
