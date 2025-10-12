import json
import time
from unittest import SkipTest
from uuid import uuid4

import boto3
import pytest
import requests
from botocore.exceptions import ClientError

from moto import mock_aws, settings
from tests.test_awslambda.utilities import wait_for_log_msg

from ..markers import requires_docker
from .fixtures.custom_lambda import get_template, get_template_for_unknown_lambda


def get_lambda_code():
    return f"""
def lambda_handler(event, context):
    # Need to print this, one of the tests verifies the correct input
    print(event)
    response = dict()
    response["Status"] = "SUCCESS"
    response["StackId"] = event["StackId"]
    response["RequestId"] = event["RequestId"]
    response["LogicalResourceId"] = event["LogicalResourceId"]
    response["PhysicalResourceId"] = "CustomResource{str(uuid4())[0:6]}"
    response_data = dict()
    response_data["info_value"] = "special value"
    if event["RequestType"] == "Create":
        response["Data"] = response_data
    import cfnresponse
    cfnresponse.send(event, context, cfnresponse.SUCCESS, response_data)
"""


@mock_aws
def test_create_custom_lambda_resource():
    #########
    # Integration test using a Custom Resource
    # Create a Lambda
    # CF will call the Lambda
    # The Lambda should call CF, to indicate success (using the cfnresponse-module)
    # This HTTP request will include any outputs that are now stored against the stack
    # TEST: verify that this output is persisted
    ##########
    if not settings.TEST_SERVER_MODE:
        raise SkipTest(
            "Needs a standalone MotoServer, as cfnresponse needs to connect to something"
        )
    # Create cloudformation stack
    stack_name = f"stack{str(uuid4())[0:6]}"
    template_body = get_template(get_lambda_code())
    cf = boto3.client("cloudformation", region_name="us-east-1")
    cf.create_stack(
        StackName=stack_name,
        TemplateBody=json.dumps(template_body),
        Capabilities=["CAPABILITY_IAM"],
    )
    # Verify CloudWatch contains the correct logs
    log_group_name = get_log_group_name(cf, stack_name)
    success, logs = wait_for_log_msg(
        expected_msg="Status code: 200", log_group=log_group_name
    )
    assert success, f"Logs should indicate success: \n{logs}"

    # Verify the correct Output was returned
    outputs = get_outputs(cf, stack_name)
    assert len(outputs) == 1
    assert outputs[0]["OutputKey"] == "infokey"
    assert outputs[0]["OutputValue"] == "special value"


@mock_aws
@requires_docker
def test_create_custom_lambda_resource__verify_cfnresponse_failed():
    #########
    # Integration test using a Custom Resource
    # Create a Lambda
    # CF will call the Lambda
    # The Lambda should call CF --- this will fail, as we cannot make a HTTP request to the in-memory moto decorators
    # TEST: verify that the original event was send to the Lambda correctly
    # TEST: verify that a failure message appears in the CloudwatchLogs
    ##########
    if settings.TEST_SERVER_MODE:
        raise SkipTest("Verify this fails if MotoServer is not running")
    # Create cloudformation stack
    stack_name = f"stack{str(uuid4())[0:6]}"
    template_body = get_template(get_lambda_code())
    cf = boto3.client("cloudformation", region_name="us-east-1")
    cf.create_stack(
        StackName=stack_name,
        TemplateBody=json.dumps(template_body),
        Capabilities=["CAPABILITY_IAM"],
    )
    # Verify CloudWatch contains the correct logs
    log_group_name = get_log_group_name(cf, stack_name)
    # urllib< 2 will emit the `failed executing http.request` message
    # urllib>=2 will emit the StatusCode=400 message
    execution_failed, logs = wait_for_log_msg(
        expected_msg=["failed executing http.request", "Status code: 400"],
        log_group=log_group_name,
    )
    assert execution_failed is True, logs

    printed_events = [
        line for line in logs if line.startswith("{'RequestType': 'Create'")
    ]
    assert len(printed_events) == 1
    original_event = json.loads(printed_events[0].replace("'", '"'))
    assert original_event["RequestType"] == "Create"
    assert "ServiceToken" in original_event  # Should equal Lambda ARN
    assert "ResponseURL" in original_event
    assert "StackId" in original_event
    assert "RequestId" in original_event  # type UUID
    assert original_event["LogicalResourceId"] == "CustomInfo"
    assert original_event["ResourceType"] == "Custom::Info"
    assert "ResourceProperties" in original_event
    assert (
        "ServiceToken" in original_event["ResourceProperties"]
    )  # Should equal Lambda ARN
    assert original_event["ResourceProperties"]["MyProperty"] == "stuff"


@mock_aws
def test_create_custom_lambda_resource__verify_manual_request():
    #########
    # Integration test using a Custom Resource
    # Create a Lambda
    # CF will call the Lambda
    # The Lambda should call CF --- this will fail, as we cannot make a HTTP request to the in-memory moto decorators
    # So we'll make this HTTP request manually
    # TEST: verify that the stack has a CREATE_IN_PROGRESS status before making the HTTP request
    # TEST: verify that the stack has a CREATE_COMPLETE status afterwards
    ##########
    if settings.TEST_SERVER_MODE:
        raise SkipTest(
            "Verify HTTP request can be made manually if MotoServer is not running"
        )
    # Create cloudformation stack
    stack_name = f"stack{str(uuid4())[0:6]}"
    template_body = get_template(get_lambda_code())
    region_name = "eu-north-1"
    cf = boto3.client("cloudformation", region_name=region_name)
    stack = cf.create_stack(
        StackName=stack_name,
        TemplateBody=json.dumps(template_body),
        Capabilities=["CAPABILITY_IAM"],
    )
    stack_id = stack["StackId"]
    stack = cf.describe_stacks(StackName=stack_id)["Stacks"][0]
    assert "Outputs" not in stack
    assert stack["StackStatus"] == "CREATE_IN_PROGRESS"

    callback_url = f"http://cloudformation.{region_name}.amazonaws.com/cloudformation_{region_name}/cfnresponse?stack={stack_id}"
    data = {
        "Status": "SUCCESS",
        "StackId": stack_id,
        "LogicalResourceId": "CustomInfo",
        "Data": {"info_value": "resultfromthirdpartysystem"},
    }
    requests.post(callback_url, json=data)

    stack = cf.describe_stacks(StackName=stack_id)["Stacks"][0]
    assert stack["StackStatus"] == "CREATE_COMPLETE"
    assert stack["Outputs"] == [
        {
            "OutputKey": "infokey",
            "OutputValue": "resultfromthirdpartysystem",
            "Description": "A very important value",
        },
    ]

    # AWSlambda will not have logged anything
    log_group_name = get_log_group_name(cf=cf, stack_name=stack_name)
    success, logs = wait_for_log_msg(
        expected_msg="Status code: 200", log_group=log_group_name, wait_time=5
    )
    assert success is False
    assert len(logs) == 0


@mock_aws
def test_create_custom_lambda_resource__unknown_arn():
    # Try to create a Lambda with an unknown ARN
    # Verify that this fails in a predictable manner
    cf = boto3.client("cloudformation", region_name="eu-north-1")
    with pytest.raises(ClientError) as exc:
        cf.create_stack(
            StackName=f"stack{str(uuid4())[0:6]}",
            TemplateBody=json.dumps(get_template_for_unknown_lambda()),
            Capabilities=["CAPABILITY_IAM"],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationError"
    assert (
        err["Message"]
        == "Template error: instance of Fn::GetAtt references undefined resource InfoFunction"
    )


def get_log_group_name(cf, stack_name):
    resources = cf.describe_stack_resources(StackName=stack_name)["StackResources"]
    start = time.time()
    while (time.time() - start) < 5:
        fns = [
            r
            for r in resources
            if r["ResourceType"] == "AWS::Lambda::Function"
            and "PhysicalResourceId" in r
        ]
        if not fns:
            time.sleep(1)
            resources = cf.describe_stack_resources(StackName=stack_name)[
                "StackResources"
            ]
            continue

        fn = fns[0]
        resource_id = fn["PhysicalResourceId"]
        return f"/aws/lambda/{resource_id}"
    raise Exception("Could not find log group name in time")


def get_outputs(cf, stack_name):
    stack = cf.describe_stacks(StackName=stack_name)["Stacks"][0]
    start = time.time()
    while (time.time() - start) < 5:
        status = stack["StackStatus"]
        if status != "CREATE_COMPLETE":
            time.sleep(1)
            stack = cf.describe_stacks(StackName=stack_name)["Stacks"][0]
            continue

        outputs = stack["Outputs"]
        return outputs
