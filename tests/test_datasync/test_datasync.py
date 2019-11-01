import logging

import boto
import boto3
from moto import mock_datasync


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
    response = client.create_location_s3(S3BucketArn='my_bucket',
                                         Subdirectory='dir',
                                         S3Config={'BucketAccessRoleArn':'role'})
    assert 'LocationArn' in response

'''
@mock_datasync
def test_list_locations():
    client = boto3.client("datasync", region_name="us-east-1")
    response = client.list_locations()
    logging.info ('No locations: {0}'.format(response))

    response = client.create_location_smb(ServerHostname='host',
                                          Subdirectory='somewhere',
                                          User='',
                                          Password='',
                                          AgentArns=['stuff'])
    logging.info ('A location 1 : {0}'.format(response))
    response = client.list_locations()
    logging.info ('A location 2 : {0}'.format(response))

    assert 1 == 0
    #assert response == ["TestLocation"]
'''
