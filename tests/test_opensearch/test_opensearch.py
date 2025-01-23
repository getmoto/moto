import boto3
import pytest
from botocore.exceptions import ClientError
from freezegun import freeze_time

from moto import mock_aws, settings

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
def test_create_domain__minimal_options():
    client = boto3.client("opensearch", region_name="eu-west-1")
    status = client.create_domain(DomainName="testdn")["DomainStatus"]
    assert "DomainId" in status
    assert "DomainName" in status
    assert status["DomainName"] == "testdn"
    assert status["Endpoint"] is not None
    assert "Endpoints" not in status


@mock_aws
def test_create_domain_in_vpc():
    client = boto3.client("opensearch", region_name="eu-west-1")
    status = client.create_domain(
        DomainName="testdn", VPCOptions={"SubnetIds": ["sub1"]}
    )["DomainStatus"]
    assert "DomainId" in status
    assert "DomainName" in status
    assert status["DomainName"] == "testdn"
    assert "Endpoint" not in status
    assert status["Endpoints"] is not None


@mock_aws
def test_create_domain_with_some_options():
    client = boto3.client("opensearch", region_name="eu-north-1")
    status = client.create_domain(
        DomainName="testdn",
        DomainEndpointOptions={
            "CustomEndpointEnabled": False,
            "EnforceHTTPS": True,
            "TLSSecurityPolicy": "Policy-Min-TLS-1-0-2019-07",
        },
        EBSOptions={"EBSEnabled": True, "VolumeSize": 10},
        SnapshotOptions={"AutomatedSnapshotStartHour": 20},
        EngineVersion="OpenSearch_1.1",
    )["DomainStatus"]
    assert status["Created"]
    assert status["EngineVersion"]["Options"] == "OpenSearch_1.1"
    assert status["DomainEndpointOptions"] == {
        "EnforceHTTPS": True,
        "TLSSecurityPolicy": "Policy-Min-TLS-1-0-2019-07",
        "CustomEndpointEnabled": False,
    }
    assert status["EBSOptions"] == {"EBSEnabled": True, "VolumeSize": 10}
    assert status["SnapshotOptions"] == {"AutomatedSnapshotStartHour": 20}


@mock_aws
def test_get_compatible_versions():
    client = boto3.client("opensearch", region_name="us-east-2")
    client.create_domain(DomainName="testdn")

    versions = client.get_compatible_versions(DomainName="testdn")["CompatibleVersions"]
    assert len(versions) == 22


@mock_aws
def test_get_compatible_versions_unknown_domain():
    client = boto3.client("opensearch", region_name="us-east-2")

    with pytest.raises(ClientError) as exc:
        client.get_compatible_versions(DomainName="testdn")
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "Domain not found: testdn"


@mock_aws
def test_describe_unknown_domain():
    client = boto3.client("opensearch", region_name="eu-west-1")

    with pytest.raises(ClientError) as exc:
        client.describe_domain(DomainName="testdn")
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "Domain not found: testdn"


@mock_aws
@freeze_time("2015-01-01 12:00:00")
def test_describe_domain():
    # Setup
    client = boto3.client("opensearch", region_name="eu-west-1")
    client.create_domain(DomainName="testdn")

    # Execute
    status = client.describe_domain(DomainName="testdn")["DomainStatus"]
    ev_status = status["EngineVersion"]["Status"]

    # Verify
    assert "DomainId" in status
    assert "DomainName" in status
    assert status["DomainName"] == "testdn"
    assert status["EngineVersion"]["Options"] == "OpenSearch_2.5"
    assert ev_status["State"] == "Active"
    assert ev_status["PendingDeletion"] is False

    if not settings.TEST_SERVER_MODE:
        assert ev_status["CreationDate"] == 1420113600.0
        assert ev_status["UpdateDate"] == 1420113600.0


@mock_aws
def test_delete_domain():
    client = boto3.client("opensearch", region_name="eu-west-1")
    client.create_domain(DomainName="testdn")
    resp = client.delete_domain(DomainName="testdn")
    status = resp["DomainStatus"]
    assert "DomainId" in status
    assert "DomainName" in status
    assert status["Deleted"]  # assume deleted completion
    assert status["DomainName"] == "testdn"


@mock_aws
def test_delete_invalid_domain():
    client = boto3.client("opensearch", region_name="eu-west-1")
    with pytest.raises(ClientError) as exc:
        client.describe_domain(DomainName="testdn")
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "Domain not found: testdn"


@mock_aws
def test_update_domain_config():
    client = boto3.client("opensearch", region_name="eu-north-1")
    client.create_domain(
        DomainName="testdn",
        DomainEndpointOptions={
            "CustomEndpointEnabled": False,
            "EnforceHTTPS": True,
            "TLSSecurityPolicy": "Policy-Min-TLS-1-0-2019-07",
        },
        EBSOptions={"EBSEnabled": True, "VolumeSize": 10},
        EngineVersion="OpenSearch 1.1",
    )

    config = client.update_domain_config(
        DomainName="testdn",
        EBSOptions={"EBSEnabled": False},
    )["DomainConfig"]

    assert config["EBSOptions"] == {"Options": {"EBSEnabled": False}}
    assert config["DomainEndpointOptions"] == {
        "Options": {
            "EnforceHTTPS": True,
            "TLSSecurityPolicy": "Policy-Min-TLS-1-0-2019-07",
            "CustomEndpointEnabled": False,
        }
    }


@mock_aws
def test_list_domain_names():
    client = boto3.client("opensearch", region_name="ap-southeast-1")

    test_domain_names_list_exist = False

    opensearch_domain_name = "testdn"
    opensearch_engine_version = "OpenSearch_1.0"
    client.create_domain(
        DomainName=opensearch_domain_name, EngineVersion=opensearch_engine_version
    )

    resp = client.list_domain_names()
    domain_names = resp["DomainNames"]

    for domain_name in domain_names:
        if domain_name["DomainName"] == opensearch_domain_name:
            test_domain_names_list_exist = True

    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert test_domain_names_list_exist


@mock_aws
def test_list_filtered_domain_names():
    client = boto3.client("opensearch", region_name="ap-southeast-1")

    test_domain_names_list_exist = False

    opensearch_domain_name = "testdn"
    opensearch_engine_version = "OpenSearch_1.0"
    client.create_domain(
        DomainName=opensearch_domain_name, EngineVersion=opensearch_engine_version
    )

    resp = client.list_domain_names(EngineType="OpenSearch")
    domain_names = resp["DomainNames"]

    for domain_name in domain_names:
        if domain_name["DomainName"] == opensearch_domain_name:
            if domain_name["EngineType"] == opensearch_engine_version.split("_")[0]:
                test_domain_names_list_exist = True

    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert test_domain_names_list_exist


@mock_aws
def test_list_unknown_domain_names_engine_type():
    client = boto3.client("opensearch", region_name="ap-southeast-1")

    opensearch_domain_name = "testdn"
    opensearch_engine_version = "OpenSearch_1.0"
    client.create_domain(
        DomainName=opensearch_domain_name, EngineVersion=opensearch_engine_version
    )

    with pytest.raises(ClientError) as exc:
        client.list_domain_names(EngineType="unknown")
    err = exc.value.response["Error"]
    assert err["Code"] == "EngineTypeNotFoundException"
    assert err["Message"] == "Engine Type not found: unknown"


@mock_aws
def test_describe_domains():
    client = boto3.client("opensearch", region_name="us-east-1")
    domain_names = [f"env{i}" for i in range(1, 5)]
    opensearch_engine_version = "OpenSearch_1.0"
    for name in domain_names:
        client.create_domain(DomainName=name, EngineVersion=opensearch_engine_version)
    resp = client.describe_domains(DomainNames=domain_names)

    assert len(resp["DomainStatusList"]) == 4
    for domain in resp["DomainStatusList"]:
        assert domain["DomainName"] in domain_names
        assert "AdvancedSecurityOptions" in domain.keys()
        assert "AdvancedOptions" in domain.keys()

    # Test for invalid domain name
    resp = client.describe_domains(DomainNames=["invalid"])
    assert len(resp["DomainStatusList"]) == 0
