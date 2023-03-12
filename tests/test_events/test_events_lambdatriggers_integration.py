import boto3
import json

from moto import mock_events, mock_iam, mock_lambda, mock_logs, mock_s3
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from ..markers import requires_docker
from ..test_awslambda.utilities import get_test_zip_file1, wait_for_log_msg


@mock_events
@mock_iam
@mock_lambda
@mock_logs
@mock_s3
@requires_docker
def test_creating_bucket__invokes_lambda():
    iam_client = boto3.client("iam", "us-east-1")
    lambda_client = boto3.client("lambda", "us-east-1")
    events_client = boto3.client("events", "us-east-1")
    s3_client = boto3.client("s3", "us-east-1")

    role = iam_client.create_role(
        RoleName="foobar",
        AssumeRolePolicyDocument="{}",
    )["Role"]

    func = lambda_client.create_function(
        FunctionName="foobar",
        Runtime="python3.8",
        Role=role["Arn"],
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": get_test_zip_file1()},
    )

    events_client.put_rule(
        Name="foobarrule",
        EventPattern="""{
                "source": [
                    "aws.s3"
                ],
                "detail-type": [
                    "AWS API Call via CloudTrail"
                ],
                "detail": {
                    "eventSource": [
                        "s3.amazonaws.com"
                    ],
                    "eventName": [
                        "CreateBucket"
                    ]
                }
            }""",
        State="ENABLED",
        RoleArn=role["Arn"],
    )

    events_client.put_targets(
        Rule="foobarrule",
        Targets=[
            {
                "Id": "n/a",
                "Arn": func["FunctionArn"],
                "RoleArn": role["Arn"],
            }
        ],
    )

    bucket_name = "foobar"
    s3_client.create_bucket(
        ACL="public-read-write",
        Bucket=bucket_name,
    )

    expected_msg = '"detail-type":"Object Created"'
    log_group = f"/aws/lambda/{bucket_name}"
    msg_showed_up, all_logs = wait_for_log_msg(expected_msg, log_group, wait_time=5)

    assert (
        msg_showed_up
    ), "Lambda was not invoked after creating an S3 bucket. All logs: " + str(all_logs)

    event = json.loads(list([line for line in all_logs if expected_msg in line])[-1])

    event.should.have.key("detail-type").equals("Object Created")
    event.should.have.key("source").equals("aws.s3")
    event.should.have.key("account").equals(ACCOUNT_ID)
    event.should.have.key("time")
    event.should.have.key("region").equals("us-east-1")
    event.should.have.key("resources").equals([f"arn:aws:s3:::{bucket_name}"])


@mock_events
@mock_iam
@mock_lambda
@mock_logs
@mock_s3
def test_create_disabled_rule():
    iam_client = boto3.client("iam", "us-east-1")
    lambda_client = boto3.client("lambda", "us-east-1")
    events_client = boto3.client("events", "us-east-1")
    s3_client = boto3.client("s3", "us-east-1")

    role = iam_client.create_role(
        RoleName="foobar",
        AssumeRolePolicyDocument="{}",
    )["Role"]

    func = lambda_client.create_function(
        FunctionName="foobar",
        Runtime="python3.8",
        Role=role["Arn"],
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": get_test_zip_file1()},
    )

    events_client.put_rule(
        Name="foobarrule",
        EventPattern="""{
                    "source": [
                        "aws.s3"
                    ],
                    "detail-type": [
                        "AWS API Call via CloudTrail"
                    ],
                    "detail": {
                        "eventSource": [
                            "s3.amazonaws.com"
                        ],
                        "eventName": [
                            "CreateBucket"
                        ]
                    }
                }""",
        State="DISABLED",
        RoleArn=role["Arn"],
    )

    events_client.put_targets(
        Rule="foobarrule",
        Targets=[
            {
                "Id": "n/a",
                "Arn": func["FunctionArn"],
                "RoleArn": role["Arn"],
            }
        ],
    )

    bucket_name = "foobar"
    s3_client.create_bucket(
        ACL="public-read-write",
        Bucket=bucket_name,
    )

    expected_msg = '"detail-type":"Object Created"'
    log_group = f"/aws/lambda/{bucket_name}"
    msg_showed_up, _ = wait_for_log_msg(expected_msg, log_group, wait_time=5)
    msg_showed_up.should.equal(False)


@mock_events
@mock_iam
@mock_logs
@mock_s3
def test_create_rule_for_unsupported_target_arn():
    iam_client = boto3.client("iam", "us-east-1")
    events_client = boto3.client("events", "us-east-1")
    s3_client = boto3.client("s3", "us-east-1")

    role = iam_client.create_role(
        RoleName="foobar",
        AssumeRolePolicyDocument="{}",
    )["Role"]

    events_client.put_rule(
        Name="foobarrule",
        EventPattern="""{
                    "source": [
                        "aws.s3"
                    ],
                    "detail-type": [
                        "AWS API Call via CloudTrail"
                    ],
                    "detail": {
                        "eventSource": [
                            "s3.amazonaws.com"
                        ],
                        "eventName": [
                            "CreateBucket"
                        ]
                    }
                }""",
        State="ENABLED",
        RoleArn=role["Arn"],
    )

    events_client.put_targets(
        Rule="foobarrule",
        Targets=[
            {
                "Id": "n/a",
                "Arn": "arn:aws:unknown",
                "RoleArn": role["Arn"],
            }
        ],
    )

    bucket_name = "foobar"
    s3_client.create_bucket(
        ACL="public-read-write",
        Bucket=bucket_name,
    )

    expected_msg = '"detail-type":"Object Created"'
    log_group = f"/aws/lambda/{bucket_name}"
    msg_showed_up, _ = wait_for_log_msg(expected_msg, log_group, wait_time=5)
    msg_showed_up.should.equal(False)


@mock_events
@mock_iam
@mock_lambda
@mock_logs
@mock_s3
def test_creating_bucket__but_invoke_lambda_on_create_object():
    iam_client = boto3.client("iam", "us-east-1")
    lambda_client = boto3.client("lambda", "us-east-1")
    events_client = boto3.client("events", "us-east-1")
    s3_client = boto3.client("s3", "us-east-1")

    role = iam_client.create_role(
        RoleName="foobar",
        AssumeRolePolicyDocument="{}",
    )["Role"]

    func = lambda_client.create_function(
        FunctionName="foobar",
        Runtime="python3.8",
        Role=role["Arn"],
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": get_test_zip_file1()},
    )

    events_client.put_rule(
        Name="foobarrule",
        EventPattern="""{
                "source": [
                    "aws.s3"
                ],
                "detail": {
                    "eventSource": [
                        "s3.amazonaws.com"
                    ],
                    "eventName": [
                        "CreateObject"
                    ]
                }
            }""",
        State="ENABLED",
        RoleArn=role["Arn"],
    )

    events_client.put_targets(
        Rule="foobarrule",
        Targets=[
            {
                "Id": "n/a",
                "Arn": func["FunctionArn"],
                "RoleArn": role["Arn"],
            }
        ],
    )

    bucket_name = "foobar"
    s3_client.create_bucket(
        ACL="public-read-write",
        Bucket=bucket_name,
    )

    expected_msg = '"detail-type":"Object Created"'
    log_group = f"/aws/lambda/{bucket_name}"
    msg_showed_up, _ = wait_for_log_msg(expected_msg, log_group, wait_time=5)
    msg_showed_up.should.equal(False)


@mock_events
@mock_iam
@mock_s3
def test_creating_bucket__succeeds_despite_unknown_lambda():
    iam_client = boto3.client("iam", "us-east-1")
    events_client = boto3.client("events", "us-east-1")
    s3_client = boto3.client("s3", "us-east-1")

    role = iam_client.create_role(
        RoleName="foobar",
        AssumeRolePolicyDocument="{}",
    )["Role"]

    events_client.put_rule(
        Name="foobarrule",
        EventPattern="""{
                "source": [
                    "aws.s3"
                ],
                "detail-type": [
                    "AWS API Call via CloudTrail"
                ],
                "detail": {
                    "eventSource": [
                        "s3.amazonaws.com"
                    ],
                    "eventName": [
                        "CreateBucket"
                    ]
                }
            }""",
        State="ENABLED",
        RoleArn=role["Arn"],
    )

    events_client.put_targets(
        Rule="foobarrule",
        Targets=[
            {
                "Id": "n/a",
                "Arn": "arn:aws:lambda:unknown",
                "RoleArn": role["Arn"],
            }
        ],
    )

    bucket_name = "foobar"
    bucket = s3_client.create_bucket(
        ACL="public-read-write",
        Bucket=bucket_name,
    )
    bucket.shouldnt.equal(None)
