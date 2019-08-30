import json

import boto3
import sure  # noqa
from botocore.exceptions import ClientError
# Ensure 'assert_raises' context manager support for Python 2.6
import tests.backport_assert_raises
from nose.tools import assert_raises

from moto import mock_iam, mock_ec2, mock_s3, mock_sts, mock_elbv2, mock_rds2
from moto.core import set_initial_no_auth_action_count
from moto.iam.models import ACCOUNT_ID


@mock_iam
def create_user_with_access_key(user_name='test-user'):
    client = boto3.client('iam', region_name='us-east-1')
    client.create_user(UserName=user_name)
    return client.create_access_key(UserName=user_name)['AccessKey']


@mock_iam
def create_user_with_access_key_and_inline_policy(user_name, policy_document, policy_name='policy1'):
    client = boto3.client('iam', region_name='us-east-1')
    client.create_user(UserName=user_name)
    client.put_user_policy(UserName=user_name, PolicyName=policy_name, PolicyDocument=json.dumps(policy_document))
    return client.create_access_key(UserName=user_name)['AccessKey']


@mock_iam
def create_user_with_access_key_and_attached_policy(user_name, policy_document, policy_name='policy1'):
    client = boto3.client('iam', region_name='us-east-1')
    client.create_user(UserName=user_name)
    policy_arn = client.create_policy(
        PolicyName=policy_name,
        PolicyDocument=json.dumps(policy_document)
    )['Policy']['Arn']
    client.attach_user_policy(UserName=user_name, PolicyArn=policy_arn)
    return client.create_access_key(UserName=user_name)['AccessKey']


@mock_iam
def create_user_with_access_key_and_multiple_policies(user_name, inline_policy_document,
                                                      attached_policy_document, inline_policy_name='policy1', attached_policy_name='policy1'):
    client = boto3.client('iam', region_name='us-east-1')
    client.create_user(UserName=user_name)
    policy_arn = client.create_policy(
        PolicyName=attached_policy_name,
        PolicyDocument=json.dumps(attached_policy_document)
    )['Policy']['Arn']
    client.attach_user_policy(UserName=user_name, PolicyArn=policy_arn)
    client.put_user_policy(UserName=user_name, PolicyName=inline_policy_name, PolicyDocument=json.dumps(inline_policy_document))
    return client.create_access_key(UserName=user_name)['AccessKey']


def create_group_with_attached_policy_and_add_user(user_name, policy_document,
                                                   group_name='test-group', policy_name='policy1'):
    client = boto3.client('iam', region_name='us-east-1')
    client.create_group(GroupName=group_name)
    policy_arn = client.create_policy(
        PolicyName=policy_name,
        PolicyDocument=json.dumps(policy_document)
    )['Policy']['Arn']
    client.attach_group_policy(GroupName=group_name, PolicyArn=policy_arn)
    client.add_user_to_group(GroupName=group_name, UserName=user_name)


def create_group_with_inline_policy_and_add_user(user_name, policy_document,
                                                 group_name='test-group', policy_name='policy1'):
    client = boto3.client('iam', region_name='us-east-1')
    client.create_group(GroupName=group_name)
    client.put_group_policy(
        GroupName=group_name,
        PolicyName=policy_name,
        PolicyDocument=json.dumps(policy_document)
    )
    client.add_user_to_group(GroupName=group_name, UserName=user_name)


def create_group_with_multiple_policies_and_add_user(user_name, inline_policy_document,
                                                     attached_policy_document, group_name='test-group',
                                                     inline_policy_name='policy1', attached_policy_name='policy1'):
    client = boto3.client('iam', region_name='us-east-1')
    client.create_group(GroupName=group_name)
    client.put_group_policy(
        GroupName=group_name,
        PolicyName=inline_policy_name,
        PolicyDocument=json.dumps(inline_policy_document)
    )
    policy_arn = client.create_policy(
        PolicyName=attached_policy_name,
        PolicyDocument=json.dumps(attached_policy_document)
    )['Policy']['Arn']
    client.attach_group_policy(GroupName=group_name, PolicyArn=policy_arn)
    client.add_user_to_group(GroupName=group_name, UserName=user_name)


@mock_iam
@mock_sts
def create_role_with_attached_policy_and_assume_it(role_name, trust_policy_document,
                                                   policy_document, session_name='session1', policy_name='policy1'):
    iam_client = boto3.client('iam', region_name='us-east-1')
    sts_client = boto3.client('sts', region_name='us-east-1')
    role_arn = iam_client.create_role(
        RoleName=role_name,
        AssumeRolePolicyDocument=json.dumps(trust_policy_document)
    )['Role']['Arn']
    policy_arn = iam_client.create_policy(
        PolicyName=policy_name,
        PolicyDocument=json.dumps(policy_document)
    )['Policy']['Arn']
    iam_client.attach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
    return sts_client.assume_role(RoleArn=role_arn, RoleSessionName=session_name)['Credentials']


@mock_iam
@mock_sts
def create_role_with_inline_policy_and_assume_it(role_name, trust_policy_document,
                                                 policy_document, session_name='session1', policy_name='policy1'):
    iam_client = boto3.client('iam', region_name='us-east-1')
    sts_client = boto3.client('sts', region_name='us-east-1')
    role_arn = iam_client.create_role(
        RoleName=role_name,
        AssumeRolePolicyDocument=json.dumps(trust_policy_document)
    )['Role']['Arn']
    iam_client.put_role_policy(
        RoleName=role_name,
        PolicyName=policy_name,
        PolicyDocument=json.dumps(policy_document)
    )
    return sts_client.assume_role(RoleArn=role_arn, RoleSessionName=session_name)['Credentials']


@set_initial_no_auth_action_count(0)
@mock_iam
def test_invalid_client_token_id():
    client = boto3.client('iam', region_name='us-east-1', aws_access_key_id='invalid', aws_secret_access_key='invalid')
    with assert_raises(ClientError) as ex:
        client.get_user()
    ex.exception.response['Error']['Code'].should.equal('InvalidClientTokenId')
    ex.exception.response['ResponseMetadata']['HTTPStatusCode'].should.equal(403)
    ex.exception.response['Error']['Message'].should.equal('The security token included in the request is invalid.')


@set_initial_no_auth_action_count(0)
@mock_ec2
def test_auth_failure():
    client = boto3.client('ec2', region_name='us-east-1', aws_access_key_id='invalid', aws_secret_access_key='invalid')
    with assert_raises(ClientError) as ex:
        client.describe_instances()
    ex.exception.response['Error']['Code'].should.equal('AuthFailure')
    ex.exception.response['ResponseMetadata']['HTTPStatusCode'].should.equal(401)
    ex.exception.response['Error']['Message'].should.equal('AWS was not able to validate the provided access credentials')


@set_initial_no_auth_action_count(2)
@mock_iam
def test_signature_does_not_match():
    access_key = create_user_with_access_key()
    client = boto3.client('iam', region_name='us-east-1',
                          aws_access_key_id=access_key['AccessKeyId'],
                          aws_secret_access_key='invalid')
    with assert_raises(ClientError) as ex:
        client.get_user()
    ex.exception.response['Error']['Code'].should.equal('SignatureDoesNotMatch')
    ex.exception.response['ResponseMetadata']['HTTPStatusCode'].should.equal(403)
    ex.exception.response['Error']['Message'].should.equal('The request signature we calculated does not match the signature you provided. Check your AWS Secret Access Key and signing method. Consult the service documentation for details.')


@set_initial_no_auth_action_count(2)
@mock_ec2
def test_auth_failure_with_valid_access_key_id():
    access_key = create_user_with_access_key()
    client = boto3.client('ec2', region_name='us-east-1',
                          aws_access_key_id=access_key['AccessKeyId'],
                          aws_secret_access_key='invalid')
    with assert_raises(ClientError) as ex:
        client.describe_instances()
    ex.exception.response['Error']['Code'].should.equal('AuthFailure')
    ex.exception.response['ResponseMetadata']['HTTPStatusCode'].should.equal(401)
    ex.exception.response['Error']['Message'].should.equal('AWS was not able to validate the provided access credentials')


@set_initial_no_auth_action_count(2)
@mock_ec2
def test_access_denied_with_no_policy():
    user_name = 'test-user'
    access_key = create_user_with_access_key(user_name)
    client = boto3.client('ec2', region_name='us-east-1',
                          aws_access_key_id=access_key['AccessKeyId'],
                          aws_secret_access_key=access_key['SecretAccessKey'])
    with assert_raises(ClientError) as ex:
        client.describe_instances()
    ex.exception.response['Error']['Code'].should.equal('AccessDenied')
    ex.exception.response['ResponseMetadata']['HTTPStatusCode'].should.equal(403)
    ex.exception.response['Error']['Message'].should.equal(
        'User: arn:aws:iam::{account_id}:user/{user_name} is not authorized to perform: {operation}'.format(
            account_id=ACCOUNT_ID,
            user_name=user_name,
            operation="ec2:DescribeInstances"
        )
    )


@set_initial_no_auth_action_count(3)
@mock_ec2
def test_access_denied_with_not_allowing_policy():
    user_name = 'test-user'
    inline_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "ec2:Describe*"
                ],
                "Resource": "*"
            }
        ]
    }
    access_key = create_user_with_access_key_and_inline_policy(user_name, inline_policy_document)
    client = boto3.client('ec2', region_name='us-east-1',
                          aws_access_key_id=access_key['AccessKeyId'],
                          aws_secret_access_key=access_key['SecretAccessKey'])
    with assert_raises(ClientError) as ex:
        client.run_instances(MaxCount=1, MinCount=1)
    ex.exception.response['Error']['Code'].should.equal('AccessDenied')
    ex.exception.response['ResponseMetadata']['HTTPStatusCode'].should.equal(403)
    ex.exception.response['Error']['Message'].should.equal(
        'User: arn:aws:iam::{account_id}:user/{user_name} is not authorized to perform: {operation}'.format(
            account_id=ACCOUNT_ID,
            user_name=user_name,
            operation="ec2:RunInstances"
        )
    )


@set_initial_no_auth_action_count(3)
@mock_ec2
def test_access_denied_with_denying_policy():
    user_name = 'test-user'
    inline_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "ec2:*",
                ],
                "Resource": "*"
            },
            {
                "Effect": "Deny",
                "Action": "ec2:CreateVpc",
                "Resource": "*"
            }
        ]
    }
    access_key = create_user_with_access_key_and_inline_policy(user_name, inline_policy_document)
    client = boto3.client('ec2', region_name='us-east-1',
                          aws_access_key_id=access_key['AccessKeyId'],
                          aws_secret_access_key=access_key['SecretAccessKey'])
    with assert_raises(ClientError) as ex:
        client.create_vpc(CidrBlock="10.0.0.0/16")
    ex.exception.response['Error']['Code'].should.equal('AccessDenied')
    ex.exception.response['ResponseMetadata']['HTTPStatusCode'].should.equal(403)
    ex.exception.response['Error']['Message'].should.equal(
        'User: arn:aws:iam::{account_id}:user/{user_name} is not authorized to perform: {operation}'.format(
            account_id=ACCOUNT_ID,
            user_name=user_name,
            operation="ec2:CreateVpc"
        )
    )


@set_initial_no_auth_action_count(3)
@mock_sts
def test_get_caller_identity_allowed_with_denying_policy():
    user_name = 'test-user'
    inline_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Deny",
                "Action": "sts:GetCallerIdentity",
                "Resource": "*"
            }
        ]
    }
    access_key = create_user_with_access_key_and_inline_policy(user_name, inline_policy_document)
    client = boto3.client('sts', region_name='us-east-1',
                          aws_access_key_id=access_key['AccessKeyId'],
                          aws_secret_access_key=access_key['SecretAccessKey'])
    client.get_caller_identity().should.be.a(dict)


@set_initial_no_auth_action_count(3)
@mock_ec2
def test_allowed_with_wildcard_action():
    user_name = 'test-user'
    inline_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "ec2:Describe*",
                "Resource": "*"
            }
        ]
    }
    access_key = create_user_with_access_key_and_inline_policy(user_name, inline_policy_document)
    client = boto3.client('ec2', region_name='us-east-1',
                          aws_access_key_id=access_key['AccessKeyId'],
                          aws_secret_access_key=access_key['SecretAccessKey'])
    client.describe_tags()['Tags'].should.be.empty


@set_initial_no_auth_action_count(4)
@mock_iam
def test_allowed_with_explicit_action_in_attached_policy():
    user_name = 'test-user'
    attached_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "iam:ListGroups",
                "Resource": "*"
            }
        ]
    }
    access_key = create_user_with_access_key_and_attached_policy(user_name, attached_policy_document)
    client = boto3.client('iam', region_name='us-east-1',
                          aws_access_key_id=access_key['AccessKeyId'],
                          aws_secret_access_key=access_key['SecretAccessKey'])
    client.list_groups()['Groups'].should.be.empty


@set_initial_no_auth_action_count(8)
@mock_s3
@mock_iam
def test_s3_access_denied_with_denying_attached_group_policy():
    user_name = 'test-user'
    attached_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "s3:ListAllMyBuckets",
                "Resource": "*"
            }
        ]
    }
    group_attached_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Deny",
                "Action": "s3:List*",
                "Resource": "*"
            }
        ]
    }
    access_key = create_user_with_access_key_and_attached_policy(user_name, attached_policy_document)
    create_group_with_attached_policy_and_add_user(user_name, group_attached_policy_document)
    client = boto3.client('s3', region_name='us-east-1',
                          aws_access_key_id=access_key['AccessKeyId'],
                          aws_secret_access_key=access_key['SecretAccessKey'])
    with assert_raises(ClientError) as ex:
        client.list_buckets()
    ex.exception.response['Error']['Code'].should.equal('AccessDenied')
    ex.exception.response['ResponseMetadata']['HTTPStatusCode'].should.equal(403)
    ex.exception.response['Error']['Message'].should.equal('Access Denied')


@set_initial_no_auth_action_count(6)
@mock_s3
@mock_iam
def test_s3_access_denied_with_denying_inline_group_policy():
    user_name = 'test-user'
    bucket_name = 'test-bucket'
    inline_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "*",
                "Resource": "*"
            }
        ]
    }
    group_inline_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Deny",
                "Action": "s3:GetObject",
                "Resource": "*"
            }
        ]
    }
    access_key = create_user_with_access_key_and_inline_policy(user_name, inline_policy_document)
    create_group_with_inline_policy_and_add_user(user_name, group_inline_policy_document)
    client = boto3.client('s3', region_name='us-east-1',
                          aws_access_key_id=access_key['AccessKeyId'],
                          aws_secret_access_key=access_key['SecretAccessKey'])
    client.create_bucket(Bucket=bucket_name)
    with assert_raises(ClientError) as ex:
        client.get_object(Bucket=bucket_name, Key='sdfsdf')
    ex.exception.response['Error']['Code'].should.equal('AccessDenied')
    ex.exception.response['ResponseMetadata']['HTTPStatusCode'].should.equal(403)
    ex.exception.response['Error']['Message'].should.equal('Access Denied')


@set_initial_no_auth_action_count(10)
@mock_iam
@mock_ec2
def test_access_denied_with_many_irrelevant_policies():
    user_name = 'test-user'
    inline_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "ec2:Describe*",
                "Resource": "*"
            }
        ]
    }
    attached_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "s3:*",
                "Resource": "*"
            }
        ]
    }
    group_inline_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Deny",
                "Action": "iam:List*",
                "Resource": "*"
            }
        ]
    }
    group_attached_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Deny",
                "Action": "lambda:*",
                "Resource": "*"
            }
        ]
    }
    access_key = create_user_with_access_key_and_multiple_policies(user_name, inline_policy_document,
                                                                   attached_policy_document)
    create_group_with_multiple_policies_and_add_user(user_name, group_inline_policy_document,
                                                     group_attached_policy_document)
    client = boto3.client('ec2', region_name='us-east-1',
                          aws_access_key_id=access_key['AccessKeyId'],
                          aws_secret_access_key=access_key['SecretAccessKey'])
    with assert_raises(ClientError) as ex:
        client.create_key_pair(KeyName="TestKey")
    ex.exception.response['Error']['Code'].should.equal('AccessDenied')
    ex.exception.response['ResponseMetadata']['HTTPStatusCode'].should.equal(403)
    ex.exception.response['Error']['Message'].should.equal(
        'User: arn:aws:iam::{account_id}:user/{user_name} is not authorized to perform: {operation}'.format(
            account_id=ACCOUNT_ID,
            user_name=user_name,
            operation="ec2:CreateKeyPair"
        )
    )


@set_initial_no_auth_action_count(4)
@mock_iam
@mock_sts
@mock_ec2
@mock_elbv2
def test_allowed_with_temporary_credentials():
    role_name = 'test-role'
    trust_policy_document = {
        "Version": "2012-10-17",
        "Statement": {
            "Effect": "Allow",
            "Principal": {"AWS": "arn:aws:iam::{account_id}:root".format(account_id=ACCOUNT_ID)},
            "Action": "sts:AssumeRole"
        }
    }
    attached_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "elasticloadbalancing:CreateLoadBalancer",
                    "ec2:DescribeSubnets"
                ],
                "Resource": "*"
            }
        ]
    }
    credentials = create_role_with_attached_policy_and_assume_it(role_name, trust_policy_document, attached_policy_document)
    elbv2_client = boto3.client('elbv2', region_name='us-east-1',
                                aws_access_key_id=credentials['AccessKeyId'],
                                aws_secret_access_key=credentials['SecretAccessKey'],
                                aws_session_token=credentials['SessionToken'])
    ec2_client = boto3.client('ec2', region_name='us-east-1',
                              aws_access_key_id=credentials['AccessKeyId'],
                              aws_secret_access_key=credentials['SecretAccessKey'],
                              aws_session_token=credentials['SessionToken'])
    subnets = ec2_client.describe_subnets()['Subnets']
    len(subnets).should.be.greater_than(1)
    elbv2_client.create_load_balancer(
        Name='test-load-balancer',
        Subnets=[
            subnets[0]['SubnetId'],
            subnets[1]['SubnetId']
        ]
    )['LoadBalancers'].should.have.length_of(1)


@set_initial_no_auth_action_count(3)
@mock_iam
@mock_sts
@mock_rds2
def test_access_denied_with_temporary_credentials():
    role_name = 'test-role'
    session_name = 'test-session'
    trust_policy_document = {
        "Version": "2012-10-17",
        "Statement": {
            "Effect": "Allow",
            "Principal": {"AWS": "arn:aws:iam::{account_id}:root".format(account_id=ACCOUNT_ID)},
            "Action": "sts:AssumeRole"
        }
    }
    attached_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    'rds:Describe*'
                ],
                "Resource": "*"
            }
        ]
    }
    credentials = create_role_with_inline_policy_and_assume_it(role_name, trust_policy_document,
                                                               attached_policy_document, session_name)
    client = boto3.client('rds', region_name='us-east-1',
                          aws_access_key_id=credentials['AccessKeyId'],
                          aws_secret_access_key=credentials['SecretAccessKey'],
                          aws_session_token=credentials['SessionToken'])
    with assert_raises(ClientError) as ex:
        client.create_db_instance(
            DBInstanceIdentifier='test-db-instance',
            DBInstanceClass='db.t3',
            Engine='aurora-postgresql'
        )
    ex.exception.response['Error']['Code'].should.equal('AccessDenied')
    ex.exception.response['ResponseMetadata']['HTTPStatusCode'].should.equal(403)
    ex.exception.response['Error']['Message'].should.equal(
        'User: arn:aws:sts::{account_id}:assumed-role/{role_name}/{session_name} is not authorized to perform: {operation}'.format(
            account_id=ACCOUNT_ID,
            role_name=role_name,
            session_name=session_name,
            operation="rds:CreateDBInstance"
        )
    )


@set_initial_no_auth_action_count(3)
@mock_iam
def test_get_user_from_credentials():
    user_name = 'new-test-user'
    inline_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "iam:*",
                "Resource": "*"
            }
        ]
    }
    access_key = create_user_with_access_key_and_inline_policy(user_name, inline_policy_document)
    client = boto3.client('iam', region_name='us-east-1',
                          aws_access_key_id=access_key['AccessKeyId'],
                          aws_secret_access_key=access_key['SecretAccessKey'])
    client.get_user()['User']['UserName'].should.equal(user_name)


@set_initial_no_auth_action_count(0)
@mock_s3
def test_s3_invalid_access_key_id():
    client = boto3.client('s3', region_name='us-east-1', aws_access_key_id='invalid', aws_secret_access_key='invalid')
    with assert_raises(ClientError) as ex:
        client.list_buckets()
    ex.exception.response['Error']['Code'].should.equal('InvalidAccessKeyId')
    ex.exception.response['ResponseMetadata']['HTTPStatusCode'].should.equal(403)
    ex.exception.response['Error']['Message'].should.equal('The AWS Access Key Id you provided does not exist in our records.')


@set_initial_no_auth_action_count(3)
@mock_s3
@mock_iam
def test_s3_signature_does_not_match():
    bucket_name = 'test-bucket'
    access_key = create_user_with_access_key()
    client = boto3.client('s3', region_name='us-east-1',
                          aws_access_key_id=access_key['AccessKeyId'],
                          aws_secret_access_key='invalid')
    client.create_bucket(Bucket=bucket_name)
    with assert_raises(ClientError) as ex:
        client.put_object(Bucket=bucket_name, Key="abc")
    ex.exception.response['Error']['Code'].should.equal('SignatureDoesNotMatch')
    ex.exception.response['ResponseMetadata']['HTTPStatusCode'].should.equal(403)
    ex.exception.response['Error']['Message'].should.equal('The request signature we calculated does not match the signature you provided. Check your key and signing method.')


@set_initial_no_auth_action_count(7)
@mock_s3
@mock_iam
def test_s3_access_denied_not_action():
    user_name = 'test-user'
    bucket_name = 'test-bucket'
    inline_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "*",
                "Resource": "*"
            }
        ]
    }
    group_inline_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Deny",
                "NotAction": "iam:GetUser",
                "Resource": "*"
            }
        ]
    }
    access_key = create_user_with_access_key_and_inline_policy(user_name, inline_policy_document)
    create_group_with_inline_policy_and_add_user(user_name, group_inline_policy_document)
    client = boto3.client('s3', region_name='us-east-1',
                          aws_access_key_id=access_key['AccessKeyId'],
                          aws_secret_access_key=access_key['SecretAccessKey'])
    client.create_bucket(Bucket=bucket_name)
    with assert_raises(ClientError) as ex:
        client.delete_object(Bucket=bucket_name, Key='sdfsdf')
    ex.exception.response['Error']['Code'].should.equal('AccessDenied')
    ex.exception.response['ResponseMetadata']['HTTPStatusCode'].should.equal(403)
    ex.exception.response['Error']['Message'].should.equal('Access Denied')


@set_initial_no_auth_action_count(4)
@mock_iam
@mock_sts
@mock_s3
def test_s3_invalid_token_with_temporary_credentials():
    role_name = 'test-role'
    session_name = 'test-session'
    bucket_name = 'test-bucket-888'
    trust_policy_document = {
        "Version": "2012-10-17",
        "Statement": {
            "Effect": "Allow",
            "Principal": {"AWS": "arn:aws:iam::{account_id}:root".format(account_id=ACCOUNT_ID)},
            "Action": "sts:AssumeRole"
        }
    }
    attached_policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    '*'
                ],
                "Resource": "*"
            }
        ]
    }
    credentials = create_role_with_inline_policy_and_assume_it(role_name, trust_policy_document,
                                                               attached_policy_document, session_name)
    client = boto3.client('s3', region_name='us-east-1',
                          aws_access_key_id=credentials['AccessKeyId'],
                          aws_secret_access_key=credentials['SecretAccessKey'],
                          aws_session_token='invalid')
    client.create_bucket(Bucket=bucket_name)
    with assert_raises(ClientError) as ex:
        client.list_bucket_metrics_configurations(Bucket=bucket_name)
    ex.exception.response['Error']['Code'].should.equal('InvalidToken')
    ex.exception.response['ResponseMetadata']['HTTPStatusCode'].should.equal(400)
    ex.exception.response['Error']['Message'].should.equal('The provided token is malformed or otherwise invalid.')
