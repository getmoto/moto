import boto3
import io
import json
import mock
import os
import sure  # noqa
import time
import zipfile

from moto import mock_lambda, mock_cloudformation, mock_logs, mock_s3, settings
from pprint import pprint
from unittest import SkipTest
from uuid import uuid4
from tests.test_awslambda.utilities import wait_for_log_msg
from .fixtures.custom_lambda import get_template


def get_lambda_code():
    pfunc = """
def lambda_handler(event, context):
    print(event)
    response = dict()
    response["Status"] = "SUCCESS"
    response["StackId"] = event["StackId"]
    response["RequestId"] = event["RequestId"]
    response["LogicalResourceId"] = event["LogicalResourceId"]
    response["PhysicalResourceId"] = "{resource_id}"
    response_data = dict()
    response_data["info_value"] = "special value"
    if event["RequestType"] == "Create":
        response["Data"] = response_data
    print(response)
    print("finished")
    import cfnresponse
    cfnresponse.send(event, context, cfnresponse.SUCCESS, response_data)
    return response
""".format(
        resource_id=f"CustomResource{str(uuid4())[0:6]}"
    )
    return pfunc


@mock_cloudformation
@mock_lambda
@mock_logs
@mock_s3
def test_create_custom_lambda_resource():
    if not settings.TEST_SERVER_MODE:
        raise SkipTest(
            "Needs a standalone MotoServer, as cfnresponse needs to connect to something"
        )
    # Create Lambda-source code
    lambda_content = get_lambda_code()
    # Create cloudformation stack
    stack_name = f"stack{str(uuid4())[0:6]}"
    template_body = get_template(get_lambda_code())
    cf = boto3.client("cloudformation", region_name="us-east-1")
    stack = cf.create_stack(
        StackName=stack_name,
        TemplateBody=json.dumps(template_body),
        Capabilities=["CAPABILITY_IAM"],
    )
    print(stack)
    # Verify CloudWatch contains the correct logs
    log_group_name = get_log_group_name(cf, stack_name)
    success, logs = wait_for_log_msg(expected_msg="finished", log_group=log_group_name)
    print(success)
    print(logs)
    printed_events = [l for l in logs if l.startswith("{'RequestType': 'Create'")]
    printed_events.should.have.length_of(1)
    original_event = json.loads(printed_events[0].replace("'", '"'))
    original_event.should.have.key("RequestType").equals("Create")
    original_event.should.have.key("ServiceToken")  # Should equal Lambda ARN
    original_event.should.have.key("ResponseURL")
    original_event.should.have.key("StackId")
    original_event.should.have.key("RequestId")  # type UUID
    original_event.should.have.key("LogicalResourceId").equals("CustomInfo")
    original_event.should.have.key("ResourceType").equals("Custom::Info")
    original_event.should.have.key("ResourceProperties")
    original_event["ResourceProperties"].should.have.key(
        "ServiceToken"
    )  # Should equal Lambda ARN
    original_event["ResourceProperties"].should.have.key("MyProperty").equals("stuff")
    # Verify the correct Output was returned
    outputs = get_outputs(cf, stack_name)
    outputs.should.have.length_of(1)
    outputs[0].should.have.key("OutputKey").equals("infokey")
    outputs[0].should.have.key("OutputValue").equals("special value")


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
        pprint(fn)
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
        pprint(outputs)
        return outputs
