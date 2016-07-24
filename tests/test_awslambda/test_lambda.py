from __future__ import unicode_literals

import botocore.client
import boto3
import hashlib
import io
import zipfile
import sure  # noqa

from freezegun import freeze_time
from moto import mock_lambda, mock_s3


def get_test_zip_file():
    zip_output = io.BytesIO()
    zip_file = zipfile.ZipFile(zip_output, 'w')
    zip_file.writestr('lambda_function.py', b'''\
def handler(event, context):
    return "hello world"
''')
    zip_file.close()
    zip_output.seek(0)
    return zip_output.read()


@mock_lambda
def test_list_functions():
    conn = boto3.client('lambda', 'us-west-2')

    result = conn.list_functions()

    result['Functions'].should.have.length_of(0)


@mock_lambda
@mock_s3
@freeze_time('2015-01-01 00:00:00')
def test_invoke_function():
    conn = boto3.client('lambda', 'us-west-2')

    zip_content = get_test_zip_file()
    conn.create_function(
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
    )

    success_result = conn.invoke(FunctionName='testFunction', InvocationType='Event', Payload='{}')
    success_result["StatusCode"].should.equal(200)

    conn.invoke.when.called_with(
        FunctionName='notAFunction',
        InvocationType='Event',
        Payload='{}'
    ).should.throw(botocore.client.ClientError)

    success_result = conn.invoke(FunctionName='testFunction', InvocationType='RequestResponse', Payload='{}')
    success_result["StatusCode"].should.equal(200)

    import base64
    base64.b64decode(success_result["LogResult"]).decode('utf-8').should.equal("Some log file output...")


@mock_lambda
@freeze_time('2015-01-01 00:00:00')
def test_create_based_on_s3_with_missing_bucket():
    conn = boto3.client('lambda', 'us-west-2')

    conn.create_function.when.called_with(
        FunctionName='testFunction',
        Runtime='python2.7',
        Role='test-iam-role',
        Handler='lambda_function.handler',
        Code={
            'S3Bucket': 'this-bucket-does-not-exist',
            'S3Key': 'test.zip',
        },
        Description='test lambda function',
        Timeout=3,
        MemorySize=128,
        Publish=True,
        VpcConfig={
            "SecurityGroupIds": ["sg-123abc"],
            "SubnetIds": ["subnet-123abc"],
        },
    ).should.throw(botocore.client.ClientError)


@mock_lambda
@mock_s3
@freeze_time('2015-01-01 00:00:00')
def test_create_function_from_aws_bucket():
    s3_conn = boto3.client('s3', 'us-west-2')
    s3_conn.create_bucket(Bucket='test-bucket')

    zip_content = get_test_zip_file()
    s3_conn.put_object(Bucket='test-bucket', Key='test.zip', Body=zip_content)
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
        VpcConfig={
            "SecurityGroupIds": ["sg-123abc"],
            "SubnetIds": ["subnet-123abc"],
        },
    )
    result['ResponseMetadata'].pop('HTTPHeaders', None) # this is hard to match against, so remove it
    result.should.equal({
        'FunctionName': 'testFunction',
        'FunctionArn': 'arn:aws:lambda:123456789012:function:testFunction',
        'Runtime': 'python2.7',
        'Role': 'test-iam-role',
        'Handler': 'lambda_function.handler',
        "CodeSha256": hashlib.sha256(zip_content).hexdigest(),
        "CodeSize": len(zip_content),
        'Description': 'test lambda function',
        'Timeout': 3,
        'MemorySize': 128,
        'LastModified': '2015-01-01 00:00:00',
        'Version': '$LATEST',
        'VpcConfig': {
            "SecurityGroupIds": ["sg-123abc"],
            "SubnetIds": ["subnet-123abc"],
            "VpcId": "vpc-123abc"
        },

        'ResponseMetadata': {'HTTPStatusCode': 201},
    })


@mock_lambda
@freeze_time('2015-01-01 00:00:00')
def test_create_function_from_zipfile():
    conn = boto3.client('lambda', 'us-west-2')

    zip_content = get_test_zip_file()
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
    )
    result['ResponseMetadata'].pop('HTTPHeaders', None) # this is hard to match against, so remove it
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
        'VpcConfig': {
            "SecurityGroupIds": [],
            "SubnetIds": [],
        },

        'ResponseMetadata': {'HTTPStatusCode': 201},
    })


@mock_lambda
@mock_s3
@freeze_time('2015-01-01 00:00:00')
def test_get_function():
    s3_conn = boto3.client('s3', 'us-west-2')
    s3_conn.create_bucket(Bucket='test-bucket')

    zip_content = get_test_zip_file()
    s3_conn.put_object(Bucket='test-bucket', Key='test.zip', Body=zip_content)
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
    result['ResponseMetadata'].pop('HTTPHeaders', None) # this is hard to match against, so remove it

    result.should.equal({
        "Code": {
            "Location": "s3://lambda-functions.aws.amazon.com/test.zip",
            "RepositoryType": "S3"
        },
        "Configuration": {
            "CodeSha256": hashlib.sha256(zip_content).hexdigest(),
            "CodeSize": len(zip_content),
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
            "VpcConfig": {
                "SecurityGroupIds": [],
                "SubnetIds": [],
            }
        },
        'ResponseMetadata': {'HTTPStatusCode': 200},
    })



@mock_lambda
@mock_s3
def test_delete_function():
    s3_conn = boto3.client('s3', 'us-west-2')
    s3_conn.create_bucket(Bucket='test-bucket')

    zip_content = get_test_zip_file()
    s3_conn.put_object(Bucket='test-bucket', Key='test.zip', Body=zip_content)
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
    success_result['ResponseMetadata'].pop('HTTPHeaders', None) # this is hard to match against, so remove it
    success_result.should.equal({'ResponseMetadata': {'HTTPStatusCode': 204}})

    conn.delete_function.when.called_with(FunctionName='testFunctionThatDoesntExist').should.throw(botocore.client.ClientError)


@mock_lambda
@mock_s3
@freeze_time('2015-01-01 00:00:00')
def test_list_create_list_get_delete_list():
    """
    test `list -> create -> list -> get -> delete -> list` integration

    """
    s3_conn = boto3.client('s3', 'us-west-2')
    s3_conn.create_bucket(Bucket='test-bucket')

    zip_content = get_test_zip_file()
    s3_conn.put_object(Bucket='test-bucket', Key='test.zip', Body=zip_content)
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
            "CodeSha256": hashlib.sha256(zip_content).hexdigest(),
            "CodeSize": len(zip_content),
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
            "VpcConfig": {
                "SecurityGroupIds": [],
                "SubnetIds": [],
            }
        },
        'ResponseMetadata': {'HTTPStatusCode': 200},
    }
    conn.list_functions()['Functions'].should.equal([expected_function_result['Configuration']])

    func = conn.get_function(FunctionName='testFunction')
    func['ResponseMetadata'].pop('HTTPHeaders', None) # this is hard to match against, so remove it
    func.should.equal(expected_function_result)
    conn.delete_function(FunctionName='testFunction')

    conn.list_functions()['Functions'].should.have.length_of(0)
