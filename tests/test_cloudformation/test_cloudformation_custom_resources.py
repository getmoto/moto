import boto3
import json
import requests
import sure  # noqa # pylint: disable=unused-import
import time

from moto import mock_lambda, mock_cloudformation, mock_logs, mock_s3, settings
from unittest import SkipTest
from uuid import uuid4
from tests.test_awslambda.utilities import wait_for_log_msg
from .fixtures.custom_lambda import get_template


def get_lambda_code():
    pfunc = """
def lambda_handler(event, context):
    # Need to print this, one of the tests verifies the correct input
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
    import cfnresponse
    cfnresponse.send(event, context, cfnresponse.SUCCESS, response_data)
""".format(
        resource_id=f"CustomResource{str(uuid4())[0:6]}"
    )
    return pfunc


@mock_cloudformation
@mock_lambda
@mock_logs
@mock_s3
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
    with sure.ensure(f"Logs should indicate success: \n{logs}"):
        success.should.equal(True)
    # Verify the correct Output was returned
    outputs = get_outputs(cf, stack_name)
    outputs.should.have.length_of(1)
    outputs[0].should.have.key("OutputKey").equals("infokey")
    outputs[0].should.have.key("OutputValue").equals("special value")


@mock_cloudformation
@mock_lambda
@mock_logs
@mock_s3
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
    execution_failed, logs = wait_for_log_msg(
        expected_msg="failed executing http.request", log_group=log_group_name
    )
    execution_failed.should.equal(True)

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


@mock_cloudformation
@mock_lambda
@mock_logs
@mock_s3
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
    stack["Outputs"].should.equal([])
    stack["StackStatus"].should.equal("CREATE_IN_PROGRESS")

    callback_url = f"http://cloudformation.{region_name}.amazonaws.com/cloudformation_{region_name}/cfnresponse?stack={stack_id}"
    data = {
        "Status": "SUCCESS",
        "StackId": stack_id,
        "LogicalResourceId": "CustomInfo",
        "Data": {"info_value": "resultfromthirdpartysystem"},
    }
    requests.post(callback_url, json=data)

    stack = cf.describe_stacks(StackName=stack_id)["Stacks"][0]
    stack["StackStatus"].should.equal("CREATE_COMPLETE")
    stack["Outputs"].should.equal(
        [{"OutputKey": "infokey", "OutputValue": "resultfromthirdpartysystem"}]
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
