import boto3
from moto import mock_neptune


@mock_neptune
def test_db_cluster_options():
    # Verified against AWS on 23-02-2023
    # We're not checking the exact data here, that is already done in TF
    client = boto3.client("neptune", region_name="us-east-1")
    response = client.describe_orderable_db_instance_options(Engine="neptune")
    assert len(response["OrderableDBInstanceOptions"]) == 286

    response = client.describe_orderable_db_instance_options(
        Engine="neptune", EngineVersion="1.0.2.1"
    )
    assert len(response["OrderableDBInstanceOptions"]) == 0

    response = client.describe_orderable_db_instance_options(
        Engine="neptune", EngineVersion="1.0.3.0"
    )
    assert len(response["OrderableDBInstanceOptions"]) == 12
