"""Tests against the AWS SDK for Python v4: https://github.com/aws/aws-sdk-python"""

from uuid import uuid4

import pytest

from moto import mock_aws

try:
    from aws_sdk_rds import RDSClient, RDSConfig
    from aws_sdk_rds.models import DBInstanceNotFoundFault
except ImportError:  # Requires Python 3.12+
    pytest.skip("aws-sdk-rds is not installed", allow_module_level=True)


@mock_aws
def test_postgres_database_lifecycle():
    """Create a tuned Postgres database, back it up, scale it up and delete it."""
    suffix = uuid4().hex[:8]
    db_id = f"orders-db-{suffix}"
    parameter_group = f"orders-pg16-{suffix}"

    with RDSClient(config=RDSConfig.resolve(region="us-east-1")) as client:
        group = client.create_db_parameter_group(
            db_parameter_group_name=parameter_group,
            db_parameter_group_family="postgres16",
            description="Tuned settings for the orders database",
        ).db_parameter_group
        assert group.db_parameter_group_family == "postgres16"
        client.modify_db_parameter_group(
            db_parameter_group_name=parameter_group,
            parameters=[
                {
                    "parameter_name": "log_min_duration_statement",
                    "parameter_value": "500",
                    "apply_method": "immediate",
                }
            ],
        )
        parameters = client.describe_db_parameters(
            db_parameter_group_name=parameter_group, source="user"
        ).parameters
        assert [(p.parameter_name, p.parameter_value) for p in parameters] == [
            ("log_min_duration_statement", "500")
        ]

        db = client.create_db_instance(
            db_instance_identifier=db_id,
            db_instance_class="db.t3.micro",
            engine="postgres",
            engine_version="16.3",
            db_name="orders",
            master_username="app_admin",
            master_user_password="correct-horse-battery-staple",
            allocated_storage=20,
            db_parameter_group_name=parameter_group,
            backup_retention_period=7,
            tags=[{"key": "team", "value": "orders"}],
        ).db_instance
        assert db.db_instance_identifier == db_id
        assert db.engine == "postgres"

        db = client.describe_db_instances(db_instance_identifier=db_id).db_instances[0]
        assert db.db_instance_status == "available"
        assert db.endpoint.port == 5432
        assert db.db_name == "orders"
        assert [g.db_parameter_group_name for g in db.db_parameter_groups] == [
            parameter_group
        ]

        snapshot = client.create_db_snapshot(
            db_instance_identifier=db_id,
            db_snapshot_identifier=f"{db_id}-before-upgrade",
        ).db_snapshot
        assert snapshot.db_instance_identifier == db_id
        assert snapshot.engine == "postgres"

        modified = client.modify_db_instance(
            db_instance_identifier=db_id,
            db_instance_class="db.t3.medium",
            apply_immediately=True,
        ).db_instance
        assert modified.db_instance_class == "db.t3.medium"

        tags = client.list_tags_for_resource(resource_name=db.db_instance_arn).tag_list
        assert [(t.key, t.value) for t in tags] == [("team", "orders")]

        client.delete_db_instance(
            db_instance_identifier=db_id,
            final_db_snapshot_identifier=f"{db_id}-final",
        )
        snapshots = client.describe_db_snapshots(
            db_instance_identifier=db_id
        ).db_snapshots
        assert sorted(s.db_snapshot_identifier for s in snapshots) == [
            f"{db_id}-before-upgrade",
            f"{db_id}-final",
        ]

        with pytest.raises(DBInstanceNotFoundFault):
            client.describe_db_instances(db_instance_identifier=db_id)
