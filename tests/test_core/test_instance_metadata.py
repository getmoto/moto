from __future__ import unicode_literals
import sure  # noqa
from nose.tools import assert_raises
import requests

from moto import mock_ec2


@mock_ec2
def test_latest_meta_data():
    res = requests.get("http://169.254.169.254/latest/meta-data/")
    res.content.should.equal(b"iam")


@mock_ec2
def test_meta_data_iam():
    res = requests.get("http://169.254.169.254/latest/meta-data/iam")
    json_response = res.json()
    default_role = json_response['security-credentials']['default-role']
    default_role.should.contain('AccessKeyId')
    default_role.should.contain('SecretAccessKey')
    default_role.should.contain('Token')
    default_role.should.contain('Expiration')


@mock_ec2
def test_meta_data_security_credentials():
    res = requests.get("http://169.254.169.254/latest/meta-data/iam/security-credentials/")
    res.content.should.equal(b"default-role")


@mock_ec2
def test_meta_data_default_role():
    res = requests.get("http://169.254.169.254/latest/meta-data/iam/security-credentials/default-role")
    json_response = res.json()
    json_response.should.contain('AccessKeyId')
    json_response.should.contain('SecretAccessKey')
    json_response.should.contain('Token')
    json_response.should.contain('Expiration')


@mock_ec2
def test_meta_data_unknown_path():
    with assert_raises(NotImplementedError):
        requests.get("http://169.254.169.254/latest/meta-data/badpath")
