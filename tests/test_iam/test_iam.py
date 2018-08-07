from __future__ import unicode_literals
import base64

import boto
import boto3
import sure  # noqa
from boto.exception import BotoServerError
from botocore.exceptions import ClientError
from moto import mock_iam, mock_iam_deprecated
from moto.iam.models import aws_managed_policies
from nose.tools import assert_raises, assert_equals
from nose.tools import raises

from tests.helpers import requires_boto_gte


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
    conn.put_role_policy("my-role", "test policy", "my policy")
    role = conn.list_role_policies("my-role")
    role.policy_names.should.have.length_of(1)
    role.policy_names[0].should.equal("test policy")

    conn.put_role_policy("my-role", "test policy 2", "another policy")
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
    conn.put_role_policy("my-role", "test policy", "my policy")
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
        PolicyDocument='{"some":"policy"}')
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
        PolicyDocument='{"some":"policy"}')
    version = conn.create_policy_version(
        PolicyArn="arn:aws:iam::123456789012:policy/TestCreatePolicyVersion",
        PolicyDocument='{"some":"policy"}')
    version.get('PolicyVersion').get('Document').should.equal({'some': 'policy'})


@mock_iam
def test_get_policy_version():
    conn = boto3.client('iam', region_name='us-east-1')
    conn.create_policy(
        PolicyName="TestGetPolicyVersion",
        PolicyDocument='{"some":"policy"}')
    version = conn.create_policy_version(
        PolicyArn="arn:aws:iam::123456789012:policy/TestGetPolicyVersion",
        PolicyDocument='{"some":"policy"}')
    with assert_raises(ClientError):
        conn.get_policy_version(
            PolicyArn="arn:aws:iam::123456789012:policy/TestGetPolicyVersion",
            VersionId='v2-does-not-exist')
    retrieved = conn.get_policy_version(
        PolicyArn="arn:aws:iam::123456789012:policy/TestGetPolicyVersion",
        VersionId=version.get('PolicyVersion').get('VersionId'))
    retrieved.get('PolicyVersion').get('Document').should.equal({'some': 'policy'})


@mock_iam
def test_list_policy_versions():
    conn = boto3.client('iam', region_name='us-east-1')
    with assert_raises(ClientError):
        versions = conn.list_policy_versions(
            PolicyArn="arn:aws:iam::123456789012:policy/TestListPolicyVersions")
    conn.create_policy(
        PolicyName="TestListPolicyVersions",
        PolicyDocument='{"some":"policy"}')
    conn.create_policy_version(
        PolicyArn="arn:aws:iam::123456789012:policy/TestListPolicyVersions",
        PolicyDocument='{"first":"policy"}')
    conn.create_policy_version(
        PolicyArn="arn:aws:iam::123456789012:policy/TestListPolicyVersions",
        PolicyDocument='{"second":"policy"}')
    versions = conn.list_policy_versions(
        PolicyArn="arn:aws:iam::123456789012:policy/TestListPolicyVersions")
    versions.get('Versions')[0].get('Document').should.equal({'first': 'policy'})
    versions.get('Versions')[1].get('Document').should.equal({'second': 'policy'})


@mock_iam
def test_delete_policy_version():
    conn = boto3.client('iam', region_name='us-east-1')
    conn.create_policy(
        PolicyName="TestDeletePolicyVersion",
        PolicyDocument='{"some":"policy"}')
    conn.create_policy_version(
        PolicyArn="arn:aws:iam::123456789012:policy/TestDeletePolicyVersion",
        PolicyDocument='{"first":"policy"}')
    with assert_raises(ClientError):
        conn.delete_policy_version(
            PolicyArn="arn:aws:iam::123456789012:policy/TestDeletePolicyVersion",
            VersionId='v2-nope-this-does-not-exist')
    conn.delete_policy_version(
        PolicyArn="arn:aws:iam::123456789012:policy/TestDeletePolicyVersion",
        VersionId='v1')
    versions = conn.list_policy_versions(
        PolicyArn="arn:aws:iam::123456789012:policy/TestDeletePolicyVersion")
    len(versions.get('Versions')).should.equal(0)


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
    policy_document = "{'mypolicy': 'test'}"
    user_name = 'my-user'
    conn = boto3.client('iam', region_name='us-east-1')
    conn.create_user(UserName=user_name)
    conn.put_user_policy(
        UserName=user_name,
        PolicyName=policy_name,
        PolicyDocument=policy_document
    )

    policy_doc = conn.get_user_policy(
        UserName=user_name,
        PolicyName=policy_name
    )
    test = policy_document in policy_doc['PolicyDocument']
    test.should.equal(True)

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


@requires_boto_gte('2.39')
@mock_iam_deprecated()
def test_managed_policy():
    conn = boto.connect_iam()

    conn.create_policy(policy_name='UserManagedPolicy',
                       policy_document={'mypolicy': 'test'},
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
                               PolicyDocument='{"mypolicy": "test"}',
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
def test_get_account_authorization_details():
    import json
    conn = boto3.client('iam', region_name='us-east-1')
    conn.create_role(RoleName="my-role", AssumeRolePolicyDocument="some policy", Path="/my-path/")
    conn.create_user(Path='/', UserName='testCloudAuxUser')
    conn.create_group(Path='/', GroupName='testCloudAuxGroup')
    conn.create_policy(
        PolicyName='testCloudAuxPolicy',
        Path='/',
        PolicyDocument=json.dumps({
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "s3:ListBucket",
                    "Resource": "*",
                    "Effect": "Allow",
                }
            ]
        }),
        Description='Test CloudAux Policy'
    )

    result = conn.get_account_authorization_details(Filter=['Role'])
    len(result['RoleDetailList']) == 1
    len(result['UserDetailList']) == 0
    len(result['GroupDetailList']) == 0
    len(result['Policies']) == 0

    result = conn.get_account_authorization_details(Filter=['User'])
    len(result['RoleDetailList']) == 0
    len(result['UserDetailList']) == 1
    len(result['GroupDetailList']) == 0
    len(result['Policies']) == 0

    result = conn.get_account_authorization_details(Filter=['Group'])
    len(result['RoleDetailList']) == 0
    len(result['UserDetailList']) == 0
    len(result['GroupDetailList']) == 1
    len(result['Policies']) == 0

    result = conn.get_account_authorization_details(Filter=['LocalManagedPolicy'])
    len(result['RoleDetailList']) == 0
    len(result['UserDetailList']) == 0
    len(result['GroupDetailList']) == 0
    len(result['Policies']) == 1

    # Check for greater than 1 since this should always be greater than one but might change.
    # See iam/aws_managed_policies.py
    result = conn.get_account_authorization_details(Filter=['AWSManagedPolicy'])
    len(result['RoleDetailList']) == 0
    len(result['UserDetailList']) == 0
    len(result['GroupDetailList']) == 0
    len(result['Policies']) > 1

    result = conn.get_account_authorization_details()
    len(result['RoleDetailList']) == 1
    len(result['UserDetailList']) == 1
    len(result['GroupDetailList']) == 1
    len(result['Policies']) > 1



