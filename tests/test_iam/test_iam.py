from __future__ import unicode_literals
import base64
import json

import boto
import boto3
import os
import sure  # noqa
import sys
from boto.exception import BotoServerError
from botocore.exceptions import ClientError
from moto import mock_iam, mock_iam_deprecated
from moto.iam.models import aws_managed_policies
from nose.tools import assert_raises, assert_equals
from nose.tools import raises

from datetime import datetime
from tests.helpers import requires_boto_gte


MOCK_CERT = """-----BEGIN CERTIFICATE-----
MIIBpzCCARACCQCY5yOdxCTrGjANBgkqhkiG9w0BAQsFADAXMRUwEwYDVQQKDAxt
b3RvIHRlc3RpbmcwIBcNMTgxMTA1MTkwNTIwWhgPMjI5MjA4MTkxOTA1MjBaMBcx
FTATBgNVBAoMDG1vdG8gdGVzdGluZzCBnzANBgkqhkiG9w0BAQEFAAOBjQAwgYkC
gYEA1Jn3g2h7LD3FLqdpcYNbFXCS4V4eDpuTCje9vKFcC3pi/01147X3zdfPy8Mt
ZhKxcREOwm4NXykh23P9KW7fBovpNwnbYsbPqj8Hf1ZaClrgku1arTVhEnKjx8zO
vaR/bVLCss4uE0E0VM1tJn/QGQsfthFsjuHtwx8uIWz35tUCAwEAATANBgkqhkiG
9w0BAQsFAAOBgQBWdOQ7bDc2nWkUhFjZoNIZrqjyNdjlMUndpwREVD7FQ/DuxJMj
FyDHrtlrS80dPUQWNYHw++oACDpWO01LGLPPrGmuO/7cOdojPEd852q5gd+7W9xt
8vUH+pBa6IBLbvBp+szli51V3TLSWcoyy4ceJNQU2vCkTLoFdS0RLd/7tQ==
-----END CERTIFICATE-----"""

MOCK_POLICY = """
{
  "Version": "2012-10-17",
  "Statement":
    {
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::example_bucket"
    }
}
"""

MOCK_POLICY_2 = """
{
  "Version": "2012-10-17",
  "Id": "2",
  "Statement":
    {
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::example_bucket"
    }
}
"""

MOCK_POLICY_3 = """
{
  "Version": "2012-10-17",
  "Id": "3",
  "Statement":
    {
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::example_bucket"
    }
}
"""


@mock_iam_deprecated()
def test_get_all_server_certs():
    conn = boto.connect_iam()

    conn.upload_server_cert("certname", "certbody", "privatekey")
    certs = conn.get_all_server_certs()['list_server_certificates_response'][
        'list_server_certificates_result']['server_certificate_metadata_list']
    certs.should.have.length_of(1)
    cert1 = certs[0]
    cert1.server_certificate_name.should.equal("certname")
    cert1.arn.should.equal(
        "arn:aws:iam::123456789012:server-certificate/certname")


@mock_iam_deprecated()
def test_get_server_cert_doesnt_exist():
    conn = boto.connect_iam()

    with assert_raises(BotoServerError):
        conn.get_server_certificate("NonExistant")


@mock_iam_deprecated()
def test_get_server_cert():
    conn = boto.connect_iam()

    conn.upload_server_cert("certname", "certbody", "privatekey")
    cert = conn.get_server_certificate("certname")
    cert.server_certificate_name.should.equal("certname")
    cert.arn.should.equal(
        "arn:aws:iam::123456789012:server-certificate/certname")


@mock_iam_deprecated()
def test_upload_server_cert():
    conn = boto.connect_iam()

    conn.upload_server_cert("certname", "certbody", "privatekey")
    cert = conn.get_server_certificate("certname")
    cert.server_certificate_name.should.equal("certname")
    cert.arn.should.equal(
        "arn:aws:iam::123456789012:server-certificate/certname")


@mock_iam_deprecated()
def test_delete_server_cert():
    conn = boto.connect_iam()

    conn.upload_server_cert("certname", "certbody", "privatekey")
    conn.get_server_certificate("certname")
    conn.delete_server_cert("certname")
    with assert_raises(BotoServerError):
        conn.get_server_certificate("certname")
    with assert_raises(BotoServerError):
        conn.delete_server_cert("certname")


@mock_iam_deprecated()
@raises(BotoServerError)
def test_get_role__should_throw__when_role_does_not_exist():
    conn = boto.connect_iam()

    conn.get_role('unexisting_role')


@mock_iam_deprecated()
@raises(BotoServerError)
def test_get_instance_profile__should_throw__when_instance_profile_does_not_exist():
    conn = boto.connect_iam()

    conn.get_instance_profile('unexisting_instance_profile')


@mock_iam_deprecated()
def test_create_role_and_instance_profile():
    conn = boto.connect_iam()
    conn.create_instance_profile("my-profile", path="my-path")
    conn.create_role(
        "my-role", assume_role_policy_document="some policy", path="my-path")

    conn.add_role_to_instance_profile("my-profile", "my-role")

    role = conn.get_role("my-role")
    role.path.should.equal("my-path")
    role.assume_role_policy_document.should.equal("some policy")

    profile = conn.get_instance_profile("my-profile")
    profile.path.should.equal("my-path")
    role_from_profile = list(profile.roles.values())[0]
    role_from_profile['role_id'].should.equal(role.role_id)
    role_from_profile['role_name'].should.equal("my-role")

    conn.list_roles().roles[0].role_name.should.equal('my-role')

    # Test with an empty path:
    profile = conn.create_instance_profile('my-other-profile')
    profile.path.should.equal('/')

@mock_iam_deprecated()
def test_remove_role_from_instance_profile():
    conn = boto.connect_iam()
    conn.create_instance_profile("my-profile", path="my-path")
    conn.create_role(
        "my-role", assume_role_policy_document="some policy", path="my-path")
    conn.add_role_to_instance_profile("my-profile", "my-role")

    profile = conn.get_instance_profile("my-profile")
    role_from_profile = list(profile.roles.values())[0]
    role_from_profile['role_name'].should.equal("my-role")

    conn.remove_role_from_instance_profile("my-profile", "my-role")

    profile = conn.get_instance_profile("my-profile")
    dict(profile.roles).should.be.empty


@mock_iam()
def test_get_login_profile():
    conn = boto3.client('iam', region_name='us-east-1')
    conn.create_user(UserName='my-user')
    conn.create_login_profile(UserName='my-user', Password='my-pass')

    response = conn.get_login_profile(UserName='my-user')
    response['LoginProfile']['UserName'].should.equal('my-user')


@mock_iam()
def test_update_login_profile():
    conn = boto3.client('iam', region_name='us-east-1')
    conn.create_user(UserName='my-user')
    conn.create_login_profile(UserName='my-user', Password='my-pass')
    response = conn.get_login_profile(UserName='my-user')
    response['LoginProfile'].get('PasswordResetRequired').should.equal(None)

    conn.update_login_profile(UserName='my-user', Password='new-pass', PasswordResetRequired=True)
    response = conn.get_login_profile(UserName='my-user')
    response['LoginProfile'].get('PasswordResetRequired').should.equal(True)


@mock_iam()
def test_delete_role():
    conn = boto3.client('iam', region_name='us-east-1')

    with assert_raises(ClientError):
        conn.delete_role(RoleName="my-role")

    conn.create_role(RoleName="my-role", AssumeRolePolicyDocument="some policy", Path="/my-path/")
    role = conn.get_role(RoleName="my-role")
    role.get('Role').get('Arn').should.equal('arn:aws:iam::123456789012:role/my-path/my-role')

    conn.delete_role(RoleName="my-role")

    with assert_raises(ClientError):
        conn.get_role(RoleName="my-role")


@mock_iam_deprecated()
def test_list_instance_profiles():
    conn = boto.connect_iam()
    conn.create_instance_profile("my-profile", path="my-path")
    conn.create_role("my-role", path="my-path")

    conn.add_role_to_instance_profile("my-profile", "my-role")

    profiles = conn.list_instance_profiles().instance_profiles

    len(profiles).should.equal(1)
    profiles[0].instance_profile_name.should.equal("my-profile")
    profiles[0].roles.role_name.should.equal("my-role")


@mock_iam_deprecated()
def test_list_instance_profiles_for_role():
    conn = boto.connect_iam()

    conn.create_role(role_name="my-role",
                     assume_role_policy_document="some policy", path="my-path")
    conn.create_role(role_name="my-role2",
                     assume_role_policy_document="some policy2", path="my-path2")

    profile_name_list = ['my-profile', 'my-profile2']
    profile_path_list = ['my-path', 'my-path2']
    for profile_count in range(0, 2):
        conn.create_instance_profile(
            profile_name_list[profile_count], path=profile_path_list[profile_count])

    for profile_count in range(0, 2):
        conn.add_role_to_instance_profile(
            profile_name_list[profile_count], "my-role")

    profile_dump = conn.list_instance_profiles_for_role(role_name="my-role")
    profile_list = profile_dump['list_instance_profiles_for_role_response'][
        'list_instance_profiles_for_role_result']['instance_profiles']
    for profile_count in range(0, len(profile_list)):
        profile_name_list.remove(profile_list[profile_count][
                                 "instance_profile_name"])
        profile_path_list.remove(profile_list[profile_count]["path"])
        profile_list[profile_count]["roles"]["member"][
            "role_name"].should.equal("my-role")

    len(profile_name_list).should.equal(0)
    len(profile_path_list).should.equal(0)

    profile_dump2 = conn.list_instance_profiles_for_role(role_name="my-role2")
    profile_list = profile_dump2['list_instance_profiles_for_role_response'][
        'list_instance_profiles_for_role_result']['instance_profiles']
    len(profile_list).should.equal(0)


@mock_iam_deprecated()
def test_list_role_policies():
    conn = boto.connect_iam()
    conn.create_role("my-role")
    conn.put_role_policy("my-role", "test policy", MOCK_POLICY)
    role = conn.list_role_policies("my-role")
    role.policy_names.should.have.length_of(1)
    role.policy_names[0].should.equal("test policy")

    conn.put_role_policy("my-role", "test policy 2", MOCK_POLICY)
    role = conn.list_role_policies("my-role")
    role.policy_names.should.have.length_of(2)

    conn.delete_role_policy("my-role", "test policy")
    role = conn.list_role_policies("my-role")
    role.policy_names.should.have.length_of(1)
    role.policy_names[0].should.equal("test policy 2")

    with assert_raises(BotoServerError):
        conn.delete_role_policy("my-role", "test policy")


@mock_iam_deprecated()
def test_put_role_policy():
    conn = boto.connect_iam()
    conn.create_role(
        "my-role", assume_role_policy_document="some policy", path="my-path")
    conn.put_role_policy("my-role", "test policy", MOCK_POLICY)
    policy = conn.get_role_policy(
        "my-role", "test policy")['get_role_policy_response']['get_role_policy_result']['policy_name']
    policy.should.equal("test policy")


@mock_iam_deprecated()
def test_update_assume_role_policy():
    conn = boto.connect_iam()
    role = conn.create_role("my-role")
    conn.update_assume_role_policy(role.role_name, "my-policy")
    role = conn.get_role("my-role")
    role.assume_role_policy_document.should.equal("my-policy")


@mock_iam
def test_create_policy():
    conn = boto3.client('iam', region_name='us-east-1')
    response = conn.create_policy(
        PolicyName="TestCreatePolicy",
        PolicyDocument=MOCK_POLICY)
    response['Policy']['Arn'].should.equal("arn:aws:iam::123456789012:policy/TestCreatePolicy")


@mock_iam
def test_create_policy_versions():
    conn = boto3.client('iam', region_name='us-east-1')
    with assert_raises(ClientError):
        conn.create_policy_version(
            PolicyArn="arn:aws:iam::123456789012:policy/TestCreatePolicyVersion",
            PolicyDocument='{"some":"policy"}')
    conn.create_policy(
        PolicyName="TestCreatePolicyVersion",
        PolicyDocument=MOCK_POLICY)
    version = conn.create_policy_version(
        PolicyArn="arn:aws:iam::123456789012:policy/TestCreatePolicyVersion",
        PolicyDocument=MOCK_POLICY,
        SetAsDefault=True)
    version.get('PolicyVersion').get('Document').should.equal(json.loads(MOCK_POLICY))
    version.get('PolicyVersion').get('VersionId').should.equal("v2")
    conn.delete_policy_version(
        PolicyArn="arn:aws:iam::123456789012:policy/TestCreatePolicyVersion",
        VersionId="v1")
    version = conn.create_policy_version(
        PolicyArn="arn:aws:iam::123456789012:policy/TestCreatePolicyVersion",
        PolicyDocument=MOCK_POLICY)
    version.get('PolicyVersion').get('VersionId').should.equal("v3")


@mock_iam
def test_get_policy():
    conn = boto3.client('iam', region_name='us-east-1')
    response = conn.create_policy(
        PolicyName="TestGetPolicy",
        PolicyDocument=MOCK_POLICY)
    policy = conn.get_policy(
        PolicyArn="arn:aws:iam::123456789012:policy/TestGetPolicy")
    policy['Policy']['Arn'].should.equal("arn:aws:iam::123456789012:policy/TestGetPolicy")


@mock_iam
def test_get_aws_managed_policy():
    conn = boto3.client('iam', region_name='us-east-1')
    managed_policy_arn = 'arn:aws:iam::aws:policy/IAMUserChangePassword'
    managed_policy_create_date = datetime.strptime("2016-11-15T00:25:16+00:00", "%Y-%m-%dT%H:%M:%S+00:00")
    policy = conn.get_policy(
        PolicyArn=managed_policy_arn)
    policy['Policy']['Arn'].should.equal(managed_policy_arn)
    policy['Policy']['CreateDate'].replace(tzinfo=None).should.equal(managed_policy_create_date)


@mock_iam
def test_get_policy_version():
    conn = boto3.client('iam', region_name='us-east-1')
    conn.create_policy(
        PolicyName="TestGetPolicyVersion",
        PolicyDocument=MOCK_POLICY)
    version = conn.create_policy_version(
        PolicyArn="arn:aws:iam::123456789012:policy/TestGetPolicyVersion",
        PolicyDocument=MOCK_POLICY)
    with assert_raises(ClientError):
        conn.get_policy_version(
            PolicyArn="arn:aws:iam::123456789012:policy/TestGetPolicyVersion",
            VersionId='v2-does-not-exist')
    retrieved = conn.get_policy_version(
        PolicyArn="arn:aws:iam::123456789012:policy/TestGetPolicyVersion",
        VersionId=version.get('PolicyVersion').get('VersionId'))
    retrieved.get('PolicyVersion').get('Document').should.equal(json.loads(MOCK_POLICY))


@mock_iam
def test_get_aws_managed_policy_version():
    conn = boto3.client('iam', region_name='us-east-1')
    managed_policy_arn = 'arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
    managed_policy_version_create_date = datetime.strptime("2015-04-09T15:03:43+00:00", "%Y-%m-%dT%H:%M:%S+00:00")
    with assert_raises(ClientError):
        conn.get_policy_version(
            PolicyArn=managed_policy_arn,
            VersionId='v2-does-not-exist')
    retrieved = conn.get_policy_version(
        PolicyArn=managed_policy_arn,
        VersionId="v1")
    retrieved['PolicyVersion']['CreateDate'].replace(tzinfo=None).should.equal(managed_policy_version_create_date)
    retrieved['PolicyVersion']['Document'].should.be.an(dict)


@mock_iam
def test_get_aws_managed_policy_v4_version():
    conn = boto3.client('iam', region_name='us-east-1')
    managed_policy_arn = 'arn:aws:iam::aws:policy/job-function/SystemAdministrator'
    managed_policy_version_create_date = datetime.strptime("2018-10-08T21:33:45+00:00", "%Y-%m-%dT%H:%M:%S+00:00")
    with assert_raises(ClientError):
        conn.get_policy_version(
            PolicyArn=managed_policy_arn,
            VersionId='v2-does-not-exist')
    retrieved = conn.get_policy_version(
        PolicyArn=managed_policy_arn,
        VersionId="v4")
    retrieved['PolicyVersion']['CreateDate'].replace(tzinfo=None).should.equal(managed_policy_version_create_date)
    retrieved['PolicyVersion']['Document'].should.be.an(dict)


@mock_iam
def test_list_policy_versions():
    conn = boto3.client('iam', region_name='us-east-1')
    with assert_raises(ClientError):
        versions = conn.list_policy_versions(
            PolicyArn="arn:aws:iam::123456789012:policy/TestListPolicyVersions")
    conn.create_policy(
        PolicyName="TestListPolicyVersions",
        PolicyDocument=MOCK_POLICY)
    versions = conn.list_policy_versions(
        PolicyArn="arn:aws:iam::123456789012:policy/TestListPolicyVersions")
    versions.get('Versions')[0].get('VersionId').should.equal('v1')

    conn.create_policy_version(
        PolicyArn="arn:aws:iam::123456789012:policy/TestListPolicyVersions",
        PolicyDocument=MOCK_POLICY_2)
    conn.create_policy_version(
        PolicyArn="arn:aws:iam::123456789012:policy/TestListPolicyVersions",
        PolicyDocument=MOCK_POLICY_3)
    versions = conn.list_policy_versions(
        PolicyArn="arn:aws:iam::123456789012:policy/TestListPolicyVersions")
    print(versions.get('Versions'))
    versions.get('Versions')[1].get('Document').should.equal(json.loads(MOCK_POLICY_2))
    versions.get('Versions')[2].get('Document').should.equal(json.loads(MOCK_POLICY_3))


@mock_iam
def test_delete_policy_version():
    conn = boto3.client('iam', region_name='us-east-1')
    conn.create_policy(
        PolicyName="TestDeletePolicyVersion",
        PolicyDocument=MOCK_POLICY)
    conn.create_policy_version(
        PolicyArn="arn:aws:iam::123456789012:policy/TestDeletePolicyVersion",
        PolicyDocument=MOCK_POLICY)
    with assert_raises(ClientError):
        conn.delete_policy_version(
            PolicyArn="arn:aws:iam::123456789012:policy/TestDeletePolicyVersion",
            VersionId='v2-nope-this-does-not-exist')
    conn.delete_policy_version(
        PolicyArn="arn:aws:iam::123456789012:policy/TestDeletePolicyVersion",
        VersionId='v2')
    versions = conn.list_policy_versions(
        PolicyArn="arn:aws:iam::123456789012:policy/TestDeletePolicyVersion")
    len(versions.get('Versions')).should.equal(1)


@mock_iam_deprecated()
def test_create_user():
    conn = boto.connect_iam()
    conn.create_user('my-user')
    with assert_raises(BotoServerError):
        conn.create_user('my-user')


@mock_iam_deprecated()
def test_get_user():
    conn = boto.connect_iam()
    with assert_raises(BotoServerError):
        conn.get_user('my-user')
    conn.create_user('my-user')
    conn.get_user('my-user')


@mock_iam()
def test_update_user():
    conn = boto3.client('iam', region_name='us-east-1')
    with assert_raises(conn.exceptions.NoSuchEntityException):
        conn.update_user(UserName='my-user')
    conn.create_user(UserName='my-user')
    conn.update_user(UserName='my-user', NewPath='/new-path/', NewUserName='new-user')
    response = conn.get_user(UserName='new-user')
    response['User'].get('Path').should.equal('/new-path/')
    with assert_raises(conn.exceptions.NoSuchEntityException):
        conn.get_user(UserName='my-user')


@mock_iam_deprecated()
def test_get_current_user():
    """If no user is specific, IAM returns the current user"""
    conn = boto.connect_iam()
    user = conn.get_user()['get_user_response']['get_user_result']['user']
    user['user_name'].should.equal('default_user')


@mock_iam()
def test_list_users():
    path_prefix = '/'
    max_items = 10
    conn = boto3.client('iam', region_name='us-east-1')
    conn.create_user(UserName='my-user')
    response = conn.list_users(PathPrefix=path_prefix, MaxItems=max_items)
    user = response['Users'][0]
    user['UserName'].should.equal('my-user')
    user['Path'].should.equal('/')
    user['Arn'].should.equal('arn:aws:iam::123456789012:user/my-user')


@mock_iam()
def test_user_policies():
    policy_name = 'UserManagedPolicy'
    user_name = 'my-user'
    conn = boto3.client('iam', region_name='us-east-1')
    conn.create_user(UserName=user_name)
    conn.put_user_policy(
        UserName=user_name,
        PolicyName=policy_name,
        PolicyDocument=MOCK_POLICY
    )

    policy_doc = conn.get_user_policy(
        UserName=user_name,
        PolicyName=policy_name
    )
    policy_doc['PolicyDocument'].should.equal(json.loads(MOCK_POLICY))

    policies = conn.list_user_policies(UserName=user_name)
    len(policies['PolicyNames']).should.equal(1)
    policies['PolicyNames'][0].should.equal(policy_name)

    conn.delete_user_policy(
        UserName=user_name,
        PolicyName=policy_name
    )

    policies = conn.list_user_policies(UserName=user_name)
    len(policies['PolicyNames']).should.equal(0)


@mock_iam_deprecated()
def test_create_login_profile():
    conn = boto.connect_iam()
    with assert_raises(BotoServerError):
        conn.create_login_profile('my-user', 'my-pass')
    conn.create_user('my-user')
    conn.create_login_profile('my-user', 'my-pass')
    with assert_raises(BotoServerError):
        conn.create_login_profile('my-user', 'my-pass')


@mock_iam_deprecated()
def test_delete_login_profile():
    conn = boto.connect_iam()
    conn.create_user('my-user')
    with assert_raises(BotoServerError):
        conn.delete_login_profile('my-user')
    conn.create_login_profile('my-user', 'my-pass')
    conn.delete_login_profile('my-user')


@mock_iam_deprecated()
def test_create_access_key():
    conn = boto.connect_iam()
    with assert_raises(BotoServerError):
        conn.create_access_key('my-user')
    conn.create_user('my-user')
    conn.create_access_key('my-user')


@mock_iam_deprecated()
def test_get_all_access_keys():
    """If no access keys exist there should be none in the response,
    if an access key is present it should have the correct fields present"""
    conn = boto.connect_iam()
    conn.create_user('my-user')
    response = conn.get_all_access_keys('my-user')
    assert_equals(
        response['list_access_keys_response'][
            'list_access_keys_result']['access_key_metadata'],
        []
    )
    conn.create_access_key('my-user')
    response = conn.get_all_access_keys('my-user')
    assert_equals(
        sorted(response['list_access_keys_response'][
            'list_access_keys_result']['access_key_metadata'][0].keys()),
        sorted(['status', 'create_date', 'user_name', 'access_key_id'])
    )


@mock_iam_deprecated()
def test_delete_access_key():
    conn = boto.connect_iam()
    conn.create_user('my-user')
    access_key_id = conn.create_access_key('my-user')['create_access_key_response'][
        'create_access_key_result']['access_key']['access_key_id']
    conn.delete_access_key(access_key_id, 'my-user')


@mock_iam()
def test_mfa_devices():
    # Test enable device
    conn = boto3.client('iam', region_name='us-east-1')
    conn.create_user(UserName='my-user')
    conn.enable_mfa_device(
        UserName='my-user',
        SerialNumber='123456789',
        AuthenticationCode1='234567',
        AuthenticationCode2='987654'
    )

    # Test list mfa devices
    response = conn.list_mfa_devices(UserName='my-user')
    device = response['MFADevices'][0]
    device['SerialNumber'].should.equal('123456789')

    # Test deactivate mfa device
    conn.deactivate_mfa_device(UserName='my-user', SerialNumber='123456789')
    response = conn.list_mfa_devices(UserName='my-user')
    len(response['MFADevices']).should.equal(0)


@mock_iam_deprecated()
def test_delete_user():
    conn = boto.connect_iam()
    with assert_raises(BotoServerError):
        conn.delete_user('my-user')
    conn.create_user('my-user')
    conn.delete_user('my-user')


@mock_iam_deprecated()
def test_generate_credential_report():
    conn = boto.connect_iam()
    result = conn.generate_credential_report()
    result['generate_credential_report_response'][
        'generate_credential_report_result']['state'].should.equal('STARTED')
    result = conn.generate_credential_report()
    result['generate_credential_report_response'][
        'generate_credential_report_result']['state'].should.equal('COMPLETE')

@mock_iam
def test_boto3_generate_credential_report():
    conn = boto3.client('iam', region_name='us-east-1')
    result = conn.generate_credential_report()
    result['State'].should.equal('STARTED')
    result = conn.generate_credential_report()
    result['State'].should.equal('COMPLETE')


@mock_iam_deprecated()
def test_get_credential_report():
    conn = boto.connect_iam()
    conn.create_user('my-user')
    with assert_raises(BotoServerError):
        conn.get_credential_report()
    result = conn.generate_credential_report()
    while result['generate_credential_report_response']['generate_credential_report_result']['state'] != 'COMPLETE':
        result = conn.generate_credential_report()
    result = conn.get_credential_report()
    report = base64.b64decode(result['get_credential_report_response'][
                              'get_credential_report_result']['content'].encode('ascii')).decode('ascii')
    report.should.match(r'.*my-user.*')


@mock_iam
def test_boto3_get_credential_report():
    conn = boto3.client('iam', region_name='us-east-1')
    conn.create_user(UserName='my-user')
    with assert_raises(ClientError):
        conn.get_credential_report()
    result = conn.generate_credential_report()
    while result['State'] != 'COMPLETE':
        result = conn.generate_credential_report()
    result = conn.get_credential_report()
    report = result['Content'].decode('utf-8')
    report.should.match(r'.*my-user.*')


@requires_boto_gte('2.39')
@mock_iam_deprecated()
def test_managed_policy():
    conn = boto.connect_iam()

    conn.create_policy(policy_name='UserManagedPolicy',
                       policy_document=MOCK_POLICY,
                       path='/mypolicy/',
                       description='my user managed policy')

    marker = 0
    aws_policies = []
    while marker is not None:
        response = conn.list_policies(scope='AWS', marker=marker)[
                'list_policies_response']['list_policies_result']
        for policy in response['policies']:
            aws_policies.append(policy)
        marker = response.get('marker')
    set(p.name for p in aws_managed_policies).should.equal(
        set(p['policy_name'] for p in aws_policies))

    user_policies = conn.list_policies(scope='Local')['list_policies_response'][
        'list_policies_result']['policies']
    set(['UserManagedPolicy']).should.equal(
        set(p['policy_name'] for p in user_policies))

    marker = 0
    all_policies = []
    while marker is not None:
        response = conn.list_policies(marker=marker)[
                'list_policies_response']['list_policies_result']
        for policy in response['policies']:
            all_policies.append(policy)
        marker = response.get('marker')
    set(p['policy_name'] for p in aws_policies +
        user_policies).should.equal(set(p['policy_name'] for p in all_policies))

    role_name = 'my-role'
    conn.create_role(role_name, assume_role_policy_document={
                     'policy': 'test'}, path="my-path")
    for policy_name in ['AmazonElasticMapReduceRole',
                        'AmazonElasticMapReduceforEC2Role']:
        policy_arn = 'arn:aws:iam::aws:policy/service-role/' + policy_name
        conn.attach_role_policy(policy_arn, role_name)

    rows = conn.list_policies(only_attached=True)['list_policies_response'][
        'list_policies_result']['policies']
    rows.should.have.length_of(2)
    for x in rows:
        int(x['attachment_count']).should.be.greater_than(0)

    # boto has not implemented this end point but accessible this way
    resp = conn.get_response('ListAttachedRolePolicies',
                             {'RoleName': role_name},
                             list_marker='AttachedPolicies')
    resp['list_attached_role_policies_response']['list_attached_role_policies_result'][
        'attached_policies'].should.have.length_of(2)

    conn.detach_role_policy(
        "arn:aws:iam::aws:policy/service-role/AmazonElasticMapReduceRole",
        role_name)
    rows = conn.list_policies(only_attached=True)['list_policies_response'][
        'list_policies_result']['policies']
    rows.should.have.length_of(1)
    for x in rows:
        int(x['attachment_count']).should.be.greater_than(0)

    # boto has not implemented this end point but accessible this way
    resp = conn.get_response('ListAttachedRolePolicies',
                             {'RoleName': role_name},
                             list_marker='AttachedPolicies')
    resp['list_attached_role_policies_response']['list_attached_role_policies_result'][
        'attached_policies'].should.have.length_of(1)

    with assert_raises(BotoServerError):
        conn.detach_role_policy(
            "arn:aws:iam::aws:policy/service-role/AmazonElasticMapReduceRole",
            role_name)

    with assert_raises(BotoServerError):
        conn.detach_role_policy(
            "arn:aws:iam::aws:policy/Nonexistent", role_name)


@mock_iam
def test_boto3_create_login_profile():
    conn = boto3.client('iam', region_name='us-east-1')

    with assert_raises(ClientError):
        conn.create_login_profile(UserName='my-user', Password='Password')

    conn.create_user(UserName='my-user')
    conn.create_login_profile(UserName='my-user', Password='Password')

    with assert_raises(ClientError):
        conn.create_login_profile(UserName='my-user', Password='Password')


@mock_iam()
def test_attach_detach_user_policy():
    iam = boto3.resource('iam', region_name='us-east-1')
    client = boto3.client('iam', region_name='us-east-1')

    user = iam.create_user(UserName='test-user')

    policy_name = 'UserAttachedPolicy'
    policy = iam.create_policy(PolicyName=policy_name,
                               PolicyDocument=MOCK_POLICY,
                               Path='/mypolicy/',
                               Description='my user attached policy')

    client.attach_user_policy(UserName=user.name, PolicyArn=policy.arn)

    resp = client.list_attached_user_policies(UserName=user.name)
    resp['AttachedPolicies'].should.have.length_of(1)
    attached_policy = resp['AttachedPolicies'][0]
    attached_policy['PolicyArn'].should.equal(policy.arn)
    attached_policy['PolicyName'].should.equal(policy_name)

    client.detach_user_policy(UserName=user.name, PolicyArn=policy.arn)

    resp = client.list_attached_user_policies(UserName=user.name)
    resp['AttachedPolicies'].should.have.length_of(0)


@mock_iam
def test_update_access_key():
    iam = boto3.resource('iam', region_name='us-east-1')
    client = iam.meta.client
    username = 'test-user'
    iam.create_user(UserName=username)
    with assert_raises(ClientError):
        client.update_access_key(UserName=username,
                                 AccessKeyId='non-existent-key',
                                 Status='Inactive')
    key = client.create_access_key(UserName=username)['AccessKey']
    client.update_access_key(UserName=username,
                             AccessKeyId=key['AccessKeyId'],
                             Status='Inactive')
    resp = client.list_access_keys(UserName=username)
    resp['AccessKeyMetadata'][0]['Status'].should.equal('Inactive')


@mock_iam
def test_get_access_key_last_used():
    iam = boto3.resource('iam', region_name='us-east-1')
    client = iam.meta.client
    username = 'test-user'
    iam.create_user(UserName=username)
    with assert_raises(ClientError):
        client.get_access_key_last_used(AccessKeyId='non-existent-key-id')
    create_key_response = client.create_access_key(UserName=username)['AccessKey']
    resp = client.get_access_key_last_used(AccessKeyId=create_key_response['AccessKeyId'])

    datetime.strftime(resp["AccessKeyLastUsed"]["LastUsedDate"], "%Y-%m-%d").should.equal(datetime.strftime(
        datetime.utcnow(),
        "%Y-%m-%d"
    ))
    resp["UserName"].should.equal(create_key_response["UserName"])


@mock_iam
def test_get_account_authorization_details():
    test_policy = json.dumps({
        "Version": "2012-10-17",
        "Statement": [
            {
                "Action": "s3:ListBucket",
                "Resource": "*",
                "Effect": "Allow",
            }
        ]
    })

    conn = boto3.client('iam', region_name='us-east-1')
    conn.create_role(RoleName="my-role", AssumeRolePolicyDocument="some policy", Path="/my-path/")
    conn.create_user(Path='/', UserName='testUser')
    conn.create_group(Path='/', GroupName='testGroup')
    conn.create_policy(
        PolicyName='testPolicy',
        Path='/',
        PolicyDocument=test_policy,
        Description='Test Policy'
    )

    # Attach things to the user and group:
    conn.put_user_policy(UserName='testUser', PolicyName='testPolicy', PolicyDocument=test_policy)
    conn.put_group_policy(GroupName='testGroup', PolicyName='testPolicy', PolicyDocument=test_policy)

    conn.attach_user_policy(UserName='testUser', PolicyArn='arn:aws:iam::123456789012:policy/testPolicy')
    conn.attach_group_policy(GroupName='testGroup', PolicyArn='arn:aws:iam::123456789012:policy/testPolicy')

    conn.add_user_to_group(UserName='testUser', GroupName='testGroup')

    # Add things to the role:
    conn.create_instance_profile(InstanceProfileName='ipn')
    conn.add_role_to_instance_profile(InstanceProfileName='ipn', RoleName='my-role')
    conn.tag_role(RoleName='my-role', Tags=[
        {
            'Key': 'somekey',
            'Value': 'somevalue'
        },
        {
            'Key': 'someotherkey',
            'Value': 'someothervalue'
        }
    ])
    conn.put_role_policy(RoleName='my-role', PolicyName='test-policy', PolicyDocument=test_policy)
    conn.attach_role_policy(RoleName='my-role', PolicyArn='arn:aws:iam::123456789012:policy/testPolicy')

    result = conn.get_account_authorization_details(Filter=['Role'])
    assert len(result['RoleDetailList']) == 1
    assert len(result['UserDetailList']) == 0
    assert len(result['GroupDetailList']) == 0
    assert len(result['Policies']) == 0
    assert len(result['RoleDetailList'][0]['InstanceProfileList']) == 1
    assert len(result['RoleDetailList'][0]['Tags']) == 2
    assert len(result['RoleDetailList'][0]['RolePolicyList']) == 1
    assert len(result['RoleDetailList'][0]['AttachedManagedPolicies']) == 1
    assert result['RoleDetailList'][0]['AttachedManagedPolicies'][0]['PolicyName'] == 'testPolicy'
    assert result['RoleDetailList'][0]['AttachedManagedPolicies'][0]['PolicyArn'] == \
        'arn:aws:iam::123456789012:policy/testPolicy'

    result = conn.get_account_authorization_details(Filter=['User'])
    assert len(result['RoleDetailList']) == 0
    assert len(result['UserDetailList']) == 1
    assert len(result['UserDetailList'][0]['GroupList']) == 1
    assert len(result['UserDetailList'][0]['AttachedManagedPolicies']) == 1
    assert len(result['GroupDetailList']) == 0
    assert len(result['Policies']) == 0
    assert result['UserDetailList'][0]['AttachedManagedPolicies'][0]['PolicyName'] == 'testPolicy'
    assert result['UserDetailList'][0]['AttachedManagedPolicies'][0]['PolicyArn'] == \
        'arn:aws:iam::123456789012:policy/testPolicy'

    result = conn.get_account_authorization_details(Filter=['Group'])
    assert len(result['RoleDetailList']) == 0
    assert len(result['UserDetailList']) == 0
    assert len(result['GroupDetailList']) == 1
    assert len(result['GroupDetailList'][0]['GroupPolicyList']) == 1
    assert len(result['GroupDetailList'][0]['AttachedManagedPolicies']) == 1
    assert len(result['Policies']) == 0
    assert result['GroupDetailList'][0]['AttachedManagedPolicies'][0]['PolicyName'] == 'testPolicy'
    assert result['GroupDetailList'][0]['AttachedManagedPolicies'][0]['PolicyArn'] == \
        'arn:aws:iam::123456789012:policy/testPolicy'

    result = conn.get_account_authorization_details(Filter=['LocalManagedPolicy'])
    assert len(result['RoleDetailList']) == 0
    assert len(result['UserDetailList']) == 0
    assert len(result['GroupDetailList']) == 0
    assert len(result['Policies']) == 1
    assert len(result['Policies'][0]['PolicyVersionList']) == 1

    # Check for greater than 1 since this should always be greater than one but might change.
    # See iam/aws_managed_policies.py
    result = conn.get_account_authorization_details(Filter=['AWSManagedPolicy'])
    assert len(result['RoleDetailList']) == 0
    assert len(result['UserDetailList']) == 0
    assert len(result['GroupDetailList']) == 0
    assert len(result['Policies']) > 1

    result = conn.get_account_authorization_details()
    assert len(result['RoleDetailList']) == 1
    assert len(result['UserDetailList']) == 1
    assert len(result['GroupDetailList']) == 1
    assert len(result['Policies']) > 1


@mock_iam
def test_signing_certs():
    client = boto3.client('iam', region_name='us-east-1')

    # Create the IAM user first:
    client.create_user(UserName='testing')

    # Upload the cert:
    resp = client.upload_signing_certificate(UserName='testing', CertificateBody=MOCK_CERT)['Certificate']
    cert_id = resp['CertificateId']

    assert resp['UserName'] == 'testing'
    assert resp['Status'] == 'Active'
    assert resp['CertificateBody'] == MOCK_CERT
    assert resp['CertificateId']

    # Upload a the cert with an invalid body:
    with assert_raises(ClientError) as ce:
        client.upload_signing_certificate(UserName='testing', CertificateBody='notacert')
    assert ce.exception.response['Error']['Code'] == 'MalformedCertificate'

    # Upload with an invalid user:
    with assert_raises(ClientError):
        client.upload_signing_certificate(UserName='notauser', CertificateBody=MOCK_CERT)

    # Update:
    client.update_signing_certificate(UserName='testing', CertificateId=cert_id, Status='Inactive')

    with assert_raises(ClientError):
        client.update_signing_certificate(UserName='notauser', CertificateId=cert_id, Status='Inactive')

    with assert_raises(ClientError) as ce:
        client.update_signing_certificate(UserName='testing', CertificateId='x' * 32, Status='Inactive')

    assert ce.exception.response['Error']['Message'] == 'The Certificate with id {id} cannot be found.'.format(
        id='x' * 32)

    # List the certs:
    resp = client.list_signing_certificates(UserName='testing')['Certificates']
    assert len(resp) == 1
    assert resp[0]['CertificateBody'] == MOCK_CERT
    assert resp[0]['Status'] == 'Inactive'  # Changed with the update call above.

    with assert_raises(ClientError):
        client.list_signing_certificates(UserName='notauser')

    # Delete:
    client.delete_signing_certificate(UserName='testing', CertificateId=cert_id)

    with assert_raises(ClientError):
        client.delete_signing_certificate(UserName='notauser', CertificateId=cert_id)


@mock_iam()
def test_create_saml_provider():
    conn = boto3.client('iam', region_name='us-east-1')
    response = conn.create_saml_provider(
        Name="TestSAMLProvider",
        SAMLMetadataDocument='a' * 1024
    )
    response['SAMLProviderArn'].should.equal("arn:aws:iam::123456789012:saml-provider/TestSAMLProvider")


@mock_iam()
def test_get_saml_provider():
    conn = boto3.client('iam', region_name='us-east-1')
    saml_provider_create = conn.create_saml_provider(
        Name="TestSAMLProvider",
        SAMLMetadataDocument='a' * 1024
    )
    response = conn.get_saml_provider(
        SAMLProviderArn=saml_provider_create['SAMLProviderArn']
    )
    response['SAMLMetadataDocument'].should.equal('a' * 1024)


@mock_iam()
def test_list_saml_providers():
    conn = boto3.client('iam', region_name='us-east-1')
    conn.create_saml_provider(
        Name="TestSAMLProvider",
        SAMLMetadataDocument='a' * 1024
    )
    response = conn.list_saml_providers()
    response['SAMLProviderList'][0]['Arn'].should.equal("arn:aws:iam::123456789012:saml-provider/TestSAMLProvider")


@mock_iam()
def test_delete_saml_provider():
    conn = boto3.client('iam', region_name='us-east-1')
    saml_provider_create = conn.create_saml_provider(
        Name="TestSAMLProvider",
        SAMLMetadataDocument='a' * 1024
    )
    response = conn.list_saml_providers()
    len(response['SAMLProviderList']).should.equal(1)
    conn.delete_saml_provider(
        SAMLProviderArn=saml_provider_create['SAMLProviderArn']
    )
    response = conn.list_saml_providers()
    len(response['SAMLProviderList']).should.equal(0)
    conn.create_user(UserName='testing')

    cert_id = '123456789012345678901234'
    with assert_raises(ClientError) as ce:
        conn.delete_signing_certificate(UserName='testing', CertificateId=cert_id)

    assert ce.exception.response['Error']['Message'] == 'The Certificate with id {id} cannot be found.'.format(
        id=cert_id)

    # Verify that it's not in the list:
    resp = conn.list_signing_certificates(UserName='testing')
    assert not resp['Certificates']


@mock_iam()
def test_tag_role():
    """Tests both the tag_role and get_role_tags capability"""
    conn = boto3.client('iam', region_name='us-east-1')
    conn.create_role(RoleName="my-role", AssumeRolePolicyDocument="{}")

    # Get without tags:
    role = conn.get_role(RoleName='my-role')['Role']
    assert not role.get('Tags')

    # With proper tag values:
    conn.tag_role(RoleName='my-role', Tags=[
        {
            'Key': 'somekey',
            'Value': 'somevalue'
        },
        {
            'Key': 'someotherkey',
            'Value': 'someothervalue'
        }
    ])

    # Get role:
    role = conn.get_role(RoleName='my-role')['Role']
    assert len(role['Tags']) == 2
    assert role['Tags'][0]['Key'] == 'somekey'
    assert role['Tags'][0]['Value'] == 'somevalue'
    assert role['Tags'][1]['Key'] == 'someotherkey'
    assert role['Tags'][1]['Value'] == 'someothervalue'

    # Same -- but for list_role_tags:
    tags = conn.list_role_tags(RoleName='my-role')
    assert len(tags['Tags']) == 2
    assert role['Tags'][0]['Key'] == 'somekey'
    assert role['Tags'][0]['Value'] == 'somevalue'
    assert role['Tags'][1]['Key'] == 'someotherkey'
    assert role['Tags'][1]['Value'] == 'someothervalue'
    assert not tags['IsTruncated']
    assert not tags.get('Marker')

    # Test pagination:
    tags = conn.list_role_tags(RoleName='my-role', MaxItems=1)
    assert len(tags['Tags']) == 1
    assert tags['IsTruncated']
    assert tags['Tags'][0]['Key'] == 'somekey'
    assert tags['Tags'][0]['Value'] == 'somevalue'
    assert tags['Marker'] == '1'

    tags = conn.list_role_tags(RoleName='my-role', Marker=tags['Marker'])
    assert len(tags['Tags']) == 1
    assert tags['Tags'][0]['Key'] == 'someotherkey'
    assert tags['Tags'][0]['Value'] == 'someothervalue'
    assert not tags['IsTruncated']
    assert not tags.get('Marker')

    # Test updating an existing tag:
    conn.tag_role(RoleName='my-role', Tags=[
        {
            'Key': 'somekey',
            'Value': 'somenewvalue'
        }
    ])
    tags = conn.list_role_tags(RoleName='my-role')
    assert len(tags['Tags']) == 2
    assert tags['Tags'][0]['Key'] == 'somekey'
    assert tags['Tags'][0]['Value'] == 'somenewvalue'

    # Empty is good:
    conn.tag_role(RoleName='my-role', Tags=[
        {
            'Key': 'somekey',
            'Value': ''
        }
    ])
    tags = conn.list_role_tags(RoleName='my-role')
    assert len(tags['Tags']) == 2
    assert tags['Tags'][0]['Key'] == 'somekey'
    assert tags['Tags'][0]['Value'] == ''

    # Test creating tags with invalid values:
    # With more than 50 tags:
    with assert_raises(ClientError) as ce:
        too_many_tags = list(map(lambda x: {'Key': str(x), 'Value': str(x)}, range(0, 51)))
        conn.tag_role(RoleName='my-role', Tags=too_many_tags)
    assert 'failed to satisfy constraint: Member must have length less than or equal to 50.' \
           in ce.exception.response['Error']['Message']

    # With a duplicate tag:
    with assert_raises(ClientError) as ce:
        conn.tag_role(RoleName='my-role', Tags=[{'Key': '0', 'Value': ''}, {'Key': '0', 'Value': ''}])
    assert 'Duplicate tag keys found. Please note that Tag keys are case insensitive.' \
           in ce.exception.response['Error']['Message']

    # Duplicate tag with different casing:
    with assert_raises(ClientError) as ce:
        conn.tag_role(RoleName='my-role', Tags=[{'Key': 'a', 'Value': ''}, {'Key': 'A', 'Value': ''}])
    assert 'Duplicate tag keys found. Please note that Tag keys are case insensitive.' \
           in ce.exception.response['Error']['Message']

    # With a really big key:
    with assert_raises(ClientError) as ce:
        conn.tag_role(RoleName='my-role', Tags=[{'Key': '0' * 129, 'Value': ''}])
    assert 'Member must have length less than or equal to 128.' in ce.exception.response['Error']['Message']

    # With a really big value:
    with assert_raises(ClientError) as ce:
        conn.tag_role(RoleName='my-role', Tags=[{'Key': '0', 'Value': '0' * 257}])
    assert 'Member must have length less than or equal to 256.' in ce.exception.response['Error']['Message']

    # With an invalid character:
    with assert_raises(ClientError) as ce:
        conn.tag_role(RoleName='my-role', Tags=[{'Key': 'NOWAY!', 'Value': ''}])
    assert 'Member must satisfy regular expression pattern: [\\p{L}\\p{Z}\\p{N}_.:/=+\\-@]+' \
           in ce.exception.response['Error']['Message']

    # With a role that doesn't exist:
    with assert_raises(ClientError):
        conn.tag_role(RoleName='notarole', Tags=[{'Key': 'some', 'Value': 'value'}])


@mock_iam
def test_untag_role():
    conn = boto3.client('iam', region_name='us-east-1')
    conn.create_role(RoleName="my-role", AssumeRolePolicyDocument="{}")

    # With proper tag values:
    conn.tag_role(RoleName='my-role', Tags=[
        {
            'Key': 'somekey',
            'Value': 'somevalue'
        },
        {
            'Key': 'someotherkey',
            'Value': 'someothervalue'
        }
    ])

    # Remove them:
    conn.untag_role(RoleName='my-role', TagKeys=['somekey'])
    tags = conn.list_role_tags(RoleName='my-role')
    assert len(tags['Tags']) == 1
    assert tags['Tags'][0]['Key'] == 'someotherkey'
    assert tags['Tags'][0]['Value'] == 'someothervalue'

    # And again:
    conn.untag_role(RoleName='my-role', TagKeys=['someotherkey'])
    tags = conn.list_role_tags(RoleName='my-role')
    assert not tags['Tags']

    # Test removing tags with invalid values:
    # With more than 50 tags:
    with assert_raises(ClientError) as ce:
        conn.untag_role(RoleName='my-role', TagKeys=[str(x) for x in range(0, 51)])
    assert 'failed to satisfy constraint: Member must have length less than or equal to 50.' \
           in ce.exception.response['Error']['Message']
    assert 'tagKeys' in ce.exception.response['Error']['Message']

    # With a really big key:
    with assert_raises(ClientError) as ce:
        conn.untag_role(RoleName='my-role', TagKeys=['0' * 129])
    assert 'Member must have length less than or equal to 128.' in ce.exception.response['Error']['Message']
    assert 'tagKeys' in ce.exception.response['Error']['Message']

    # With an invalid character:
    with assert_raises(ClientError) as ce:
        conn.untag_role(RoleName='my-role', TagKeys=['NOWAY!'])
    assert 'Member must satisfy regular expression pattern: [\\p{L}\\p{Z}\\p{N}_.:/=+\\-@]+' \
           in ce.exception.response['Error']['Message']
    assert 'tagKeys' in ce.exception.response['Error']['Message']

    # With a role that doesn't exist:
    with assert_raises(ClientError):
        conn.untag_role(RoleName='notarole', TagKeys=['somevalue'])


@mock_iam()
def test_update_role_description():
    conn = boto3.client('iam', region_name='us-east-1')

    with assert_raises(ClientError):
        conn.delete_role(RoleName="my-role")

    conn.create_role(RoleName="my-role", AssumeRolePolicyDocument="some policy", Path="/my-path/")
    response = conn.update_role_description(RoleName="my-role", Description="test")

    assert response['Role']['RoleName'] == 'my-role'

@mock_iam()
def test_update_role():
    conn = boto3.client('iam', region_name='us-east-1')

    with assert_raises(ClientError):
        conn.delete_role(RoleName="my-role")

    conn.create_role(RoleName="my-role", AssumeRolePolicyDocument="some policy", Path="/my-path/")
    response = conn.update_role_description(RoleName="my-role", Description="test")
    assert response['Role']['RoleName'] == 'my-role'

@mock_iam()
def test_update_role():
    conn = boto3.client('iam', region_name='us-east-1')

    with assert_raises(ClientError):
        conn.delete_role(RoleName="my-role")

    conn.create_role(RoleName="my-role", AssumeRolePolicyDocument="some policy", Path="/my-path/")
    response = conn.update_role(RoleName="my-role", Description="test")
    assert len(response.keys()) == 1


@mock_iam()
def test_list_entities_for_policy():
    test_policy = json.dumps({
        "Version": "2012-10-17",
        "Statement": [
            {
                "Action": "s3:ListBucket",
                "Resource": "*",
                "Effect": "Allow",
            }
        ]
    })

    conn = boto3.client('iam', region_name='us-east-1')
    conn.create_role(RoleName="my-role", AssumeRolePolicyDocument="some policy", Path="/my-path/")
    conn.create_user(Path='/', UserName='testUser')
    conn.create_group(Path='/', GroupName='testGroup')
    conn.create_policy(
        PolicyName='testPolicy',
        Path='/',
        PolicyDocument=test_policy,
        Description='Test Policy'
    )

    # Attach things to the user and group:
    conn.put_user_policy(UserName='testUser', PolicyName='testPolicy', PolicyDocument=test_policy)
    conn.put_group_policy(GroupName='testGroup', PolicyName='testPolicy', PolicyDocument=test_policy)

    conn.attach_user_policy(UserName='testUser', PolicyArn='arn:aws:iam::123456789012:policy/testPolicy')
    conn.attach_group_policy(GroupName='testGroup', PolicyArn='arn:aws:iam::123456789012:policy/testPolicy')

    conn.add_user_to_group(UserName='testUser', GroupName='testGroup')

    # Add things to the role:
    conn.create_instance_profile(InstanceProfileName='ipn')
    conn.add_role_to_instance_profile(InstanceProfileName='ipn', RoleName='my-role')
    conn.tag_role(RoleName='my-role', Tags=[
        {
            'Key': 'somekey',
            'Value': 'somevalue'
        },
        {
            'Key': 'someotherkey',
            'Value': 'someothervalue'
        }
    ])
    conn.put_role_policy(RoleName='my-role', PolicyName='test-policy', PolicyDocument=test_policy)
    conn.attach_role_policy(RoleName='my-role', PolicyArn='arn:aws:iam::123456789012:policy/testPolicy')

    response = conn.list_entities_for_policy(
        PolicyArn='arn:aws:iam::123456789012:policy/testPolicy',
        EntityFilter='Role'
    )
    assert response['PolicyRoles'] == [{'RoleName': 'my-role'}]

    response = conn.list_entities_for_policy(
        PolicyArn='arn:aws:iam::123456789012:policy/testPolicy',
        EntityFilter='User',
    )
    assert response['PolicyUsers'] ==  [{'UserName': 'testUser'}]

    response = conn.list_entities_for_policy(
        PolicyArn='arn:aws:iam::123456789012:policy/testPolicy',
        EntityFilter='Group',
    )
    assert response['PolicyGroups'] == [{'GroupName': 'testGroup'}]

    response = conn.list_entities_for_policy(
        PolicyArn='arn:aws:iam::123456789012:policy/testPolicy',
        EntityFilter='LocalManagedPolicy',
    )
    assert response['PolicyGroups'] == [{'GroupName': 'testGroup'}]
    assert response['PolicyUsers'] ==  [{'UserName': 'testUser'}]
    assert response['PolicyRoles'] == [{'RoleName': 'my-role'}]


@mock_iam()
def test_create_role_no_path():
    conn = boto3.client('iam', region_name='us-east-1')
    resp = conn.create_role(RoleName='my-role', AssumeRolePolicyDocument='some policy', Description='test')
    resp.get('Role').get('Arn').should.equal('arn:aws:iam::123456789012:role/my-role')
    resp.get('Role').should_not.have.key('PermissionsBoundary')

@mock_iam()
def test_create_role_with_permissions_boundary():
    conn = boto3.client('iam', region_name='us-east-1')
    boundary = 'arn:aws:iam::123456789012:policy/boundary'
    resp = conn.create_role(RoleName='my-role', AssumeRolePolicyDocument='some policy', Description='test', PermissionsBoundary=boundary)
    expected = {
        'PermissionsBoundaryType': 'PermissionsBoundaryPolicy',
        'PermissionsBoundaryArn': boundary
    }
    resp.get('Role').get('PermissionsBoundary').should.equal(expected)

    invalid_boundary_arn = 'arn:aws:iam::123456789:not_a_boundary'
    with assert_raises(ClientError):
        conn.create_role(RoleName='bad-boundary', AssumeRolePolicyDocument='some policy', Description='test',  PermissionsBoundary=invalid_boundary_arn)

    # Ensure the PermissionsBoundary is included in role listing as well
    conn.list_roles().get('Roles')[0].get('PermissionsBoundary').should.equal(expected)
