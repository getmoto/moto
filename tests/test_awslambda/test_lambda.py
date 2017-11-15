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

_lambda_region = 'us-west-2'


def _process_lambda(func_str):
    zip_output = io.BytesIO()
    zip_file = zipfile.ZipFile(zip_output, 'w', zipfile.ZIP_DEFLATED)
    zip_file.writestr('lambda_function.py', func_str)
    zip_file.close()
    zip_output.seek(0)
    return zip_output.read()


def get_test_zip_file1():
    pfunc = """
def lambda_handler(event, context):
    return event
"""
    return _process_lambda(pfunc)


def get_test_zip_file2():
    func_str = """
import boto3

def lambda_handler(event, context):
    ec2 = boto3.resource('ec2', region_name='us-west-2', endpoint_url='http://{base_url}')

    volume_id = event.get('volume_id')
    vol = ec2.Volume(volume_id)

    print('get volume details for %s\\nVolume - %s  state=%s, size=%s' % (volume_id, volume_id, vol.state, vol.size))
    return event
""".format(base_url="motoserver:5000" if settings.TEST_SERVER_MODE else "ec2.us-west-2.amazonaws.com")
    return _process_lambda(func_str)


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
        Handler='lambda_function.lambda_handler',
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
    result_obj = json.loads(
        base64.b64decode(success_result["LogResult"]).decode('utf-8'))

    result_obj.should.equal(in_data)

    payload = success_result["Payload"].read().decode('utf-8')
    json.loads(payload).should.equal(in_data)


@mock_lambda
def test_invoke_event_function():
    conn = boto3.client('lambda', 'us-west-2')
    conn.create_function(
        FunctionName='testFunction',
        Runtime='python2.7',
        Role='test-iam-role',
        Handler='lambda_function.lambda_handler',
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


if settings.TEST_SERVER_MODE:
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
            Handler='lambda_function.lambda_handler',
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

        log_result = base64.b64decode(result["LogResult"]).decode('utf-8')

        # fix for running under travis (TODO: investigate why it has an extra newline)
        log_result = log_result.replace('\n\n', '\n')
        log_result.should.equal(msg)

        payload = result['Payload'].read().decode('utf-8')

        # fix for running under travis (TODO: investigate why it has an extra newline)
        payload = payload.replace('\n\n', '\n')
        payload.should.equal(msg)


@mock_lambda
def test_create_based_on_s3_with_missing_bucket():
    conn = boto3.client('lambda', 'us-west-2')

    conn.create_function.when.called_with(
        FunctionName='testFunction',
        Runtime='python2.7',
        Role='test-iam-role',
        Handler='lambda_function.lambda_handler',
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
        Handler='lambda_function.lambda_handler',
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
        'FunctionArn': 'arn:aws:lambda:{}:123456789012:function:testFunction:$LATEST'.format(_lambda_region),
        'Runtime': 'python2.7',
        'Role': 'test-iam-role',
        'Handler': 'lambda_function.lambda_handler',
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
        Handler='lambda_function.lambda_handler',
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
        'FunctionArn': 'arn:aws:lambda:{}:123456789012:function:testFunction:$LATEST'.format(_lambda_region),
        'Runtime': 'python2.7',
        'Role': 'test-iam-role',
        'Handler': 'lambda_function.lambda_handler',
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
        Handler='lambda_function.lambda_handler',
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

    result['Code']['Location'].should.equal('s3://awslambda-{0}-tasks.s3-{0}.amazonaws.com/test.zip'.format(_lambda_region))
    result['Code']['RepositoryType'].should.equal('S3')

    result['Configuration']['CodeSha256'].should.equal(hashlib.sha256(zip_content).hexdigest())
    result['Configuration']['CodeSize'].should.equal(len(zip_content))
    result['Configuration']['Description'].should.equal('test lambda function')
    result['Configuration'].should.contain('FunctionArn')
    result['Configuration']['FunctionName'].should.equal('testFunction')
    result['Configuration']['Handler'].should.equal('lambda_function.lambda_handler')
    result['Configuration']['MemorySize'].should.equal(128)
    result['Configuration']['Role'].should.equal('test-iam-role')
    result['Configuration']['Runtime'].should.equal('python2.7')
    result['Configuration']['Timeout'].should.equal(3)
    result['Configuration']['Version'].should.equal('$LATEST')
    result['Configuration'].should.contain('VpcConfig')

    # Test get function with
    result = conn.get_function(FunctionName='testFunction', Qualifier='$LATEST')
    result['Configuration']['Version'].should.equal('$LATEST')


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
        Handler='lambda_function.lambda_handler',
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
def test_publish():
    s3_conn = boto3.client('s3', 'us-west-2')
    s3_conn.create_bucket(Bucket='test-bucket')

    zip_content = get_test_zip_file2()
    s3_conn.put_object(Bucket='test-bucket', Key='test.zip', Body=zip_content)
    conn = boto3.client('lambda', 'us-west-2')

    conn.create_function(
        FunctionName='testFunction',
        Runtime='python2.7',
        Role='test-iam-role',
        Handler='lambda_function.lambda_handler',
        Code={
            'S3Bucket': 'test-bucket',
            'S3Key': 'test.zip',
        },
        Description='test lambda function',
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    function_list = conn.list_functions()
    function_list['Functions'].should.have.length_of(1)
    latest_arn = function_list['Functions'][0]['FunctionArn']

    conn.publish_version(FunctionName='testFunction')

    function_list = conn.list_functions()
    function_list['Functions'].should.have.length_of(2)

    # #SetComprehension ;-)
    published_arn = list({f['FunctionArn'] for f in function_list['Functions']} - {latest_arn})[0]
    published_arn.should.contain('testFunction:1')

    conn.delete_function(FunctionName='testFunction', Qualifier='1')

    function_list = conn.list_functions()
    function_list['Functions'].should.have.length_of(1)
    function_list['Functions'][0]['FunctionArn'].should.contain('testFunction:$LATEST')



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
        Handler='lambda_function.lambda_handler',
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
            "Location": "s3://awslambda-{0}-tasks.s3-{0}.amazonaws.com/test.zip".format(_lambda_region),
            "RepositoryType": "S3"
        },
        "Configuration": {
            "CodeSha256": hashlib.sha256(zip_content).hexdigest(),
            "CodeSize": len(zip_content),
            "Description": "test lambda function",
            "FunctionArn": 'arn:aws:lambda:{}:123456789012:function:testFunction:$LATEST'.format(_lambda_region),
            "FunctionName": "testFunction",
            "Handler": "lambda_function.lambda_handler",
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
    zip_file.writestr('lambda_function.py', lambda_fx)
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


@mock_lambda
@mock_s3
def test_tags():
    """
    test list_tags -> tag_resource -> list_tags -> tag_resource -> list_tags -> untag_resource -> list_tags integration
    """
    s3_conn = boto3.client('s3', 'us-west-2')
    s3_conn.create_bucket(Bucket='test-bucket')

    zip_content = get_test_zip_file2()
    s3_conn.put_object(Bucket='test-bucket', Key='test.zip', Body=zip_content)
    conn = boto3.client('lambda', 'us-west-2')

    function = conn.create_function(
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

    # List tags when there are none
    conn.list_tags(
        Resource=function['FunctionArn']
    )['Tags'].should.equal(dict())

    # List tags when there is one
    conn.tag_resource(
        Resource=function['FunctionArn'],
        Tags=dict(spam='eggs')
    )['ResponseMetadata']['HTTPStatusCode'].should.equal(200)
    conn.list_tags(
        Resource=function['FunctionArn']
    )['Tags'].should.equal(dict(spam='eggs'))

    # List tags when another has been added
    conn.tag_resource(
        Resource=function['FunctionArn'],
        Tags=dict(foo='bar')
    )['ResponseMetadata']['HTTPStatusCode'].should.equal(200)
    conn.list_tags(
        Resource=function['FunctionArn']
    )['Tags'].should.equal(dict(spam='eggs', foo='bar'))

    # Untag resource
    conn.untag_resource(
        Resource=function['FunctionArn'],
        TagKeys=['spam', 'trolls']
    )['ResponseMetadata']['HTTPStatusCode'].should.equal(204)
    conn.list_tags(
        Resource=function['FunctionArn']
    )['Tags'].should.equal(dict(foo='bar'))

    # Untag a tag that does not exist (no error and no change)
    conn.untag_resource(
        Resource=function['FunctionArn'],
        TagKeys=['spam']
    )['ResponseMetadata']['HTTPStatusCode'].should.equal(204)


@mock_lambda
def test_tags_not_found():
    """
    Test list_tags and tag_resource when the lambda with the given arn does not exist
    """
    conn = boto3.client('lambda', 'us-west-2')
    conn.list_tags.when.called_with(
        Resource='arn:aws:lambda:123456789012:function:not-found'
    ).should.throw(botocore.client.ClientError)

    conn.tag_resource.when.called_with(
        Resource='arn:aws:lambda:123456789012:function:not-found',
        Tags=dict(spam='eggs')
    ).should.throw(botocore.client.ClientError)

    conn.untag_resource.when.called_with(
        Resource='arn:aws:lambda:123456789012:function:not-found',
        TagKeys=['spam']
    ).should.throw(botocore.client.ClientError)


@mock_lambda
def test_invoke_async_function():
    conn = boto3.client('lambda', 'us-west-2')
    conn.create_function(
        FunctionName='testFunction',
        Runtime='python2.7',
        Role='test-iam-role',
        Handler='lambda_function.lambda_handler',
        Code={'ZipFile': get_test_zip_file1()},
        Description='test lambda function',
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    success_result = conn.invoke_async(
        FunctionName='testFunction', 
        InvokeArgs=json.dumps({'test': 'event'})
        )

    success_result['Status'].should.equal(202)


@mock_lambda
@freeze_time('2015-01-01 00:00:00')
def test_get_function_created_with_zipfile():
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

    response = conn.get_function(
        FunctionName='testFunction'
    )
    response['Configuration'].pop('LastModified')

    response['ResponseMetadata']['HTTPStatusCode'].should.equal(200)
    assert len(response['Code']) == 2
    assert response['Code']['RepositoryType'] == 'S3'
    assert response['Code']['Location'].startswith('s3://awslambda-{0}-tasks.s3-{0}.amazonaws.com'.format(_lambda_region))
    response['Configuration'].should.equal(
        {
            "CodeSha256": hashlib.sha256(zip_content).hexdigest(),
            "CodeSize": len(zip_content),
            "Description": "test lambda function",
            "FunctionArn":'arn:aws:lambda:{}:123456789012:function:testFunction:$LATEST'.format(_lambda_region),
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
    )


@mock_lambda
def add_function_permission():
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

    response = conn.add_permission(
        FunctionName='testFunction',
        StatementId='1',
        Action="lambda:InvokeFunction",
        Principal='432143214321',
        SourceArn="arn:aws:lambda:us-west-2:account-id:function:helloworld",
        SourceAccount='123412341234',
        EventSourceToken='blah',
        Qualifier='2'
    )
    assert 'Statement' in response
    res = json.loads(response['Statement'])
    assert res['Action'] == "lambda:InvokeFunction"


@mock_lambda
def get_function_policy():
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

    response = conn.add_permission(
        FunctionName='testFunction',
        StatementId='1',
        Action="lambda:InvokeFunction",
        Principal='432143214321',
        SourceArn="arn:aws:lambda:us-west-2:account-id:function:helloworld",
        SourceAccount='123412341234',
        EventSourceToken='blah',
        Qualifier='2'
    )

    response = conn.get_policy(
        FunctionName='testFunction'
    )

    assert 'Policy' in response
    assert isinstance(response['Policy'], str)
    res = json.loads(response['Policy'])
    assert res['Statement'][0]['Action'] == 'lambda:InvokeFunction'
