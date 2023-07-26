"""Unit tests for es-supported APIs."""
import boto3
import pytest
from botocore.exceptions import ClientError
from moto import mock_es

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@pytest.mark.parametrize(
    "name", ["getmoto.org", "search-is-$$$", "dev_or_test", "dev/test", "1love", "DEV"]
)
@mock_es
def test_create_domain_invalid_name(name):
    client = boto3.client("es", region_name="us-east-2")
    with pytest.raises(ClientError) as exc:
        client.create_elasticsearch_domain(DomainName=name)
    err = exc.value.response["Error"]
    assert (
        err["Message"]
        == f"1 validation error detected: Value '{name}' at 'domainName' failed to satisfy constraint: Member must satisfy regular expression pattern: [a-z][a-z0-9\\-]+"
    )
    assert err["Code"] == "ValidationException"


@mock_es
def test_create_elasticsearch_domain_minimal():
    client = boto3.client("es", region_name="us-east-2")
    resp = client.create_elasticsearch_domain(DomainName="motosearch")

    domain = resp["DomainStatus"]
    assert domain["DomainName"] == "motosearch"
    assert domain["ARN"] == f"arn:aws:es:us-east-2:domain/{domain['DomainId']}"
    assert domain["Created"] is True
    assert domain["Deleted"] is False
    assert domain["Processing"] is False
    assert domain["UpgradeProcessing"] is False
    assert "ElasticsearchVersion" not in domain


@mock_es
def test_create_elasticsearch_domain():
    client = boto3.client("es", region_name="us-east-2")
    resp = client.create_elasticsearch_domain(
        DomainName="motosearch",
        ElasticsearchVersion="7.10",
        ElasticsearchClusterConfig={
            "InstanceType": "m3.large.elasticsearch",
            "InstanceCount": 1,
            "DedicatedMasterEnabled": True,
            "DedicatedMasterType": "m3.large.elasticsearch",
            "DedicatedMasterCount": 1,
            "ZoneAwarenessEnabled": False,
            "WarmEnabled": False,
            "ColdStorageOptions": {"Enabled": False},
        },
        EBSOptions={
            "EBSEnabled": True,
            "VolumeType": "io2",
            "VolumeSize": 10,
            "Iops": 1,
        },
        AccessPolicies="some unvalidated accesspolicy",
        SnapshotOptions={"AutomatedSnapshotStartHour": 1},
        VPCOptions={"SubnetIds": ["s1"], "SecurityGroupIds": ["sg1"]},
        CognitoOptions={"Enabled": False},
        EncryptionAtRestOptions={"Enabled": False},
        NodeToNodeEncryptionOptions={"Enabled": False},
        AdvancedOptions={"option": "value"},
        LogPublishingOptions={"log1": {"Enabled": False}},
        DomainEndpointOptions={"EnforceHTTPS": True, "CustomEndpointEnabled": False},
        AdvancedSecurityOptions={"Enabled": False},
        AutoTuneOptions={"DesiredState": "ENABLED"},
    )

    domain = resp["DomainStatus"]
    assert "DomainId" in domain
    assert domain["Created"] is True
    assert domain["ElasticsearchVersion"] == "7.10"

    cluster_config = domain["ElasticsearchClusterConfig"]
    assert cluster_config["ColdStorageOptions"] == {"Enabled": False}
    assert cluster_config["DedicatedMasterCount"] == 1
    assert cluster_config["DedicatedMasterType"] == "m3.large.elasticsearch"
    assert cluster_config["WarmEnabled"] is False

    ebs = domain["EBSOptions"]
    assert ebs["EBSEnabled"] is True
    assert ebs["Iops"] == 1
    assert ebs["VolumeSize"] == 10
    assert ebs["VolumeType"] == "io2"

    assert domain["AccessPolicies"] == "some unvalidated accesspolicy"

    snapshots = domain["SnapshotOptions"]
    assert snapshots["AutomatedSnapshotStartHour"] == 1

    vpcs = domain["VPCOptions"]
    assert vpcs["SubnetIds"] == ["s1"]
    assert vpcs["SecurityGroupIds"] == ["sg1"]

    cognito = domain["CognitoOptions"]
    assert cognito["Enabled"] is False

    encryption_at_rest = domain["EncryptionAtRestOptions"]
    assert encryption_at_rest["Enabled"] is False

    encryption = domain["NodeToNodeEncryptionOptions"]
    assert encryption["Enabled"] is False

    advanced = domain["AdvancedOptions"]
    assert advanced["option"] == "value"

    advanced = domain["LogPublishingOptions"]
    assert advanced["log1"] == {"Enabled": False}

    endpoint = domain["DomainEndpointOptions"]
    assert endpoint["EnforceHTTPS"] is True
    assert endpoint["CustomEndpointEnabled"] is False

    advanced_security = domain["AdvancedSecurityOptions"]
    assert advanced_security["Enabled"] is False

    auto_tune = domain["AutoTuneOptions"]
    assert auto_tune["State"] == "ENABLED"


@mock_es
def test_delete_elasticsearch_domain():
    client = boto3.client("es", region_name="ap-southeast-1")
    client.create_elasticsearch_domain(DomainName="motosearch")
    client.delete_elasticsearch_domain(DomainName="motosearch")

    assert client.list_domain_names()["DomainNames"] == []


@mock_es
def test_missing_delete_elasticsearch_domain():
    client = boto3.client("es", region_name="ap-southeast-1")
    with pytest.raises(ClientError) as exc:
        client.delete_elasticsearch_domain(DomainName="unknown")

    meta = exc.value.response["ResponseMetadata"]
    assert meta["HTTPStatusCode"] == 409

    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "Domain not found: unknown"


@mock_es
def test_describe_invalid_domain():
    client = boto3.client("es", region_name="us-east-2")
    with pytest.raises(ClientError) as exc:
        client.describe_elasticsearch_domain(DomainName="moto.org")
    meta = exc.value.response["ResponseMetadata"]
    assert meta["HTTPStatusCode"] == 400
    err = exc.value.response["Error"]
    assert (
        err["Message"]
        == "1 validation error detected: Value 'moto.org' at 'domainName' failed to satisfy constraint: Member must satisfy regular expression pattern: [a-z][a-z0-9\\-]+"
    )
    assert err["Code"] == "ValidationException"


@mock_es
def test_describe_unknown_domain():
    client = boto3.client("es", region_name="ap-southeast-1")
    with pytest.raises(ClientError) as exc:
        client.describe_elasticsearch_domain(DomainName="unknown")

    meta = exc.value.response["ResponseMetadata"]
    assert meta["HTTPStatusCode"] == 409

    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "Domain not found: unknown"


@mock_es
def test_describe_elasticsearch_domain():
    client = boto3.client("es", region_name="ap-southeast-1")
    client.create_elasticsearch_domain(DomainName="motosearch")
    resp = client.describe_elasticsearch_domain(DomainName="motosearch")

    domain = resp["DomainStatus"]
    assert domain["DomainName"] == "motosearch"
    assert domain["ARN"] == f"arn:aws:es:ap-southeast-1:domain/{domain['DomainId']}"
    assert domain["Created"] is True
    assert domain["Deleted"] is False
    assert domain["Processing"] is False
    assert domain["UpgradeProcessing"] is False
    assert "ElasticsearchVersion" not in domain


@mock_es
def test_list_domain_names_initial():
    client = boto3.client("es", region_name="eu-west-1")
    resp = client.list_domain_names()

    assert resp["DomainNames"] == []


@mock_es
def test_list_domain_names_with_multiple_domains():
    client = boto3.client("es", region_name="eu-west-1")
    domain_names = [f"env{i}" for i in range(1, 5)]
    for name in domain_names:
        client.create_elasticsearch_domain(DomainName=name)
    resp = client.list_domain_names()

    assert len(resp["DomainNames"]) == 4
    for name in domain_names:
        assert {"DomainName": name} in resp["DomainNames"]
