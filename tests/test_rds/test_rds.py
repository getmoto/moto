import boto3
import sure  # noqa # pylint: disable=unused-import

from moto import mock_rds


@mock_rds
def test_get_databases_paginated():
    conn = boto3.client("rds", region_name="us-west-2")

    for i in range(51):
        conn.create_db_instance(
            AllocatedStorage=5,
            Port=5432,
            DBInstanceIdentifier="rds%d" % i,
            DBInstanceClass="db.t1.micro",
            Engine="postgres",
        )

    resp = conn.describe_db_instances()
    resp["DBInstances"].should.have.length_of(50)
    resp["Marker"].should.equal(resp["DBInstances"][-1]["DBInstanceIdentifier"])

    resp2 = conn.describe_db_instances(Marker=resp["Marker"])
    resp2["DBInstances"].should.have.length_of(1)
