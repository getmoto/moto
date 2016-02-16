from __future__ import unicode_literals

import boto3
import hashlib
import io
import zipfile
import sure  # noqa

from freezegun import freeze_time
from moto import mock_lambda


@mock_lambda
def test_list_functions():
    conn = boto3.client('lambda', 'us-west-2')

    result = conn.list_functions()

    result['Functions'].should.have.length_of(0)


@mock_lambda
@freeze_time('2015-01-01 00:00:00')
def test_create_function_from_aws_bucket():
    conn = boto3.client('lambda', 'us-west-2')

    result = conn.create_function(
        FunctionName='testFunction',
        Runtime='python2.7',
        Role='test-iam-role',
        Handler='lambda_function.handler',
        Code={
            'S3Bucket': 'test-bucket',
            'S3Key': 'test.zip',
        },
        Description='test lambda function',
        Timeout=3,
        MemorySize=128,
        Publish=True,
        # boto3 doesnt support it
        # VpcConfig={
        #     "SecurityGroupIds": ["sg-123abc"],
        #     "SubnetIds": ["subnet-123abc"],
        #     "VpcId": "vpc-123abc"
        # },
    )
    result.should.equal({
        'FunctionName': 'testFunction',
        'FunctionArn': 'arn:aws:lambda:123456789012:function:testFunction',
        'Runtime': 'python2.7',
        'Role': 'test-iam-role',
        'Handler': 'lambda_function.handler',
        'CodeSize': 123,
        'Description': 'test lambda function',
        'Timeout': 3,
        'MemorySize': 128,
        'LastModified': '2015-01-01 00:00:00',
        'CodeSha256': 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
        'Version': '$LATEST',
        # boto3 doesnt support it
        # VpcConfig={
        #     "SecurityGroupIds": ["sg-123abc"],
        #     "SubnetIds": ["subnet-123abc"],
        #     "VpcId": "vpc-123abc"
        # },

        'ResponseMetadata': {'HTTPStatusCode': 201},
    })


@mock_lambda
@freeze_time('2015-01-01 00:00:00')
def test_create_function_from_zipfile():
    conn = boto3.client('lambda', 'us-west-2')

    zip_output = io.BytesIO()
    with zipfile.ZipFile(zip_output, 'w') as f:
        f.writestr('lambda_function.py', b'''\
def handler(event, context):
    return "hello world"
''')
    zip_output.seek(0)
    zip_content = zip_output.read()
    result = conn.create_function(
        FunctionName='testFunction',
        Runtime='python2.7',
        Role='test-iam-role',
        Handler='lambda_function.handler',
        Code={
            'ZipFile': zip_content,
        },
        Description='test lambda function',
        Timeout=3,
        MemorySize=128,
        Publish=True,
        # boto3 doesnt support it
        # VpcConfig={
        #     "SecurityGroupIds": ["sg-123abc"],
        #     "SubnetIds": ["subnet-123abc"],
        #     "VpcId": "vpc-123abc"
        # },
    )
    result.should.equal({
        'FunctionName': 'testFunction',
        'FunctionArn': 'arn:aws:lambda:123456789012:function:testFunction',
        'Runtime': 'python2.7',
        'Role': 'test-iam-role',
        'Handler': 'lambda_function.handler',
        'CodeSize': len(zip_content),
        'Description': 'test lambda function',
        'Timeout': 3,
        'MemorySize': 128,
        'LastModified': '2015-01-01 00:00:00',
        'CodeSha256': hashlib.sha256(zip_content).hexdigest(),
        'Version': '$LATEST',
        # boto3 doesnt support it
        # VpcConfig={
        #     "SecurityGroupIds": ["sg-123abc"],
        #     "SubnetIds": ["subnet-123abc"],
        #     "VpcId": "vpc-123abc"
        # },

        'ResponseMetadata': {'HTTPStatusCode': 201},
    })


@mock_lambda
@freeze_time('2015-01-01 00:00:00')
def test_get_function():
    conn = boto3.client('lambda', 'us-west-2')

    conn.create_function(
        FunctionName='testFunction',
        Runtime='python2.7',
        Role='test-iam-role',
        Handler='lambda_function.handler',
        Code={
            'S3Bucket': 'test-bucket',
            'S3Key': 'test.zip',
        },
        Description='test lambda function',
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    result = conn.get_function(FunctionName='testFunction')

    result.should.equal({
        "Code": {
            "Location": "s3://lambda-functions.aws.amazon.com/test.zip",
            "RepositoryType": "S3"
        },
        "Configuration": {
            "CodeSha256": 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
            "CodeSize": 123,
            "Description": "test lambda function",
            "FunctionArn": "arn:aws:lambda:123456789012:function:testFunction",
            "FunctionName": "testFunction",
            "Handler": "lambda_function.handler",
            "LastModified": "2015-01-01 00:00:00",
            "MemorySize": 128,
            "Role": "test-iam-role",
            "Runtime": "python2.7",
            "Timeout": 3,
            "Version": '$LATEST',
            # "VpcConfig": {
            #     "SecurityGroupIds": [
            #         "string"
            #     ],
            #     "SubnetIds": [
            #         "string"
            #     ],
            #     "VpcId": "string"
            # }
        },
        'ResponseMetadata': {'HTTPStatusCode': 200},
    })



@mock_lambda
def test_delete_function():
    conn = boto3.client('lambda', 'us-west-2')

    conn.create_function(
        FunctionName='testFunction',
        Runtime='python2.7',
        Role='test-iam-role',
        Handler='lambda_function.handler',
        Code={
            'S3Bucket': 'test-bucket',
            'S3Key': 'test.zip',
        },
        Description='test lambda function',
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    success_result = conn.delete_function(FunctionName='testFunction')

    success_result.should.equal({'ResponseMetadata': {'HTTPStatusCode': 204}})

    # FIXME:!!!!
    # not_found_result = conn.delete_function(FunctionName='testFunctionThatDoesntExist')
    # not_found_result.should.equal({'ResponseMetadata': {'HTTPStatusCode': 404}})


@mock_lambda
@freeze_time('2015-01-01 00:00:00')
def test_list_create_list_get_delete_list():
    """
    test `list -> create -> list -> get -> delete -> list` integration

    """
    conn = boto3.client('lambda', 'us-west-2')

    conn.list_functions()['Functions'].should.have.length_of(0)

    conn.create_function(
        FunctionName='testFunction',
        Runtime='python2.7',
        Role='test-iam-role',
        Handler='lambda_function.handler',
        Code={
            'S3Bucket': 'test-bucket',
            'S3Key': 'test.zip',
        },
        Description='test lambda function',
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )
    expected_function_result = {
        "Code": {
            "Location": "s3://lambda-functions.aws.amazon.com/test.zip",
            "RepositoryType": "S3"
        },
        "Configuration": {
            "CodeSha256": 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
            "CodeSize": 123,
            "Description": "test lambda function",
            "FunctionArn": "arn:aws:lambda:123456789012:function:testFunction",
            "FunctionName": "testFunction",
            "Handler": "lambda_function.handler",
            "LastModified": "2015-01-01 00:00:00",
            "MemorySize": 128,
            "Role": "test-iam-role",
            "Runtime": "python2.7",
            "Timeout": 3,
            "Version": '$LATEST',
            # "VpcConfig": {
            #     "SecurityGroupIds": [
            #         "string"
            #     ],
            #     "SubnetIds": [
            #         "string"
            #     ],
            #     "VpcId": "string"
            # }
        },
        'ResponseMetadata': {'HTTPStatusCode': 200},
    }
    conn.list_functions()['Functions'].should.equal([expected_function_result['Configuration']])

    conn.get_function(FunctionName='testFunction').should.equal(expected_function_result)
    conn.delete_function(FunctionName='testFunction')

    conn.list_functions()['Functions'].should.have.length_of(0)
