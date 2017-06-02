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
from moto import mock_lambda, mock_s3, mock_ec2, settings


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
    return event
"""
    return _process_lamda(pfunc)


def get_test_zip_file2():
    pfunc = """
def lambda_handler(event, context):
    volume_id = event.get('volume_id')
    print('get volume details for %s' % volume_id)
    import boto3
    ec2 = boto3.resource('ec2', region_name='us-west-2', endpoint_url="http://{base_url}")
    vol = ec2.Volume(volume_id)
    print('Volume - %s  state=%s, size=%s' % (volume_id, vol.state, vol.size))
    return event
""".format(base_url="localhost:5000" if settings.TEST_SERVER_MODE else "ec2.us-west-2.amazonaws.com")
    return _process_lamda(pfunc)


@mock_lambda
def test_list_functions():
    conn = boto3.client('lambda', 'us-west-2')
    result = conn.list_functions()
    result['Functions'].should.have.length_of(0)


@mock_lambda
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

    in_data = {'msg': 'So long and thanks for all the fish'}
    success_result = conn.invoke(FunctionName='testFunction', InvocationType='RequestResponse',
                                 Payload=json.dumps(in_data))

    success_result["StatusCode"].should.equal(202)
    base64.b64decode(success_result["LogResult"]).decode(
        'utf-8').should.equal(json.dumps(in_data))
    json.loads(success_result["Payload"].read().decode(
        'utf-8')).should.equal(in_data)


@mock_lambda
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

    conn.invoke.when.called_with(
        FunctionName='notAFunction',
        InvocationType='Event',
        Payload='{}'
    ).should.throw(botocore.client.ClientError)

    in_data = {'msg': 'So long and thanks for all the fish'}
    success_result = conn.invoke(
        FunctionName='testFunction', InvocationType='Event', Payload=json.dumps(in_data))
    success_result["StatusCode"].should.equal(202)
    json.loads(success_result['Payload'].read().decode(
        'utf-8')).should.equal({})


@mock_ec2
@mock_lambda
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

    in_data = {'volume_id': vol.id}
    result = conn.invoke(FunctionName='testFunction',
                         InvocationType='RequestResponse', Payload=json.dumps(in_data))
    result["StatusCode"].should.equal(202)
    msg = 'get volume details for %s\nVolume - %s  state=%s, size=%s\n%s' % (
        vol.id, vol.id, vol.state, vol.size, json.dumps(in_data))
    base64.b64decode(result["LogResult"]).decode('utf-8').should.equal(msg)
    result['Payload'].read().decode('utf-8').should.equal(msg)


@mock_lambda
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
    # this is hard to match against, so remove it
    result['ResponseMetadata'].pop('HTTPHeaders', None)
    # Botocore inserts retry attempts not seen in Python27
    result['ResponseMetadata'].pop('RetryAttempts', None)
    result.pop('LastModified')
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
    # this is hard to match against, so remove it
    result['ResponseMetadata'].pop('HTTPHeaders', None)
    # Botocore inserts retry attempts not seen in Python27
    result['ResponseMetadata'].pop('RetryAttempts', None)
    result.pop('LastModified')

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
    # this is hard to match against, so remove it
    result['ResponseMetadata'].pop('HTTPHeaders', None)
    # Botocore inserts retry attempts not seen in Python27
    result['ResponseMetadata'].pop('RetryAttempts', None)
    result['Configuration'].pop('LastModified')

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
    # this is hard to match against, so remove it
    success_result['ResponseMetadata'].pop('HTTPHeaders', None)
    # Botocore inserts retry attempts not seen in Python27
    success_result['ResponseMetadata'].pop('RetryAttempts', None)

    success_result.should.equal({'ResponseMetadata': {'HTTPStatusCode': 204}})

    conn.delete_function.when.called_with(
        FunctionName='testFunctionThatDoesntExist').should.throw(botocore.client.ClientError)


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
    func = conn.list_functions()['Functions'][0]
    func.pop('LastModified')
    func.should.equal(expected_function_result['Configuration'])

    func = conn.get_function(FunctionName='testFunction')
    # this is hard to match against, so remove it
    func['ResponseMetadata'].pop('HTTPHeaders', None)
    # Botocore inserts retry attempts not seen in Python27
    func['ResponseMetadata'].pop('RetryAttempts', None)
    func['Configuration'].pop('LastModified')

    func.should.equal(expected_function_result)
    conn.delete_function(FunctionName='testFunction')

    conn.list_functions()['Functions'].should.have.length_of(0)


@mock_lambda
def test_invoke_lambda_error():
    lambda_fx = """
    def lambda_handler(event, context):
        raise Exception('failsauce')
    """
    zip_output = io.BytesIO()
    zip_file = zipfile.ZipFile(zip_output, 'w', zipfile.ZIP_DEFLATED)
    zip_file.writestr('lambda_function.zip', lambda_fx)
    zip_file.close()
    zip_output.seek(0)

    client = boto3.client('lambda', region_name='us-east-1')
    client.create_function(
        FunctionName='test-lambda-fx',
        Runtime='python2.7',
        Role='test-iam-role',
        Handler='lambda_function.lambda_handler',
        Description='test lambda function',
        Timeout=3,
        MemorySize=128,
        Publish=True,
        Code={
            'ZipFile': zip_output.read()
        },
    )

    result = client.invoke(
        FunctionName='test-lambda-fx',
        InvocationType='RequestResponse',
        LogType='Tail'
    )

    assert 'FunctionError' in result
    assert result['FunctionError'] == 'Handled'
