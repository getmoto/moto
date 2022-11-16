import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import
from botocore.exceptions import ClientError

from moto import mock_rds


class TestDBInstanceFilters(object):

    mock = mock_rds()

    @classmethod
    def setup_class(cls):
        cls.mock.start()
        client = boto3.client("rds", region_name="us-west-2")
        for i in range(10):
            instance_identifier = f"db-instance-{i}"
            cluster_identifier = f"db-cluster-{i}"
            engine = "postgres" if (i % 3) else "mysql"
            client.create_db_instance(
                DBInstanceIdentifier=instance_identifier,
                DBClusterIdentifier=cluster_identifier,
                Engine=engine,
                DBInstanceClass="db.m1.small",
            )
        cls.client = client

    @classmethod
    def teardown_class(cls):
        try:
            cls.mock.stop()
        except RuntimeError:
            pass

    def test_invalid_filter_name_raises_error(self):
        with pytest.raises(ClientError) as ex:
            self.client.describe_db_instances(
                Filters=[{"Name": "invalid-filter-name", "Values": []}]
            )
        ex.value.response["Error"]["Code"].should.equal("InvalidParameterValue")
        ex.value.response["Error"]["Message"].should.equal(
            "Unrecognized filter name: invalid-filter-name"
        )

    def test_empty_filter_values_raises_error(self):
        with pytest.raises(ClientError) as ex:
            self.client.describe_db_instances(
                Filters=[{"Name": "db-instance-id", "Values": []}]
            )
        ex.value.response["Error"]["Code"].should.equal("InvalidParameterCombination")
        ex.value.response["Error"]["Message"].should.contain("must not be empty")

    def test_db_cluster_id_filter(self):
        resp = self.client.describe_db_instances()
        db_cluster_identifier = resp["DBInstances"][0]["DBClusterIdentifier"]

        db_instances = self.client.describe_db_instances(
            Filters=[{"Name": "db-cluster-id", "Values": [db_cluster_identifier]}]
        ).get("DBInstances")
        db_instances.should.have.length_of(1)
        db_instances[0]["DBClusterIdentifier"].should.equal(db_cluster_identifier)

    def test_db_instance_id_filter(self):
        resp = self.client.describe_db_instances()
        db_instance_identifier = resp["DBInstances"][0]["DBInstanceIdentifier"]

        db_instances = self.client.describe_db_instances(
            Filters=[{"Name": "db-instance-id", "Values": [db_instance_identifier]}]
        ).get("DBInstances")
        db_instances.should.have.length_of(1)
        db_instances[0]["DBInstanceIdentifier"].should.equal(db_instance_identifier)

    def test_db_instance_id_filter_works_with_arns(self):
        resp = self.client.describe_db_instances()
        db_instance_arn = resp["DBInstances"][0]["DBInstanceArn"]

        db_instances = self.client.describe_db_instances(
            Filters=[{"Name": "db-instance-id", "Values": [db_instance_arn]}]
        ).get("DBInstances")
        db_instances.should.have.length_of(1)
        db_instances[0]["DBInstanceArn"].should.equal(db_instance_arn)

    def test_dbi_resource_id_filter(self):
        resp = self.client.describe_db_instances()
        dbi_resource_identifier = resp["DBInstances"][0]["DbiResourceId"]

        db_instances = self.client.describe_db_instances(
            Filters=[{"Name": "dbi-resource-id", "Values": [dbi_resource_identifier]}]
        ).get("DBInstances")
        for db_instance in db_instances:
            db_instance["DbiResourceId"].should.equal(dbi_resource_identifier)

    def test_engine_filter(self):
        db_instances = self.client.describe_db_instances(
            Filters=[{"Name": "engine", "Values": ["postgres"]}]
        ).get("DBInstances")
        for db_instance in db_instances:
            db_instance["Engine"].should.equal("postgres")

        db_instances = self.client.describe_db_instances(
            Filters=[{"Name": "engine", "Values": ["oracle"]}]
        ).get("DBInstances")
        db_instances.should.have.length_of(0)

    def test_multiple_filters(self):
        resp = self.client.describe_db_instances(
            Filters=[
                {
                    "Name": "db-instance-id",
                    "Values": ["db-instance-0", "db-instance-1", "db-instance-3"],
                },
                {"Name": "engine", "Values": ["mysql", "oracle"]},
            ]
        )
        returned_identifiers = [
            db["DBInstanceIdentifier"] for db in resp["DBInstances"]
        ]
        returned_identifiers.should.have.length_of(2)
        "db-instance-0".should.be.within(returned_identifiers)
        "db-instance-3".should.be.within(returned_identifiers)

    def test_invalid_db_instance_identifier_with_exclusive_filter(self):
        # Passing a non-existent DBInstanceIdentifier will not raise an error
        # if the resulting filter matches other resources.
        resp = self.client.describe_db_instances(
            DBInstanceIdentifier="non-existent",
            Filters=[{"Name": "db-instance-id", "Values": ["db-instance-1"]}],
        )
        resp["DBInstances"].should.have.length_of(1)
        resp["DBInstances"][0]["DBInstanceIdentifier"].should.equal("db-instance-1")

    def test_invalid_db_instance_identifier_with_non_matching_filter(self):
        # Passing a non-existent DBInstanceIdentifier will raise an error if
        # the resulting filter does not match any resources.
        with pytest.raises(ClientError) as ex:
            self.client.describe_db_instances(
                DBInstanceIdentifier="non-existent",
                Filters=[{"Name": "engine", "Values": ["mysql"]}],
            )
        ex.value.response["Error"]["Code"].should.equal("DBInstanceNotFound")
        ex.value.response["Error"]["Message"].should.equal(
            "DBInstance non-existent not found."
        )

    def test_valid_db_instance_identifier_with_exclusive_filter(self):
        # Passing a valid DBInstanceIdentifier with a filter it does not match
        # but does match other resources will return those other resources.
        resp = self.client.describe_db_instances(
            DBInstanceIdentifier="db-instance-0",
            Filters=[
                {"Name": "db-instance-id", "Values": ["db-instance-1"]},
                {"Name": "engine", "Values": ["postgres"]},
            ],
        )
        returned_identifiers = [
            db["DBInstanceIdentifier"] for db in resp["DBInstances"]
        ]
        "db-instance-0".should_not.be.within(returned_identifiers)
        "db-instance-1".should.be.within(returned_identifiers)

    def test_valid_db_instance_identifier_with_inclusive_filter(self):
        # Passing a valid DBInstanceIdentifier with a filter it matches but also
        # matches other resources will return all matching resources.
        resp = self.client.describe_db_instances(
            DBInstanceIdentifier="db-instance-0",
            Filters=[
                {"Name": "db-instance-id", "Values": ["db-instance-1"]},
                {"Name": "engine", "Values": ["mysql", "postgres"]},
            ],
        )
        returned_identifiers = [
            db["DBInstanceIdentifier"] for db in resp["DBInstances"]
        ]
        "db-instance-0".should.be.within(returned_identifiers)
        "db-instance-1".should.be.within(returned_identifiers)

    def test_valid_db_instance_identifier_with_non_matching_filter(self):
        # Passing a valid DBInstanceIdentifier will raise an error if the
        # resulting filter does not match any resources.
        with pytest.raises(ClientError) as ex:
            self.client.describe_db_instances(
                DBInstanceIdentifier="db-instance-0",
                Filters=[{"Name": "engine", "Values": ["postgres"]}],
            )
        ex.value.response["Error"]["Code"].should.equal("DBInstanceNotFound")
        ex.value.response["Error"]["Message"].should.equal(
            "DBInstance db-instance-0 not found."
        )


class TestDBSnapshotFilters(object):

    mock = mock_rds()

    @classmethod
    def setup_class(cls):
        cls.mock.start()
        client = boto3.client("rds", region_name="us-west-2")
        # We'll set up two instances (one postgres, one mysql)
        # with two snapshots each.
        for i in range(2):
            identifier = f"db-instance-{i}"
            engine = "postgres" if i else "mysql"
            client.create_db_instance(
                DBInstanceIdentifier=identifier,
                Engine=engine,
                DBInstanceClass="db.m1.small",
            )
            for j in range(2):
                client.create_db_snapshot(
                    DBInstanceIdentifier=identifier,
                    DBSnapshotIdentifier=f"{identifier}-snapshot-{j}",
                )
        cls.client = client

    @classmethod
    def teardown_class(cls):
        try:
            cls.mock.stop()
        except RuntimeError:
            pass

    def test_invalid_filter_name_raises_error(self):
        with pytest.raises(ClientError) as ex:
            self.client.describe_db_snapshots(
                Filters=[{"Name": "invalid-filter-name", "Values": []}]
            )
        ex.value.response["Error"]["Code"].should.equal("InvalidParameterValue")
        ex.value.response["Error"]["Message"].should.equal(
            "Unrecognized filter name: invalid-filter-name"
        )

    def test_empty_filter_values_raises_error(self):
        with pytest.raises(ClientError) as ex:
            self.client.describe_db_snapshots(
                Filters=[{"Name": "db-snapshot-id", "Values": []}]
            )
        ex.value.response["Error"]["Code"].should.equal("InvalidParameterCombination")
        ex.value.response["Error"]["Message"].should.contain("must not be empty")

    def test_db_snapshot_id_filter(self):
        snapshots = self.client.describe_db_snapshots(
            Filters=[{"Name": "db-snapshot-id", "Values": ["db-instance-1-snapshot-0"]}]
        ).get("DBSnapshots")
        snapshots.should.have.length_of(1)
        snapshots[0]["DBSnapshotIdentifier"].should.equal("db-instance-1-snapshot-0")

    def test_db_instance_id_filter(self):
        resp = self.client.describe_db_instances()
        db_instance_identifier = resp["DBInstances"][0]["DBInstanceIdentifier"]

        snapshots = self.client.describe_db_snapshots(
            Filters=[{"Name": "db-instance-id", "Values": [db_instance_identifier]}]
        ).get("DBSnapshots")
        for snapshot in snapshots:
            snapshot["DBInstanceIdentifier"].should.equal(db_instance_identifier)

    def test_db_instance_id_filter_works_with_arns(self):
        resp = self.client.describe_db_instances()
        db_instance_identifier = resp["DBInstances"][0]["DBInstanceIdentifier"]
        db_instance_arn = resp["DBInstances"][0]["DBInstanceArn"]

        snapshots = self.client.describe_db_snapshots(
            Filters=[{"Name": "db-instance-id", "Values": [db_instance_arn]}]
        ).get("DBSnapshots")
        for snapshot in snapshots:
            snapshot["DBInstanceIdentifier"].should.equal(db_instance_identifier)

    def test_dbi_resource_id_filter(self):
        resp = self.client.describe_db_instances()
        dbi_resource_identifier = resp["DBInstances"][0]["DbiResourceId"]

        snapshots = self.client.describe_db_snapshots(
            Filters=[{"Name": "dbi-resource-id", "Values": [dbi_resource_identifier]}]
        ).get("DBSnapshots")
        for snapshot in snapshots:
            snapshot["DbiResourceId"].should.equal(dbi_resource_identifier)

    def test_engine_filter(self):
        snapshots = self.client.describe_db_snapshots(
            Filters=[{"Name": "engine", "Values": ["postgres"]}]
        ).get("DBSnapshots")
        for snapshot in snapshots:
            snapshot["Engine"].should.equal("postgres")

        snapshots = self.client.describe_db_snapshots(
            Filters=[{"Name": "engine", "Values": ["oracle"]}]
        ).get("DBSnapshots")
        snapshots.should.have.length_of(0)

    def test_multiple_filters(self):
        snapshots = self.client.describe_db_snapshots(
            Filters=[
                {"Name": "db-snapshot-id", "Values": ["db-instance-0-snapshot-1"]},
                {
                    "Name": "db-instance-id",
                    "Values": ["db-instance-1", "db-instance-0"],
                },
                {"Name": "engine", "Values": ["mysql"]},
            ]
        ).get("DBSnapshots")
        snapshots.should.have.length_of(1)
        snapshots[0]["DBSnapshotIdentifier"].should.equal("db-instance-0-snapshot-1")

    def test_invalid_snapshot_id_with_db_instance_id_and_filter(self):
        # Passing a non-existent DBSnapshotIdentifier will return an empty list
        # if DBInstanceIdentifier is also passed in.
        resp = self.client.describe_db_snapshots(
            DBSnapshotIdentifier="non-existent",
            DBInstanceIdentifier="a-db-instance-identifier",
            Filters=[{"Name": "db-instance-id", "Values": ["db-instance-1"]}],
        )
        resp["DBSnapshots"].should.have.length_of(0)

    def test_invalid_snapshot_id_with_non_matching_filter(self):
        # Passing a non-existent DBSnapshotIdentifier will raise an error if
        # the resulting filter does not match any resources.
        with pytest.raises(ClientError) as ex:
            self.client.describe_db_snapshots(
                DBSnapshotIdentifier="non-existent",
                Filters=[{"Name": "engine", "Values": ["oracle"]}],
            )
        ex.value.response["Error"]["Code"].should.equal("DBSnapshotNotFound")
        ex.value.response["Error"]["Message"].should.equal(
            "DBSnapshot non-existent not found."
        )

    def test_valid_snapshot_id_with_exclusive_filter(self):
        # Passing a valid DBSnapshotIdentifier with a filter it does not match
        # but does match other resources will return those other resources.
        resp = self.client.describe_db_snapshots(
            DBSnapshotIdentifier="db-instance-0-snapshot-0",
            Filters=[
                {"Name": "db-snapshot-id", "Values": ["db-instance-1-snapshot-1"]},
                {"Name": "db-instance-id", "Values": ["db-instance-1"]},
                {"Name": "engine", "Values": ["postgres"]},
            ],
        )
        resp["DBSnapshots"].should.have.length_of(1)
        resp["DBSnapshots"][0]["DBSnapshotIdentifier"].should.equal(
            "db-instance-1-snapshot-1"
        )

    def test_valid_snapshot_id_with_inclusive_filter(self):
        # Passing a valid DBSnapshotIdentifier with a filter it matches but also
        # matches other resources will return all matching resources.
        snapshots = self.client.describe_db_snapshots(
            DBSnapshotIdentifier="db-instance-0-snapshot-0",
            Filters=[
                {"Name": "db-snapshot-id", "Values": ["db-instance-1-snapshot-1"]},
                {
                    "Name": "db-instance-id",
                    "Values": ["db-instance-1", "db-instance-0"],
                },
                {"Name": "engine", "Values": ["mysql", "postgres"]},
            ],
        ).get("DBSnapshots")
        returned_identifiers = [ss["DBSnapshotIdentifier"] for ss in snapshots]
        returned_identifiers.should.have.length_of(2)
        "db-instance-0-snapshot-0".should.be.within(returned_identifiers)
        "db-instance-1-snapshot-1".should.be.within(returned_identifiers)

    def test_valid_snapshot_id_with_non_matching_filter(self):
        # Passing a valid DBSnapshotIdentifier will raise an error if the
        # resulting filter does not match any resources.
        with pytest.raises(ClientError) as ex:
            self.client.describe_db_snapshots(
                DBSnapshotIdentifier="db-instance-0-snapshot-0",
                Filters=[{"Name": "engine", "Values": ["postgres"]}],
            )
        ex.value.response["Error"]["Code"].should.equal("DBSnapshotNotFound")
        ex.value.response["Error"]["Message"].should.equal(
            "DBSnapshot db-instance-0-snapshot-0 not found."
        )
