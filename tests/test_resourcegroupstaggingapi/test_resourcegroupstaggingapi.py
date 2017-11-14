from __future__ import unicode_literals

import boto3
import sure  # noqa
from moto import mock_resourcegroupstaggingapi, mock_s3, mock_ec2


@mock_s3
@mock_resourcegroupstaggingapi
def test_get_resources_s3():
    # Tests pagenation
    s3_client = boto3.client('s3', region_name='eu-central-1')

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

    rtapi = boto3.client('resourcegroupstaggingapi', region_name='eu-central-1')
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


@mock_ec2
@mock_resourcegroupstaggingapi
def test_get_resources_ec2():
    client = boto3.client('ec2', region_name='eu-central-1')

    instances = client.run_instances(
        ImageId='ami-123',
        MinCount=1,
        MaxCount=1,
        InstanceType='t2.micro',
        TagSpecifications=[
            {
                'ResourceType': 'instance',
                'Tags': [
                    {
                        'Key': 'MY_TAG1',
                        'Value': 'MY_VALUE1',
                    },
                    {
                        'Key': 'MY_TAG2',
                        'Value': 'MY_VALUE2',
                    },
                ],
            },
            {
                'ResourceType': 'instance',
                'Tags': [
                    {
                        'Key': 'MY_TAG3',
                        'Value': 'MY_VALUE3',
                    },
                ]
            },
        ],
    )
    instance_id = instances['Instances'][0]['InstanceId']
    image_id = client.create_image(Name='testami', InstanceId=instance_id)['ImageId']

    client.create_tags(
        Resources=[image_id],
        Tags=[{'Key': 'ami', 'Value': 'test'}]
    )

    rtapi = boto3.client('resourcegroupstaggingapi', region_name='eu-central-1')
    resp = rtapi.get_resources()
    # Check we have 1 entry for Instance, 1 Entry for AMI
    resp['ResourceTagMappingList'].should.have.length_of(2)

    # 1 Entry for AMI
    resp = rtapi.get_resources(ResourceTypeFilters=['ec2:image'])
    resp['ResourceTagMappingList'].should.have.length_of(1)
    resp['ResourceTagMappingList'][0]['ResourceARN'].should.contain('image/')

    # As were iterating the same data, this rules out that the test above was a fluke
    resp = rtapi.get_resources(ResourceTypeFilters=['ec2:instance'])
    resp['ResourceTagMappingList'].should.have.length_of(1)
    resp['ResourceTagMappingList'][0]['ResourceARN'].should.contain('instance/')

    # Basic test of tag filters
    resp = rtapi.get_resources(TagFilters=[{'Key': 'MY_TAG1', 'Values': ['MY_VALUE1', 'some_other_value']}])
    resp['ResourceTagMappingList'].should.have.length_of(1)
    resp['ResourceTagMappingList'][0]['ResourceARN'].should.contain('instance/')


@mock_ec2
@mock_resourcegroupstaggingapi
def test_get_tag_keys_ec2():
    client = boto3.client('ec2', region_name='eu-central-1')

    client.run_instances(
        ImageId='ami-123',
        MinCount=1,
        MaxCount=1,
        InstanceType='t2.micro',
        TagSpecifications=[
            {
                'ResourceType': 'instance',
                'Tags': [
                    {
                        'Key': 'MY_TAG1',
                        'Value': 'MY_VALUE1',
                    },
                    {
                        'Key': 'MY_TAG2',
                        'Value': 'MY_VALUE2',
                    },
                ],
            },
            {
                'ResourceType': 'instance',
                'Tags': [
                    {
                        'Key': 'MY_TAG3',
                        'Value': 'MY_VALUE3',
                    },
                ]
            },
        ],
    )

    rtapi = boto3.client('resourcegroupstaggingapi', region_name='eu-central-1')
    resp = rtapi.get_tag_keys()

    assert len(set(resp['TagKeys']) - {'MY_TAG1', 'MY_TAG2', 'MY_TAG3'}) == 0

    # TODO test pagenation
