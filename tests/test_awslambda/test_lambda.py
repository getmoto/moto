from __future__ import unicode_literals

import base64
import botocore.client
import boto3
import hashlib
import io
import json
import zipfile
import sure  # noqa

from freezegun import freeze_time
from moto import mock_lambda, mock_s3, mock_ec2


def _process_lamda(pfunc):
    zip_output = io.BytesIO()
    zip_file = zipfile.ZipFile(zip_output, 'w', zipfile.ZIP_DEFLATED)
    zip_file.writestr('lambda_function.zip', pfunc)
    zip_file.close()
    zip_output.seek(0)
    return zip_output.read()


def get_test_zip_file1():
    pfunc = """
def lambda_handler(event, context):
    return (event, context)
"""
    return _process_lamda(pfunc)


def get_test_zip_file2():
    pfunc = """
def lambda_handler(event, context):
    volume_id = event.get('volume_id')
    print('get volume details for %s' % volume_id)
    import boto3
    ec2 = boto3.resource('ec2', region_name='us-west-2')
    vol = ec2.Volume(volume_id)
    print('Volume - %s  state=%s, size=%s' % (volume_id, vol.state, vol.size))
"""
    return _process_lamda(pfunc)


@mock_lambda
@mock_s3
def test_list_functions():
    conn = boto3.client('lambda', 'us-west-2')
    result = conn.list_functions()
    result['Functions'].should.have.length_of(0)

@mock_lambda
@freeze_time('2015-01-01 00:00:00')
def test_invoke_event_function():
    conn = boto3.client('lambda', 'us-west-2')
    conn.create_function(
        FunctionName='testFunction',
        Runtime='python2.7',
        Role='test-iam-role',
        Handler='lambda_function.handler',
        Code={
            'ZipFile': get_test_zip_file1(),
        },
        Description='test lambda function',
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    success_result = conn.invoke(FunctionName='testFunction', InvocationType='Event', Payload=json.dumps({'msg': 'Mostly Harmless'}))
    success_result["StatusCode"].should.equal(202)

    conn.invoke.when.called_with(
        FunctionName='notAFunction',
        InvocationType='Event',
        Payload='{}'
    ).should.throw(botocore.client.ClientError)


@mock_lambda
@freeze_time('2015-01-01 00:00:00')
def test_invoke_requestresponse_function():
    conn = boto3.client('lambda', 'us-west-2')
    conn.create_function(
        FunctionName='testFunction',
        Runtime='python2.7',
        Role='test-iam-role',
        Handler='lambda_function.handler',
        Code={
            'ZipFile': get_test_zip_file1(),
        },
        Description='test lambda function',
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    success_result = conn.invoke(FunctionName='testFunction', InvocationType='RequestResponse',
                                 Payload=json.dumps({'msg': 'So long and thanks for all the fish'}))
    success_result["StatusCode"].should.equal(202)

    #nasty hack - hope someone has better solution dealing with unicode tests working for Py2 and Py3.
    base64.b64decode(success_result["LogResult"]).decode('utf-8').replace("u'", "'").should.equal("({'msg': 'So long and thanks for all the fish'}, {})\n\n")

@mock_ec2
@mock_lambda
@freeze_time('2015-01-01 00:00:00')
def test_invoke_function_get_ec2_volume():
    conn = boto3.resource("ec2", "us-west-2")
    vol = conn.create_volume(Size=99, AvailabilityZone='us-west-2')
    vol = conn.Volume(vol.id)

    conn = boto3.client('lambda', 'us-west-2')
    conn.create_function(
        FunctionName='testFunction',
        Runtime='python2.7',
        Role='test-iam-role',
        Handler='lambda_function.handler',
        Code={
            'ZipFile': get_test_zip_file2(),
        },
        Description='test lambda function',
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    import json
    success_result = conn.invoke(FunctionName='testFunction', InvocationType='RequestResponse', Payload=json.dumps({'volume_id': vol.id}))
    success_result["StatusCode"].should.equal(202)

    import base64
    msg = 'get volume details for %s\nVolume - %s  state=%s, size=%s\nNone\n\n' % (vol.id, vol.id, vol.state, vol.size)
    # yet again hacky solution to allow code to run tests for python2 and python3 - pls someone fix :(
    base64.b64decode(success_result["LogResult"]).decode('utf-8').replace("u'", "'").should.equal(msg)


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
    zip_content = get_test_zip_file2()

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
    result['ResponseMetadata'].pop('HTTPHeaders', None)  # this is hard to match against, so remove it
    result['ResponseMetadata'].pop('RetryAttempts', None)  # Botocore inserts retry attempts not seen in Python27
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
    zip_content = get_test_zip_file1()
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
    result['ResponseMetadata'].pop('HTTPHeaders', None)  # this is hard to match against, so remove it
    result['ResponseMetadata'].pop('RetryAttempts', None)  # Botocore inserts retry attempts not seen in Python27

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

    zip_content = get_test_zip_file1()
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
    result['ResponseMetadata'].pop('HTTPHeaders', None)  # this is hard to match against, so remove it
    result['ResponseMetadata'].pop('RetryAttempts', None)  # Botocore inserts retry attempts not seen in Python27

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

    zip_content = get_test_zip_file2()
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
    success_result['ResponseMetadata'].pop('HTTPHeaders', None)  # this is hard to match against, so remove it
    success_result['ResponseMetadata'].pop('RetryAttempts', None)  # Botocore inserts retry attempts not seen in Python27

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

    zip_content = get_test_zip_file2()
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
    func['ResponseMetadata'].pop('HTTPHeaders', None)  # this is hard to match against, so remove it
    func['ResponseMetadata'].pop('RetryAttempts', None)  # Botocore inserts retry attempts not seen in Python27

    func.should.equal(expected_function_result)
    conn.delete_function(FunctionName='testFunction')

    conn.list_functions()['Functions'].should.have.length_of(0)
