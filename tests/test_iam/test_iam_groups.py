from __future__ import unicode_literals
import boto
import sure  # noqa

from nose.tools import assert_raises
from boto.exception import BotoServerError
from moto import mock_iam


@mock_iam()
def test_create_group():
    conn = boto.connect_iam()
    conn.create_group('my-group')
    with assert_raises(BotoServerError):
        conn.create_group('my-group')


@mock_iam()
def test_get_group():
    conn = boto.connect_iam()
    conn.create_group('my-group')
    conn.get_group('my-group')
    with assert_raises(BotoServerError):
        conn.get_group('not-group')


@mock_iam()
def test_get_all_groups():
    conn = boto.connect_iam()
    conn.create_group('my-group1')
    conn.create_group('my-group2')
    groups = conn.get_all_groups()['list_groups_response']['list_groups_result']['groups']
    groups.should.have.length_of(2)


@mock_iam()
def test_add_user_to_group():
    conn = boto.connect_iam()
    with assert_raises(BotoServerError):
        conn.add_user_to_group('my-group', 'my-user')
    conn.create_group('my-group')
    with assert_raises(BotoServerError):
        conn.add_user_to_group('my-group', 'my-user')
    conn.create_user('my-user')
    conn.add_user_to_group('my-group', 'my-user')


@mock_iam()
def test_remove_user_from_group():
    conn = boto.connect_iam()
    with assert_raises(BotoServerError):
        conn.remove_user_from_group('my-group', 'my-user')
    conn.create_group('my-group')
    conn.create_user('my-user')
    with assert_raises(BotoServerError):
        conn.remove_user_from_group('my-group', 'my-user')
    conn.add_user_to_group('my-group', 'my-user')
    conn.remove_user_from_group('my-group', 'my-user')


@mock_iam()
def test_get_groups_for_user():
    conn = boto.connect_iam()
    conn.create_group('my-group1')
    conn.create_group('my-group2')
    conn.create_group('other-group')
    conn.create_user('my-user')
    conn.add_user_to_group('my-group1', 'my-user')
    conn.add_user_to_group('my-group2', 'my-user')

    groups = conn.get_groups_for_user('my-user')['list_groups_for_user_response']['list_groups_for_user_result']['groups']
    groups.should.have.length_of(2)
