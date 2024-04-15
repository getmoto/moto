import csv
import datetime
from unittest import SkipTest

import boto3
from dateutil.parser import parse

from moto import mock_aws, settings
from moto.iam.models import IAMBackend, iam_backends
from tests import DEFAULT_ACCOUNT_ID


@mock_aws
def test_invoking_ec2_mark_access_key_as_used():
    c_iam = boto3.client("iam", region_name="us-east-1")
    c_iam.create_user(Path="my/path", UserName="fakeUser")
    key = c_iam.create_access_key(UserName="fakeUser")

    c_ec2 = boto3.client(
        "ec2",
        region_name="us-east-2",
        aws_access_key_id=key["AccessKey"]["AccessKeyId"],
        aws_secret_access_key=key["AccessKey"]["SecretAccessKey"],
    )
    c_ec2.describe_instances()

    last_used = c_iam.get_access_key_last_used(
        AccessKeyId=key["AccessKey"]["AccessKeyId"]
    )["AccessKeyLastUsed"]
    assert "LastUsedDate" in last_used
    assert last_used["ServiceName"] == "ec2"
    assert last_used["Region"] == "us-east-2"


@mock_aws
def test_mark_role_as_last_used():
    role_name = "role_name_created_jan_1st"
    iam = boto3.client("iam", "us-east-1")
    sts = boto3.client("sts", "us-east-1")

    role_arn = iam.create_role(RoleName=role_name, AssumeRolePolicyDocument="example")[
        "Role"
    ]["Arn"]

    creds = sts.assume_role(RoleArn=role_arn, RoleSessionName="temp_session")[
        "Credentials"
    ]

    iam2 = boto3.client(
        "iam",
        "us-east-1",
        aws_access_key_id=creds["AccessKeyId"],
        aws_secret_access_key=creds["SecretAccessKey"],
        aws_session_token=creds["SessionToken"],
    )

    iam2.create_role(RoleName="name", AssumeRolePolicyDocument="example")

    role = iam.get_role(RoleName=role_name)["Role"]
    assert isinstance(role["RoleLastUsed"]["LastUsedDate"], datetime.datetime)

    if not settings.TEST_SERVER_MODE:
        iam: IAMBackend = iam_backends[DEFAULT_ACCOUNT_ID]["global"]
        assert iam.get_role(role_name).last_used is not None


@mock_aws
def test_get_credential_report_content__set_last_used_automatically():
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("No point testing this in ServerMode")
    # Ensure LAST_USED field is set
    c_iam = boto3.client("iam", region_name="us-east-1")
    c_iam.create_user(Path="my/path", UserName="fakeUser")
    key = c_iam.create_access_key(UserName="fakeUser")

    c_ec2 = boto3.client(
        "ec2",
        region_name="us-east-2",
        aws_access_key_id=key["AccessKey"]["AccessKeyId"],
        aws_secret_access_key=key["AccessKey"]["SecretAccessKey"],
    )
    c_ec2.describe_instances()

    # VERIFY last_used can be retrieved
    conn = boto3.client("iam", region_name="us-east-1")

    result = conn.generate_credential_report()
    while result["State"] != "COMPLETE":
        result = conn.generate_credential_report()
    result = conn.get_credential_report()
    report = result["Content"].decode("utf-8")
    report_dict = csv.DictReader(report.split("\n"))
    user = next(report_dict)

    assert parse(user["access_key_1_last_used_date"])
