import json
from typing import Any, Dict, Optional
from uuid import uuid4

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_ec2, mock_elbv2, mock_iam, mock_rds, mock_s3, mock_ssm, mock_sts
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from moto.core import set_initial_no_auth_action_count


@mock_iam
def create_user_with_access_key(user_name: str = "test-user") -> Dict[str, str]:
    client = boto3.client("iam", region_name="us-east-1")
    client.create_user(UserName=user_name)
    return client.create_access_key(UserName=user_name)["AccessKey"]


@mock_iam
def create_user_with_access_key_and_inline_policy(  # type: ignore[misc]
    user_name: str, policy_document: Dict[str, Any], policy_name: str = "policy1"
) -> Dict[str, str]:
    client = boto3.client("iam", region_name="us-east-1")
    client.create_user(UserName=user_name)
    client.put_user_policy(
        UserName=user_name,
        PolicyName=policy_name,
        PolicyDocument=json.dumps(policy_document),
    )
    return client.create_access_key(UserName=user_name)["AccessKey"]


@mock_iam
def create_user_with_access_key_and_attached_policy(  # type: ignore[misc]
    user_name: str, policy_document: Dict[str, Any], policy_name: str = "policy1"
) -> Dict[str, str]:
    client = boto3.client("iam", region_name="us-east-1")
    client.create_user(UserName=user_name)
    policy_arn = client.create_policy(
        PolicyName=policy_name, PolicyDocument=json.dumps(policy_document)
    )["Policy"]["Arn"]
    client.attach_user_policy(UserName=user_name, PolicyArn=policy_arn)
    return client.create_access_key(UserName=user_name)["AccessKey"]


@mock_iam
def create_user_with_access_key_and_multiple_policies(  # type: ignore[misc]
    user_name: str,
    inline_policy_document: Dict[str, Any],
    attached_policy_document: Dict[str, Any],
    inline_policy_name: str = "policy1",
    attached_policy_name: str = "policy1",
) -> Dict[str, str]:
    client = boto3.client("iam", region_name="us-east-1")
    client.create_user(UserName=user_name)
    policy_arn = client.create_policy(
        PolicyName=attached_policy_name,
        PolicyDocument=json.dumps(attached_policy_document),
    )["Policy"]["Arn"]
    client.attach_user_policy(UserName=user_name, PolicyArn=policy_arn)
    client.put_user_policy(
        UserName=user_name,
        PolicyName=inline_policy_name,
        PolicyDocument=json.dumps(inline_policy_document),
    )
    return client.create_access_key(UserName=user_name)["AccessKey"]


def create_group_with_attached_policy_and_add_user(
    user_name: str,
    policy_document: Dict[str, Any],
    group_name: str = "test-group",
    policy_name: Optional[str] = None,
) -> None:
    if not policy_name:
        policy_name = str(uuid4())
    client = boto3.client("iam", region_name="us-east-1")
    client.create_group(GroupName=group_name)
    policy_arn = client.create_policy(
        PolicyName=policy_name, PolicyDocument=json.dumps(policy_document)
    )["Policy"]["Arn"]
    client.attach_group_policy(GroupName=group_name, PolicyArn=policy_arn)
    client.add_user_to_group(GroupName=group_name, UserName=user_name)


def create_group_with_inline_policy_and_add_user(
    user_name: str,
    policy_document: Dict[str, Any],
    group_name: str = "test-group",
    policy_name: str = "policy1",
) -> None:
    client = boto3.client("iam", region_name="us-east-1")
    client.create_group(GroupName=group_name)
    client.put_group_policy(
        GroupName=group_name,
        PolicyName=policy_name,
        PolicyDocument=json.dumps(policy_document),
    )
    client.add_user_to_group(GroupName=group_name, UserName=user_name)


def create_group_with_multiple_policies_and_add_user(
    user_name: str,
    inline_policy_document: Dict[str, Any],
    attached_policy_document: Dict[str, Any],
    group_name: str = "test-group",
    inline_policy_name: str = "policy1",
    attached_policy_name: Optional[str] = None,
) -> None:
    if not attached_policy_name:
        attached_policy_name = str(uuid4())
    client = boto3.client("iam", region_name="us-east-1")
    client.create_group(GroupName=group_name)
    client.put_group_policy(
        GroupName=group_name,
        PolicyName=inline_policy_name,
        PolicyDocument=json.dumps(inline_policy_document),
    )
    policy_arn = client.create_policy(
        PolicyName=attached_policy_name,
        PolicyDocument=json.dumps(attached_policy_document),
    )["Policy"]["Arn"]
    client.attach_group_policy(GroupName=group_name, PolicyArn=policy_arn)
    client.add_user_to_group(GroupName=group_name, UserName=user_name)


@mock_iam
@mock_sts
def create_role_with_attached_policy_and_assume_it(  # type: ignore[misc]
    role_name: str,
    trust_policy_document: Dict[str, Any],
    policy_document: Dict[str, Any],
    session_name: str = "session1",
    policy_name: str = "policy1",
) -> Dict[str, str]:
    iam_client = boto3.client("iam", region_name="us-east-1")
    sts_client = boto3.client("sts", region_name="us-east-1")
    role_arn = iam_client.create_role(
        RoleName=role_name, AssumeRolePolicyDocument=json.dumps(trust_policy_document)
    )["Role"]["Arn"]
    policy_arn = iam_client.create_policy(
        PolicyName=policy_name, PolicyDocument=json.dumps(policy_document)
    )["Policy"]["Arn"]
    iam_client.attach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
    return sts_client.assume_role(RoleArn=role_arn, RoleSessionName=session_name)[
        "Credentials"
    ]


@mock_iam
@mock_sts
def create_role_with_inline_policy_and_assume_it(  # type: ignore[misc]
    role_name: str,
    trust_policy_document: Dict[str, Any],
    policy_document: Dict[str, Any],
    session_name: str = "session1",
    policy_name: str = "policy1",
) -> Dict[str, str]:
    iam_client = boto3.client("iam", region_name="us-east-1")
    sts_client = boto3.client("sts", region_name="us-east-1")
    role_arn = iam_client.create_role(
        RoleName=role_name, AssumeRolePolicyDocument=json.dumps(trust_policy_document)
    )["Role"]["Arn"]
    iam_client.put_role_policy(
        RoleName=role_name,
        PolicyName=policy_name,
        PolicyDocument=json.dumps(policy_document),
    )
    return sts_client.assume_role(RoleArn=role_arn, RoleSessionName=session_name)[
        "Credentials"
    ]


@set_initial_no_auth_action_count(0)
@mock_iam
def test_invalid_client_token_id() -> None:
    client = boto3.client(
        "iam",
        region_name="us-east-1",
        aws_access_key_id="invalid",
        aws_secret_access_key="invalid",
    )
    with pytest.raises(ClientError) as ex:
        client.get_user()
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidClientTokenId"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 403
    assert err["Message"] == "The security token included in the request is invalid."


@set_initial_no_auth_action_count(0)
@mock_ec2
def test_auth_failure() -> None:
    client = boto3.client(
        "ec2",
        region_name="us-east-1",
        aws_access_key_id="invalid",
        aws_secret_access_key="invalid",
    )
    with pytest.raises(ClientError) as ex:
        client.describe_instances()
    err = ex.value.response["Error"]
    assert err["Code"] == "AuthFailure"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 401
    assert (
        err["Message"] == "AWS was not able to validate the provided access credentials"
    )


@set_initial_no_auth_action_count(2)
@mock_iam
def test_signature_does_not_match() -> None:
    access_key = create_user_with_access_key()
    client = boto3.client(
        "iam",
        region_name="us-east-1",
        aws_access_key_id=access_key["AccessKeyId"],
        aws_secret_access_key="invalid",
    )
    with pytest.raises(ClientError) as ex:
        client.get_user()
    assert ex.value.response["Error"]["Code"] == "SignatureDoesNotMatch"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 403
    assert (
        ex.value.response["Error"]["Message"]
        == "The request signature we calculated does not match the signature you provided. Check your AWS Secret Access Key and signing method. Consult the service documentation for details."
    )


@set_initial_no_auth_action_count(2)
@mock_ec2
def test_auth_failure_with_valid_access_key_id() -> None:
    access_key = create_user_with_access_key()
    client = boto3.client(
        "ec2",
        region_name="us-east-1",
        aws_access_key_id=access_key["AccessKeyId"],
        aws_secret_access_key="invalid",
    )
    with pytest.raises(ClientError) as ex:
        client.describe_instances()
    assert ex.value.response["Error"]["Code"] == "AuthFailure"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 401
    assert (
        ex.value.response["Error"]["Message"]
        == "AWS was not able to validate the provided access credentials"
    )


@set_initial_no_auth_action_count(2)
@mock_ec2
def test_access_denied_with_no_policy() -> None:
    user_name = "test-user"
    access_key = create_user_with_access_key(user_name)
    client = boto3.client(
        "ec2",
        region_name="us-east-1",
        aws_access_key_id=access_key["AccessKeyId"],
        aws_secret_access_key=access_key["SecretAccessKey"],
    )
    with pytest.raises(ClientError) as ex:
        client.describe_instances()
    assert ex.value.response["Error"]["Code"] == "AccessDenied"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 403
    assert (
        ex.value.response["Error"]["Message"]
        == f"User: arn:aws:iam::{ACCOUNT_ID}:user/{user_name} is not authorized to perform: ec2:DescribeInstances"
    )


@set_initial_no_auth_action_count(3)
@mock_ec2
def test_access_denied_with_not_allowing_policy() -> None:
    user_name = "test-user"
    inline_policy_document = {
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Allow", "Action": ["ec2:Run*"], "Resource": "*"}],
    }
    access_key = create_user_with_access_key_and_inline_policy(
        user_name, inline_policy_document
    )
    client = boto3.client(
        "ec2",
        region_name="us-east-1",
        aws_access_key_id=access_key["AccessKeyId"],
        aws_secret_access_key=access_key["SecretAccessKey"],
    )
    with pytest.raises(ClientError) as ex:
        client.describe_instances()
    assert ex.value.response["Error"]["Code"] == "AccessDenied"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 403
    assert (
        ex.value.response["Error"]["Message"]
        == f"User: arn:aws:iam::{ACCOUNT_ID}:user/{user_name} is not authorized to perform: ec2:DescribeInstances"
    )


@set_initial_no_auth_action_count(3)
@mock_sts
def test_access_denied_explicitly_on_specific_resource() -> None:
    user_name = "test-user"
    forbidden_role_arn = f"arn:aws:iam::{ACCOUNT_ID}:role/forbidden_explicitly"
    allowed_role_arn = f"arn:aws:iam::{ACCOUNT_ID}:role/allowed_implictly"
    role_session_name = "dummy"
    inline_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Deny",
                "Action": ["sts:AssumeRole"],
                "Resource": forbidden_role_arn,
            },
            {"Effect": "Allow", "Action": ["sts:AssumeRole"], "Resource": "*"},
        ],
    }
    access_key = create_user_with_access_key_and_inline_policy(
        user_name, inline_policy_document
    )
    client = boto3.client(
        "sts",
        region_name="us-east-1",
        aws_access_key_id=access_key["AccessKeyId"],
        aws_secret_access_key=access_key["SecretAccessKey"],
    )
    with pytest.raises(ClientError) as ex:
        client.assume_role(
            RoleArn=forbidden_role_arn, RoleSessionName=role_session_name
        )
    assert ex.value.response["Error"]["Code"] == "AccessDenied"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 403
    assert (
        ex.value.response["Error"]["Message"]
        == f"User: arn:aws:iam::{ACCOUNT_ID}:user/{user_name} is not authorized to perform: sts:AssumeRole"
    )
    # Not raising means success
    client.assume_role(RoleArn=allowed_role_arn, RoleSessionName=role_session_name)


@set_initial_no_auth_action_count(3)
@mock_ec2
def test_access_denied_for_run_instances() -> None:
    # https://github.com/getmoto/moto/issues/2774
    # The run-instances method was broken between botocore versions 1.15.8 and 1.15.12
    # This was due to the inclusion of '"idempotencyToken":true' in the response, somehow altering the signature and breaking the authentication
    # Keeping this test in place in case botocore decides to break again
    user_name = "test-user"
    inline_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {"Effect": "Allow", "Action": ["ec2:Describe*"], "Resource": "*"}
        ],
    }
    access_key = create_user_with_access_key_and_inline_policy(
        user_name, inline_policy_document
    )
    client = boto3.client(
        "ec2",
        region_name="us-east-1",
        aws_access_key_id=access_key["AccessKeyId"],
        aws_secret_access_key=access_key["SecretAccessKey"],
    )
    with pytest.raises(ClientError) as ex:
        client.run_instances(MaxCount=1, MinCount=1)
    assert ex.value.response["Error"]["Code"] == "AccessDenied"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 403
    assert (
        ex.value.response["Error"]["Message"]
        == f"User: arn:aws:iam::{ACCOUNT_ID}:user/{user_name} is not authorized to perform: ec2:RunInstances"
    )


@set_initial_no_auth_action_count(3)
@mock_ec2
def test_access_denied_with_denying_policy() -> None:
    user_name = "test-user"
    inline_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {"Effect": "Allow", "Action": ["ec2:*"], "Resource": "*"},
            {"Effect": "Deny", "Action": "ec2:CreateVpc", "Resource": "*"},
        ],
    }
    access_key = create_user_with_access_key_and_inline_policy(
        user_name, inline_policy_document
    )
    client = boto3.client(
        "ec2",
        region_name="us-east-1",
        aws_access_key_id=access_key["AccessKeyId"],
        aws_secret_access_key=access_key["SecretAccessKey"],
    )
    with pytest.raises(ClientError) as ex:
        client.create_vpc(CidrBlock="10.0.0.0/16")
    assert ex.value.response["Error"]["Code"] == "AccessDenied"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 403
    assert (
        ex.value.response["Error"]["Message"]
        == f"User: arn:aws:iam::{ACCOUNT_ID}:user/{user_name} is not authorized to perform: ec2:CreateVpc"
    )


@set_initial_no_auth_action_count(3)
@mock_sts
def test_get_caller_identity_allowed_with_denying_policy() -> None:
    user_name = "test-user"
    inline_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {"Effect": "Deny", "Action": "sts:GetCallerIdentity", "Resource": "*"}
        ],
    }
    access_key = create_user_with_access_key_and_inline_policy(
        user_name, inline_policy_document
    )
    client = boto3.client(
        "sts",
        region_name="us-east-1",
        aws_access_key_id=access_key["AccessKeyId"],
        aws_secret_access_key=access_key["SecretAccessKey"],
    )
    assert (
        client.get_caller_identity()["Arn"]
        == f"arn:aws:iam::{ACCOUNT_ID}:user/{user_name}"
    )


@set_initial_no_auth_action_count(3)
@mock_ec2
def test_allowed_with_wildcard_action() -> None:
    user_name = "test-user"
    inline_policy_document = {
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Allow", "Action": "ec2:Describe*", "Resource": "*"}],
    }
    access_key = create_user_with_access_key_and_inline_policy(
        user_name, inline_policy_document
    )
    client = boto3.client(
        "ec2",
        region_name="us-east-1",
        aws_access_key_id=access_key["AccessKeyId"],
        aws_secret_access_key=access_key["SecretAccessKey"],
    )
    assert client.describe_tags()["Tags"] == []


@set_initial_no_auth_action_count(4)
@mock_iam
def test_allowed_with_explicit_action_in_attached_policy() -> None:
    user_name = "test-user"
    attached_policy_document = {
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Allow", "Action": "iam:ListGroups", "Resource": "*"}],
    }
    access_key = create_user_with_access_key_and_attached_policy(
        user_name, attached_policy_document
    )
    client = boto3.client(
        "iam",
        region_name="us-east-1",
        aws_access_key_id=access_key["AccessKeyId"],
        aws_secret_access_key=access_key["SecretAccessKey"],
    )
    assert client.list_groups()["Groups"] == []


@set_initial_no_auth_action_count(8)
@mock_s3
@mock_iam
def test_s3_access_denied_with_denying_attached_group_policy() -> None:
    user_name = "test-user"
    attached_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {"Effect": "Allow", "Action": "s3:ListAllMyBuckets", "Resource": "*"}
        ],
    }
    group_attached_policy_document = {
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Deny", "Action": "s3:List*", "Resource": "*"}],
    }
    access_key = create_user_with_access_key_and_attached_policy(
        user_name, attached_policy_document, policy_name="policy1"
    )
    create_group_with_attached_policy_and_add_user(
        user_name, group_attached_policy_document, policy_name="policy2"
    )
    client = boto3.client(
        "s3",
        region_name="us-east-1",
        aws_access_key_id=access_key["AccessKeyId"],
        aws_secret_access_key=access_key["SecretAccessKey"],
    )
    with pytest.raises(ClientError) as ex:
        client.list_buckets()
    assert ex.value.response["Error"]["Code"] == "AccessDenied"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 403
    assert ex.value.response["Error"]["Message"] == "Access Denied"


@set_initial_no_auth_action_count(6)
@mock_s3
@mock_iam
def test_s3_access_denied_with_denying_inline_group_policy() -> None:
    user_name = "test-user"
    bucket_name = "test-bucket"
    inline_policy_document = {
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Allow", "Action": "*", "Resource": "*"}],
    }
    group_inline_policy_document = {
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Deny", "Action": "s3:GetObject", "Resource": "*"}],
    }
    access_key = create_user_with_access_key_and_inline_policy(
        user_name, inline_policy_document
    )
    create_group_with_inline_policy_and_add_user(
        user_name, group_inline_policy_document
    )
    client = boto3.client(
        "s3",
        region_name="us-east-1",
        aws_access_key_id=access_key["AccessKeyId"],
        aws_secret_access_key=access_key["SecretAccessKey"],
    )
    client.create_bucket(Bucket=bucket_name)
    with pytest.raises(ClientError) as ex:
        client.get_object(Bucket=bucket_name, Key="sdfsdf")
    assert ex.value.response["Error"]["Code"] == "AccessDenied"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 403
    assert ex.value.response["Error"]["Message"] == "Access Denied"


@set_initial_no_auth_action_count(10)
@mock_iam
@mock_ec2
def test_access_denied_with_many_irrelevant_policies() -> None:
    user_name = "test-user"
    inline_policy_document = {
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Allow", "Action": "ec2:Describe*", "Resource": "*"}],
    }
    attached_policy_document = {
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Allow", "Action": "s3:*", "Resource": "*"}],
    }
    group_inline_policy_document = {
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Deny", "Action": "iam:List*", "Resource": "*"}],
    }
    group_attached_policy_document = {
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Deny", "Action": "lambda:*", "Resource": "*"}],
    }
    access_key = create_user_with_access_key_and_multiple_policies(
        user_name,
        inline_policy_document,
        attached_policy_document,
        attached_policy_name="policy1",
    )
    create_group_with_multiple_policies_and_add_user(
        user_name,
        group_inline_policy_document,
        group_attached_policy_document,
        attached_policy_name="policy2",
    )
    client = boto3.client(
        "ec2",
        region_name="us-east-1",
        aws_access_key_id=access_key["AccessKeyId"],
        aws_secret_access_key=access_key["SecretAccessKey"],
    )
    with pytest.raises(ClientError) as ex:
        client.create_key_pair(KeyName="TestKey")
    assert ex.value.response["Error"]["Code"] == "AccessDenied"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 403
    assert (
        ex.value.response["Error"]["Message"]
        == f"User: arn:aws:iam::{ACCOUNT_ID}:user/{user_name} is not authorized to perform: ec2:CreateKeyPair"
    )


@set_initial_no_auth_action_count(4)
@mock_iam
@mock_sts
@mock_ec2
@mock_elbv2
def test_allowed_with_temporary_credentials() -> None:
    role_name = "test-role"
    trust_policy_document = {
        "Version": "2012-10-17",
        "Statement": {
            "Effect": "Allow",
            "Principal": {"AWS": f"arn:aws:iam::{ACCOUNT_ID}:root"},
            "Action": "sts:AssumeRole",
        },
    }
    attached_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "elasticloadbalancing:CreateLoadBalancer",
                    "ec2:DescribeSubnets",
                ],
                "Resource": "*",
            }
        ],
    }
    credentials = create_role_with_attached_policy_and_assume_it(
        role_name, trust_policy_document, attached_policy_document
    )
    elbv2_client = boto3.client(
        "elbv2",
        region_name="us-east-1",
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials["SessionToken"],
    )
    ec2_client = boto3.client(
        "ec2",
        region_name="us-east-1",
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials["SessionToken"],
    )
    subnets = ec2_client.describe_subnets()["Subnets"]
    assert len(subnets) > 1
    subnet_ids = [subnets[0]["SubnetId"], subnets[1]["SubnetId"]]
    resp = elbv2_client.create_load_balancer(Name="lb", Subnets=subnet_ids)
    assert len(resp["LoadBalancers"]) == 1


@set_initial_no_auth_action_count(3)
@mock_iam
@mock_sts
@mock_rds
def test_access_denied_with_temporary_credentials() -> None:
    role_name = "test-role"
    session_name = "test-session"
    trust_policy_document = {
        "Version": "2012-10-17",
        "Statement": {
            "Effect": "Allow",
            "Principal": {"AWS": f"arn:aws:iam::{ACCOUNT_ID}:root"},
            "Action": "sts:AssumeRole",
        },
    }
    attached_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {"Effect": "Allow", "Action": ["rds:Describe*"], "Resource": "*"}
        ],
    }
    credentials = create_role_with_inline_policy_and_assume_it(
        role_name, trust_policy_document, attached_policy_document, session_name
    )
    client = boto3.client(
        "rds",
        region_name="us-east-1",
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials["SessionToken"],
    )
    with pytest.raises(ClientError) as ex:
        client.create_db_instance(
            DBInstanceIdentifier="test-db-instance",
            DBInstanceClass="db.t3",
            Engine="aurora-postgresql",
        )
    assert ex.value.response["Error"]["Code"] == "AccessDenied"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 403
    assert (
        ex.value.response["Error"]["Message"]
        == f"User: arn:aws:sts::{ACCOUNT_ID}:assumed-role/{role_name}/{session_name} is not authorized to perform: rds:CreateDBInstance"
    )


@set_initial_no_auth_action_count(3)
@mock_iam
def test_get_user_from_credentials() -> None:
    user_name = "new-test-user"
    inline_policy_document = {
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Allow", "Action": "iam:*", "Resource": "*"}],
    }
    access_key = create_user_with_access_key_and_inline_policy(
        user_name, inline_policy_document
    )
    client = boto3.client(
        "iam",
        region_name="us-east-1",
        aws_access_key_id=access_key["AccessKeyId"],
        aws_secret_access_key=access_key["SecretAccessKey"],
    )
    assert client.get_user()["User"]["UserName"] == user_name


@set_initial_no_auth_action_count(0)
@mock_s3
def test_s3_invalid_access_key_id() -> None:
    client = boto3.client(
        "s3",
        region_name="us-east-1",
        aws_access_key_id="invalid",
        aws_secret_access_key="invalid",
    )
    with pytest.raises(ClientError) as ex:
        client.list_buckets()
    assert ex.value.response["Error"]["Code"] == "InvalidAccessKeyId"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 403
    assert (
        ex.value.response["Error"]["Message"]
        == "The AWS Access Key Id you provided does not exist in our records."
    )


@set_initial_no_auth_action_count(3)
@mock_s3
@mock_iam
def test_s3_signature_does_not_match() -> None:
    bucket_name = "test-bucket"
    access_key = create_user_with_access_key()
    client = boto3.client(
        "s3",
        region_name="us-east-1",
        aws_access_key_id=access_key["AccessKeyId"],
        aws_secret_access_key="invalid",
    )
    client.create_bucket(Bucket=bucket_name)
    with pytest.raises(ClientError) as ex:
        client.put_object(Bucket=bucket_name, Key="abc")
    assert ex.value.response["Error"]["Code"] == "SignatureDoesNotMatch"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 403
    assert (
        ex.value.response["Error"]["Message"]
        == "The request signature we calculated does not match the signature you provided. Check your key and signing method."
    )


@set_initial_no_auth_action_count(7)
@mock_s3
@mock_iam
def test_s3_access_denied_not_action() -> None:
    user_name = "test-user"
    bucket_name = "test-bucket"
    inline_policy_document = {
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Allow", "Action": "*", "Resource": "*"}],
    }
    group_inline_policy_document = {
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Deny", "NotAction": "iam:GetUser", "Resource": "*"}],
    }
    access_key = create_user_with_access_key_and_inline_policy(
        user_name, inline_policy_document
    )
    create_group_with_inline_policy_and_add_user(
        user_name, group_inline_policy_document
    )
    client = boto3.client(
        "s3",
        region_name="us-east-1",
        aws_access_key_id=access_key["AccessKeyId"],
        aws_secret_access_key=access_key["SecretAccessKey"],
    )
    client.create_bucket(Bucket=bucket_name)
    with pytest.raises(ClientError) as ex:
        client.delete_object(Bucket=bucket_name, Key="sdfsdf")
    assert ex.value.response["Error"]["Code"] == "AccessDenied"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 403
    assert ex.value.response["Error"]["Message"] == "Access Denied"


@set_initial_no_auth_action_count(4)
@mock_iam
@mock_sts
@mock_s3
def test_s3_invalid_token_with_temporary_credentials() -> None:
    role_name = "test-role"
    session_name = "test-session"
    bucket_name = "test-bucket-888"
    trust_policy_document = {
        "Version": "2012-10-17",
        "Statement": {
            "Effect": "Allow",
            "Principal": {"AWS": f"arn:aws:iam::{ACCOUNT_ID}:root"},
            "Action": "sts:AssumeRole",
        },
    }
    attached_policy_document = {
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Allow", "Action": ["*"], "Resource": "*"}],
    }
    credentials = create_role_with_inline_policy_and_assume_it(
        role_name, trust_policy_document, attached_policy_document, session_name
    )
    client = boto3.client(
        "s3",
        region_name="us-east-1",
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token="invalid",
    )
    client.create_bucket(Bucket=bucket_name)
    with pytest.raises(ClientError) as ex:
        client.list_bucket_metrics_configurations(Bucket=bucket_name)
    err = ex.value.response["Error"]
    assert err["Code"] == "InvalidToken"
    assert ex.value.response["ResponseMetadata"]["HTTPStatusCode"] == 400
    assert err["Message"] == "The provided token is malformed or otherwise invalid."


@set_initial_no_auth_action_count(3)
@mock_s3
@mock_iam
def test_allow_bucket_access_using_resource_arn() -> None:
    user_name = "test-user"
    policy_doc = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Action": ["s3:*"],
                "Effect": "Allow",
                "Resource": "arn:aws:s3:::my_bucket",
                "Sid": "BucketLevelGrants",
            },
        ],
    }
    access_key = create_user_with_access_key_and_inline_policy(user_name, policy_doc)

    s3_client = boto3.client(
        "s3",
        region_name="us-east-1",
        aws_access_key_id=access_key["AccessKeyId"],
        aws_secret_access_key=access_key["SecretAccessKey"],
    )

    s3_client.create_bucket(Bucket="my_bucket")
    with pytest.raises(ClientError):
        s3_client.create_bucket(Bucket="my_bucket2")

    s3_client.head_bucket(Bucket="my_bucket")
    with pytest.raises(ClientError):
        s3_client.head_bucket(Bucket="my_bucket2")


@set_initial_no_auth_action_count(3)
@mock_s3
@mock_iam
def test_allow_key_access_using_resource_arn() -> None:
    user_name = "test-user"
    policy_doc = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Action": ["s3:*"],
                "Effect": "Allow",
                "Resource": ["arn:aws:s3:::my_bucket", "arn:aws:s3:::*/keyname"],
                "Sid": "KeyLevelGrants",
            },
        ],
    }
    access_key = create_user_with_access_key_and_inline_policy(user_name, policy_doc)

    s3_client = boto3.client(
        "s3",
        region_name="us-east-1",
        aws_access_key_id=access_key["AccessKeyId"],
        aws_secret_access_key=access_key["SecretAccessKey"],
    )

    s3_client.create_bucket(Bucket="my_bucket")
    s3_client.put_object(Bucket="my_bucket", Key="keyname", Body=b"test")
    with pytest.raises(ClientError):
        s3_client.put_object(Bucket="my_bucket", Key="unknown", Body=b"test")


@set_initial_no_auth_action_count(3)
@mock_ssm
@mock_iam
def test_ssm_service() -> None:
    user_name = "test-user"
    policy_doc = {
        "Version": "2012-10-17",
        "Statement": [{"Action": ["ssm:*"], "Effect": "Allow", "Resource": ["*"]}],
    }
    access_key = create_user_with_access_key_and_inline_policy(user_name, policy_doc)

    ssmc = boto3.client(
        "ssm",
        region_name="us-east-1",
        aws_access_key_id=access_key["AccessKeyId"],
        aws_secret_access_key=access_key["SecretAccessKey"],
    )

    ssmc.put_parameter(Name="test", Value="value", Type="String")
