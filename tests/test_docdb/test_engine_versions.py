import boto3

from moto import mock_aws


@mock_aws
def test_describe_db_engine_versions():
    client = boto3.client("docdb", region_name="us-east-1")
    versions = client.describe_db_engine_versions(Engine="docdb")["DBEngineVersions"]
    assert [v["EngineVersion"] for v in versions] == ["3.6.0", "4.0.0", "5.0.0"]
    for version in versions:
        assert version["Engine"] == "docdb"
        assert version["DBParameterGroupFamily"].startswith("docdb")
        assert version["SupportsLogExportsToCloudwatchLogs"] is True
        assert version["ExportableLogTypes"] == ["audit", "profiler"]

    upgrades = versions[0]["ValidUpgradeTarget"]
    assert [u["EngineVersion"] for u in upgrades] == ["4.0.0", "5.0.0"]
    assert upgrades[0]["IsMajorVersionUpgrade"] is True


@mock_aws
def test_describe_db_engine_versions__filters():
    client = boto3.client("docdb", region_name="us-east-1")

    versions = client.describe_db_engine_versions(
        Engine="docdb", EngineVersion="4.0.0"
    )["DBEngineVersions"]
    assert [v["EngineVersion"] for v in versions] == ["4.0.0"]

    versions = client.describe_db_engine_versions(DBParameterGroupFamily="docdb5.0")[
        "DBEngineVersions"
    ]
    assert [v["EngineVersion"] for v in versions] == ["5.0.0"]

    versions = client.describe_db_engine_versions(Engine="docdb", DefaultOnly=True)[
        "DBEngineVersions"
    ]
    assert [v["EngineVersion"] for v in versions] == ["5.0.0"]

    assert (
        client.describe_db_engine_versions(Engine="unknown")["DBEngineVersions"] == []
    )


@mock_aws
def test_describe_db_engine_versions__other_engines_share_the_backend():
    rds = boto3.client("rds", region_name="us-east-1")
    versions = rds.describe_db_engine_versions()["DBEngineVersions"]
    engines = {v["Engine"] for v in versions}
    assert {"docdb", "neptune", "aurora-postgresql", "postgres"} <= engines

    neptune = boto3.client("neptune", region_name="us-east-1")
    versions = neptune.describe_db_engine_versions(Engine="neptune")["DBEngineVersions"]
    assert [v["EngineVersion"] for v in versions] == ["1.3.2.1"]


@mock_aws
def test_describe_engine_default_cluster_parameters():
    client = boto3.client("docdb", region_name="us-east-1")
    defaults = client.describe_engine_default_cluster_parameters(
        DBParameterGroupFamily="docdb5.0"
    )["EngineDefaults"]
    assert defaults["DBParameterGroupFamily"] == "docdb5.0"
    params = {p["ParameterName"]: p for p in defaults["Parameters"]}
    assert params["tls"]["ParameterValue"] == "enabled"
    assert params["tls"]["IsModifiable"] is True
    assert params["audit_logs"]["ParameterValue"] == "disabled"
    assert params["profiler_threshold_ms"]["ParameterValue"] == "100"
