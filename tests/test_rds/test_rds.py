from __future__ import unicode_literals

import boto.rds
from boto.exception import BotoServerError
import sure  # noqa

from moto import mock_rds


@mock_rds
def test_create_database():
    conn = boto.rds.connect_to_region("us-west-2")

    database = conn.create_dbinstance("db-master-1", 10, 'db.m1.small', 'root', 'hunter2')

    database.status.should.equal('available')
    database.id.should.equal("db-master-1")
    database.allocated_storage.should.equal(10)
    database.instance_class.should.equal("db.m1.small")
    database.master_username.should.equal("root")
    database.endpoint.should.equal(('db-master-1.aaaaaaaaaa.us-west-2.rds.amazonaws.com', 3306))


@mock_rds
def test_get_databases():
    conn = boto.rds.connect_to_region("us-west-2")

    list(conn.get_all_dbinstances()).should.have.length_of(0)

    conn.create_dbinstance("db-master-1", 10, 'db.m1.small', 'root', 'hunter2')
    conn.create_dbinstance("db-master-2", 10, 'db.m1.small', 'root', 'hunter2')

    list(conn.get_all_dbinstances()).should.have.length_of(2)

    databases = conn.get_all_dbinstances("db-master-1")
    list(databases).should.have.length_of(1)

    databases[0].id.should.equal("db-master-1")


@mock_rds
def test_describe_non_existant_database():
    conn = boto.rds.connect_to_region("us-west-2")
    conn.get_all_dbinstances.when.called_with("not-a-db").should.throw(BotoServerError)


@mock_rds
def test_delete_database():
    conn = boto.rds.connect_to_region("us-west-2")
    list(conn.get_all_dbinstances()).should.have.length_of(0)

    conn.create_dbinstance("db-master-1", 10, 'db.m1.small', 'root', 'hunter2')
    list(conn.get_all_dbinstances()).should.have.length_of(1)

    conn.delete_dbinstance("db-master-1")
    list(conn.get_all_dbinstances()).should.have.length_of(0)


@mock_rds
def test_delete_non_existant_database():
    conn = boto.rds.connect_to_region("us-west-2")
    conn.delete_dbinstance.when.called_with("not-a-db").should.throw(BotoServerError)
