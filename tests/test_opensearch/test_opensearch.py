import boto3
import pytest

from botocore.exceptions import ClientError
from moto import mock_opensearch

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_opensearch
def test_create_domain__minimal_options():
    client = boto3.client("opensearch", region_name="eu-west-1")
    status = client.create_domain(DomainName="testdn")["DomainStatus"]
    assert "DomainId" in status
    assert "DomainName" in status
    assert status["DomainName"] == "testdn"
    assert status["Endpoint"] is not None
    assert "Endpoints" not in status


@mock_opensearch
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


@mock_opensearch
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
    assert status["EngineVersion"] == "OpenSearch_1.1"
    assert status["DomainEndpointOptions"] == {
        "EnforceHTTPS": True,
        "TLSSecurityPolicy": "Policy-Min-TLS-1-0-2019-07",
        "CustomEndpointEnabled": False,
    }
    assert status["EBSOptions"] == {"EBSEnabled": True, "VolumeSize": 10}
    assert status["SnapshotOptions"] == {"AutomatedSnapshotStartHour": 20}


@mock_opensearch
def test_get_compatible_versions():
    client = boto3.client("opensearch", region_name="us-east-2")
    client.create_domain(DomainName="testdn")

    versions = client.get_compatible_versions(DomainName="testdn")["CompatibleVersions"]
    assert len(versions) == 22


@mock_opensearch
def test_get_compatible_versions_unknown_domain():
    client = boto3.client("opensearch", region_name="us-east-2")

    with pytest.raises(ClientError) as exc:
        client.get_compatible_versions(DomainName="testdn")
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "Domain not found: testdn"


@mock_opensearch
def test_describe_unknown_domain():
    client = boto3.client("opensearch", region_name="eu-west-1")

    with pytest.raises(ClientError) as exc:
        client.describe_domain(DomainName="testdn")
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "Domain not found: testdn"


@mock_opensearch
def test_describe_domain():
    client = boto3.client("opensearch", region_name="eu-west-1")
    client.create_domain(DomainName="testdn")

    status = client.describe_domain(DomainName="testdn")["DomainStatus"]
    assert "DomainId" in status
    assert "DomainName" in status
    assert status["DomainName"] == "testdn"


@mock_opensearch
def test_delete_domain():
    client = boto3.client("opensearch", region_name="eu-west-1")
    client.create_domain(DomainName="testdn")
    client.delete_domain(DomainName="testdn")

    with pytest.raises(ClientError) as exc:
        client.describe_domain(DomainName="testdn")
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "Domain not found: testdn"


@mock_opensearch
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
