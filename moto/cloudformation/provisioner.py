import json
from moto import mock_ec2, mock_s3


def parse_cloudformation(template_path):
    with open(template_path, 'r') as file:
        template = json.load(file)
    return template['Resources']


@mock_ec2
@mock_s3
def provision_resources(resources):
    for resource_id, resource in resources.items():
        resource_type = resource['Type']
        properties = resource['Properties']

        if resource_type == 'AWS::EC2::Instance':
            ec2 = boto3.client('ec2')
            ec2.run_instances(
                ImageId=properties['ImageId'],
                InstanceType=properties['InstanceType'],
                MaxCount=1,
                MinCount=1
            )
        elif resource_type == 'AWS::S3::Bucket':
            s3 = boto3.client('s3')
            s3.create_bucket(Bucket=properties['BucketName'])


# Usage
template_path = 'path/to/cloudformation.json'
resources = parse_cloudformation(template_path)
provision_resources(resources)