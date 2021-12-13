from __future__ import unicode_literals

import boto3
from sure import this

from . import mock_rds


@mock_rds
def test_describe_db_log_files():
    client = boto3.client("rds", region_name="us-west-2")
    client.create_db_instance(
        DBInstanceIdentifier="test-instance",
        AllocatedStorage=10,
        Engine="postgres",
        DBName="test-db",
        DBInstanceClass="db.m4.large",
        MasterUsername="root",
        MasterUserPassword="password",
    )
    logs = client.describe_db_log_files(DBInstanceIdentifier="test-instance",).get(
        "DescribeDBLogFiles"
    )
    this(len(logs)).should.be.greater_than(0)
    logs[0]["LogFileName"].should.match("error/postgresql.log")
