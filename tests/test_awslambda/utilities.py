import boto3
import io
import pytest
import time
import zipfile

from botocore.exceptions import ClientError
from moto import settings, mock_iam
from uuid import uuid4

_lambda_region = "us-west-2"


def _process_lambda(func_str):
    zip_output = io.BytesIO()
    zip_file = zipfile.ZipFile(zip_output, "w", zipfile.ZIP_DEFLATED)
    zip_file.writestr("lambda_function.py", func_str)
    zip_file.close()
    zip_output.seek(0)
    return zip_output.read()


def get_test_zip_file1():
    pfunc = """
def lambda_handler(event, context):
    print("custom log event")
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

    return {{'id': vol.id, 'state': vol.state, 'size': vol.size}}
""".format(
        base_url="motoserver:5000"
        if settings.TEST_SERVER_MODE
        else "ec2.us-west-2.amazonaws.com"
    )
    return _process_lambda(func_str)


def get_test_zip_file3():
    pfunc = """
def lambda_handler(event, context):
    print("Nr_of_records("+str(len(event['Records']))+")")
    print("get_test_zip_file3 success")
    return event
"""
    return _process_lambda(pfunc)


def get_test_zip_file_error():
    pfunc = """
def lambda_handler(event, context):
    raise Exception('I failed!')
"""
    return _process_lambda(pfunc)


def get_zip_with_multiple_files():
    pfunc = """
from utilities import util_function
def lambda_handler(event, context):
    x = util_function()
    event["msg"] = event["msg"] + x
    return event
"""
    ufunc = """
def util_function():
    return "stuff"
"""
    zip_output = io.BytesIO()
    zip_file = zipfile.ZipFile(zip_output, "a", zipfile.ZIP_DEFLATED)
    zip_file.writestr("lambda_function.py", pfunc)
    zip_file.close()
    zip_file = zipfile.ZipFile(zip_output, "a", zipfile.ZIP_DEFLATED)
    zip_file.writestr("utilities.py", ufunc)
    zip_file.close()
    zip_output.seek(0)
    return zip_output.read()


def create_invalid_lambda(role):
    conn = boto3.client("lambda", _lambda_region)
    zip_content = get_test_zip_file1()
    function_name = str(uuid4())[0:6]
    with pytest.raises(ClientError) as err:
        conn.create_function(
            FunctionName=function_name,
            Runtime="python2.7",
            Role=role,
            Handler="lambda_function.handler",
            Code={"ZipFile": zip_content},
            Description="test lambda function",
            Timeout=3,
            MemorySize=128,
            Publish=True,
        )
    return err


def get_role_name():
    with mock_iam():
        iam = boto3.client("iam", region_name=_lambda_region)
        try:
            return iam.get_role(RoleName="my-role")["Role"]["Arn"]
        except ClientError:
            return iam.create_role(
                RoleName="my-role",
                AssumeRolePolicyDocument="some policy",
                Path="/my-path/",
            )["Role"]["Arn"]


def wait_for_log_msg(expected_msg, log_group):
    logs_conn = boto3.client("logs", region_name="us-east-1")
    received_messages = []
    start = time.time()
    while (time.time() - start) < 30:
        result = logs_conn.describe_log_streams(logGroupName=log_group)
        log_streams = result.get("logStreams")
        if not log_streams:
            time.sleep(1)
            continue

        for log_stream in log_streams:
            result = logs_conn.get_log_events(
                logGroupName=log_group, logStreamName=log_stream["logStreamName"],
            )
            received_messages.extend(
                [event["message"] for event in result.get("events")]
            )
        if expected_msg in received_messages:
            return True, received_messages
        time.sleep(1)
    return False, received_messages
