"""Unit tests for es-supported APIs."""
import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import
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
    err["Message"].should.equal(
        f"1 validation error detected: Value '{name}' at 'domainName' failed to satisfy constraint: Member must satisfy regular expression pattern: [a-z][a-z0-9\\-]+"
    )
    err["Code"].should.equal("ValidationException")


@mock_es
def test_create_elasticsearch_domain_minimal():
    client = boto3.client("es", region_name="us-east-2")
    resp = client.create_elasticsearch_domain(DomainName="motosearch")

    resp.should.have.key("DomainStatus")
    domain = resp["DomainStatus"]
    domain.should.have.key("DomainName").equals("motosearch")
    domain.should.have.key("DomainId")
    domain.should.have.key("ARN").equals(
        f"arn:aws:es:us-east-2:domain/{domain['DomainId']}"
    )
    domain.should.have.key("Created").equals(True)
    domain.should.have.key("Deleted").equals(False)
    domain.should.have.key("Processing").equals(False)
    domain.should.have.key("UpgradeProcessing").equals(False)
    domain.shouldnt.have.key("ElasticsearchVersion")


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
    domain.should.have.key("DomainId")
    domain.should.have.key("Created").equals(True)
    domain.should.have.key("ElasticsearchVersion").equals("7.10")

    domain.should.have.key("ElasticsearchClusterConfig")
    cluster_config = domain["ElasticsearchClusterConfig"]
    cluster_config.should.have.key("ColdStorageOptions").equals({"Enabled": False})
    cluster_config.should.have.key("DedicatedMasterCount").equals(1)
    cluster_config.should.have.key("DedicatedMasterType").equals(
        "m3.large.elasticsearch"
    )
    cluster_config.should.have.key("WarmEnabled").equals(False)

    domain.should.have.key("EBSOptions")
    ebs = domain["EBSOptions"]
    ebs.should.have.key("EBSEnabled").equals(True)
    ebs.should.have.key("Iops").equals(1)
    ebs.should.have.key("VolumeSize").equals(10)
    ebs.should.have.key("VolumeType").equals("io2")

    domain.should.have.key("AccessPolicies").equals("some unvalidated accesspolicy")

    domain.should.have.key("SnapshotOptions")
    snapshots = domain["SnapshotOptions"]
    snapshots.should.have.key("AutomatedSnapshotStartHour").equals(1)

    domain.should.have.key("VPCOptions")
    vpcs = domain["VPCOptions"]
    vpcs.should.have.key("SubnetIds").equals(["s1"])
    vpcs.should.have.key("SecurityGroupIds").equals(["sg1"])

    domain.should.have.key("CognitoOptions")
    cognito = domain["CognitoOptions"]
    cognito.should.have.key("Enabled").equals(False)

    domain.should.have.key("EncryptionAtRestOptions")
    encryption_at_rest = domain["EncryptionAtRestOptions"]
    encryption_at_rest.should.have.key("Enabled").equals(False)

    domain.should.have.key("NodeToNodeEncryptionOptions")
    encryption = domain["NodeToNodeEncryptionOptions"]
    encryption.should.have.key("Enabled").equals(False)

    domain.should.have.key("AdvancedOptions")
    advanced = domain["AdvancedOptions"]
    advanced.should.have.key("option").equals("value")

    domain.should.have.key("LogPublishingOptions")
    advanced = domain["LogPublishingOptions"]
    advanced.should.have.key("log1").equals({"Enabled": False})

    domain.should.have.key("DomainEndpointOptions")
    endpoint = domain["DomainEndpointOptions"]
    endpoint.should.have.key("EnforceHTTPS").equals(True)
    endpoint.should.have.key("CustomEndpointEnabled").equals(False)

    domain.should.have.key("AdvancedSecurityOptions")
    advanced_security = domain["AdvancedSecurityOptions"]
    advanced_security.should.have.key("Enabled").equals(False)

    domain.should.have.key("AutoTuneOptions")
    auto_tune = domain["AutoTuneOptions"]
    auto_tune.should.have.key("State").equals("ENABLED")


@mock_es
def test_delete_elasticsearch_domain():
    client = boto3.client("es", region_name="ap-southeast-1")
    client.create_elasticsearch_domain(DomainName="motosearch")
    client.delete_elasticsearch_domain(DomainName="motosearch")

    client.list_domain_names()["DomainNames"].should.equal([])


@mock_es
def test_missing_delete_elasticsearch_domain():
    client = boto3.client("es", region_name="ap-southeast-1")
    with pytest.raises(ClientError) as exc:
        client.delete_elasticsearch_domain(DomainName="unknown")

    meta = exc.value.response["ResponseMetadata"]
    meta["HTTPStatusCode"].should.equal(409)

    err = exc.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.equal("Domain not found: unknown")


@mock_es
def test_describe_invalid_domain():
    client = boto3.client("es", region_name="us-east-2")
    with pytest.raises(ClientError) as exc:
        client.describe_elasticsearch_domain(DomainName="moto.org")
    meta = exc.value.response["ResponseMetadata"]
    meta["HTTPStatusCode"].should.equal(400)
    err = exc.value.response["Error"]
    err["Message"].should.equal(
        "1 validation error detected: Value 'moto.org' at 'domainName' failed to satisfy constraint: Member must satisfy regular expression pattern: [a-z][a-z0-9\\-]+"
    )
    err["Code"].should.equal("ValidationException")


@mock_es
def test_describe_unknown_domain():
    client = boto3.client("es", region_name="ap-southeast-1")
    with pytest.raises(ClientError) as exc:
        client.describe_elasticsearch_domain(DomainName="unknown")

    meta = exc.value.response["ResponseMetadata"]
    meta["HTTPStatusCode"].should.equal(409)

    err = exc.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.equal("Domain not found: unknown")


@mock_es
def test_describe_elasticsearch_domain():
    client = boto3.client("es", region_name="ap-southeast-1")
    client.create_elasticsearch_domain(DomainName="motosearch")
    resp = client.describe_elasticsearch_domain(DomainName="motosearch")

    resp.should.have.key("DomainStatus")
    domain = resp["DomainStatus"]
    domain.should.have.key("DomainName").equals("motosearch")
    domain.should.have.key("DomainId")
    domain.should.have.key("ARN").equals(
        f"arn:aws:es:ap-southeast-1:domain/{domain['DomainId']}"
    )
    domain.should.have.key("Created").equals(True)
    domain.should.have.key("Deleted").equals(False)
    domain.should.have.key("Processing").equals(False)
    domain.should.have.key("UpgradeProcessing").equals(False)
    domain.shouldnt.have.key("ElasticsearchVersion")


@mock_es
def test_list_domain_names_initial():
    client = boto3.client("es", region_name="eu-west-1")
    resp = client.list_domain_names()

    resp.should.have.key("DomainNames").equals([])


@mock_es
def test_list_domain_names_with_multiple_domains():
    client = boto3.client("es", region_name="eu-west-1")
    domain_names = [f"env{i}" for i in range(1, 5)]
    for name in domain_names:
        client.create_elasticsearch_domain(DomainName=name)
    resp = client.list_domain_names()

    resp.should.have.key("DomainNames").length_of(4)
    for name in domain_names:
        resp["DomainNames"].should.contain({"DomainName": name})
