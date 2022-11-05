import boto3
from moto import mock_ec2, mock_iam


@mock_ec2
@mock_iam
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
    last_used.should.have.key("LastUsedDate")
    last_used.should.have.key("ServiceName").equals("ec2")
    last_used.should.have.key("Region").equals("us-east-2")
