from __future__ import unicode_literals

import boto3
import sure  # noqa
from moto import mock_resourcegroupstaggingapi, mock_s3


@mock_s3
@mock_resourcegroupstaggingapi
def test_get_resources_s3():
    s3_client = boto3.client('s3')

    # Will end up having key1,key2,key3,key4
    response_keys = set()

    # Create 4 buckets
    for i in range(1, 5):
        i_str = str(i)
        s3_client.create_bucket(Bucket='test_bucket' + i_str)
        s3_client.put_bucket_tagging(
            Bucket='test_bucket' + i_str,
            Tagging={'TagSet': [{'Key': 'key' + i_str, 'Value': 'value' + i_str}]}
        )
        response_keys.add('key' + i_str)

    rtapi = boto3.client('resourcegroupstaggingapi')
    resp = rtapi.get_resources(ResourcesPerPage=2)
    for resource in resp['ResourceTagMappingList']:
        response_keys.remove(resource['Tags'][0]['Key'])

    response_keys.should.have.length_of(2)

    resp = rtapi.get_resources(
        ResourcesPerPage=2,
        PaginationToken=resp['PaginationToken']
    )
    for resource in resp['ResourceTagMappingList']:
        response_keys.remove(resource['Tags'][0]['Key'])

    response_keys.should.have.length_of(0)
