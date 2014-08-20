from __future__ import unicode_literals
import boto
import sure  # noqa

from nose.tools import assert_raises, assert_equals, assert_not_equals
from boto.exception import BotoServerError

from moto import mock_iam


@mock_iam()
def test_get_all_server_certs():
    conn = boto.connect_iam()

    conn.upload_server_cert("certname", "certbody", "privatekey")
    certs = conn.get_all_server_certs()['list_server_certificates_response']['list_server_certificates_result']['server_certificate_metadata_list']
    certs.should.have.length_of(1)
    cert1 = certs[0]
    cert1.server_certificate_name.should.equal("certname")
    cert1.arn.should.equal("arn:aws:iam::123456789012:server-certificate/certname")


@mock_iam()
def test_get_server_cert():
    conn = boto.connect_iam()

    conn.upload_server_cert("certname", "certbody", "privatekey")
    cert = conn.get_server_certificate("certname")
    cert.server_certificate_name.should.equal("certname")
    cert.arn.should.equal("arn:aws:iam::123456789012:server-certificate/certname")


@mock_iam()
def test_upload_server_cert():
    conn = boto.connect_iam()

    conn.upload_server_cert("certname", "certbody", "privatekey")
    cert = conn.get_server_certificate("certname")
    cert.server_certificate_name.should.equal("certname")
    cert.arn.should.equal("arn:aws:iam::123456789012:server-certificate/certname")


@mock_iam()
def test_create_role_and_instance_profile():
    conn = boto.connect_iam()
    conn.create_instance_profile("my-profile", path="my-path")
    conn.create_role("my-role", assume_role_policy_document="some policy", path="my-path")

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
    conn.list_instance_profiles().instance_profiles[0].instance_profile_name.should.equal("my-profile")


@mock_iam()
def test_create_group():
    conn = boto.connect_iam()
    conn.create_group('my-group')
    assert_raises(BotoServerError, conn.create_group, 'my-group')


@mock_iam()
def test_get_group():
    conn = boto.connect_iam()
    conn.create_group('my-group')
    conn.get_group('my-group')
    assert_raises(BotoServerError, conn.get_group, 'not-group')


@mock_iam()
def test_create_user():
    conn = boto.connect_iam()
    conn.create_user('my-user')
    assert_raises(BotoServerError, conn.create_user, 'my-user')


@mock_iam()
def test_get_user():
    conn = boto.connect_iam()
    assert_raises(BotoServerError, conn.get_user, 'my-user')
    conn.create_user('my-user')
    conn.get_user('my-user')


@mock_iam()
def test_add_user_to_group():
    conn = boto.connect_iam()
    assert_raises(BotoServerError, conn.add_user_to_group, 'my-group', 'my-user')
    conn.create_group('my-group')
    assert_raises(BotoServerError, conn.add_user_to_group, 'my-group', 'my-user')
    conn.create_user('my-user')
    conn.add_user_to_group('my-group', 'my-user')


@mock_iam()
def test_remove_user_from_group():
    conn = boto.connect_iam()
    assert_raises(BotoServerError, conn.remove_user_from_group, 'my-group', 'my-user')
    conn.create_group('my-group')
    conn.create_user('my-user')
    assert_raises(BotoServerError, conn.remove_user_from_group, 'my-group', 'my-user')
    conn.add_user_to_group('my-group', 'my-user')
    conn.remove_user_from_group('my-group', 'my-user')


@mock_iam()
def test_create_access_key():
    conn = boto.connect_iam()
    assert_raises(BotoServerError, conn.create_access_key, 'my-user')
    conn.create_user('my-user')
    conn.create_access_key('my-user')


@mock_iam()
def test_get_all_access_keys():
    conn = boto.connect_iam()
    conn.create_user('my-user')
    response = conn.get_all_access_keys('my-user')
    assert_equals(
        response['list_access_keys_response']['list_access_keys_result']['access_key_metadata'],
        []
    )
    conn.create_access_key('my-user')
    response = conn.get_all_access_keys('my-user')
    assert_not_equals(
        response['list_access_keys_response']['list_access_keys_result']['access_key_metadata'],
        []
    )


@mock_iam()
def test_delete_access_key():
    conn = boto.connect_iam()
    conn.create_user('my-user')
    access_key_id = conn.create_access_key('my-user')['create_access_key_response']['create_access_key_result']['access_key']['access_key_id']
    conn.delete_access_key(access_key_id, 'my-user')


@mock_iam()
def test_delete_user():
    conn = boto.connect_iam()
    assert_raises(BotoServerError, conn.delete_user, 'my-user')
    conn.create_user('my-user')
    conn.delete_user('my-user')
