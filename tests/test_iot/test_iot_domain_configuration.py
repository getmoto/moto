import boto3
import pytest

from moto import mock_iot


@mock_iot
def test_create_domain_configuration_only_name():
    client = boto3.client("iot", region_name="us-east-1")
    domain_config = client.create_domain_configuration(
        domainConfigurationName="testConfig"
    )
    assert domain_config["domainConfigurationName"] == "testConfig"
    assert domain_config["domainConfigurationArn"] is not None


@mock_iot
def test_create_duplicate_domain_configuration_fails():
    client = boto3.client("iot", region_name="us-east-1")
    domain_config = client.create_domain_configuration(
        domainConfigurationName="testConfig"
    )
    assert domain_config["domainConfigurationName"] == "testConfig"
    assert domain_config["domainConfigurationArn"] is not None
    with pytest.raises(client.exceptions.ResourceAlreadyExistsException) as exc:
        client.create_domain_configuration(domainConfigurationName="testConfig")
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceAlreadyExistsException"
    assert err["Message"] == "Domain configuration with given name already exists."


@mock_iot
def test_create_domain_configuration_full_params():
    client = boto3.client("iot", region_name="us-east-1")
    domain_config = client.create_domain_configuration(
        domainConfigurationName="testConfig",
        domainName="example.com",
        serverCertificateArns=["ARN1", "ARN2"],
        validationCertificateArn="VARN",
        authorizerConfig={
            "defaultAuthorizerName": "name",
            "allowAuthorizerOverride": True,
        },
        serviceType="DATA",
    )
    assert domain_config["domainConfigurationName"] == "testConfig"
    assert domain_config["domainConfigurationArn"] is not None


@mock_iot
def test_create_domain_configuration_invalid_service_type():
    client = boto3.client("iot", region_name="us-east-1")
    with pytest.raises(client.exceptions.InvalidRequestException) as exc:
        client.create_domain_configuration(
            domainConfigurationName="testConfig", serviceType="INVALIDTYPE"
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidRequestException"
    assert (
        err["Message"]
        == "An error occurred (InvalidRequestException) when calling the DescribeDomainConfiguration operation: Service type INVALIDTYPE not recognized."
    )


@mock_iot
def test_describe_nonexistent_domain_configuration():
    client = boto3.client("iot", region_name="us-east-1")
    with pytest.raises(client.exceptions.ResourceNotFoundException) as exc:
        client.describe_domain_configuration(domainConfigurationName="doesntExist")
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "The specified resource does not exist."


@mock_iot
def test_describe_domain_configuration():
    client = boto3.client("iot", region_name="us-east-1")

    client.create_domain_configuration(
        domainConfigurationName="testConfig",
        domainName="example.com",
        serverCertificateArns=["ARN1", "ARN2"],
        validationCertificateArn="VARN",
        authorizerConfig={
            "defaultAuthorizerName": "name",
            "allowAuthorizerOverride": True,
        },
        serviceType="DATA",
    )
    described_config = client.describe_domain_configuration(
        domainConfigurationName="testConfig"
    )
    assert described_config["domainConfigurationName"] == "testConfig"
    assert described_config["domainConfigurationArn"]
    assert described_config["serverCertificates"]
    assert described_config["authorizerConfig"]
    assert described_config["domainConfigurationStatus"] == "ENABLED"
    assert described_config["serviceType"] == "DATA"
    assert described_config["domainType"]
    assert described_config["lastStatusChangeDate"]


@mock_iot
def test_update_domain_configuration():
    client = boto3.client("iot", region_name="us-east-1")
    client.create_domain_configuration(
        domainConfigurationName="testConfig",
        domainName="example.com",
        serverCertificateArns=["ARN1", "ARN2"],
        validationCertificateArn="VARN",
        authorizerConfig={
            "defaultAuthorizerName": "name",
            "allowAuthorizerOverride": True,
        },
        serviceType="DATA",
    )
    client.update_domain_configuration(
        domainConfigurationName="testConfig",
        authorizerConfig={
            "defaultAuthorizerName": "updatedName",
            "allowAuthorizerOverride": False,
        },
        domainConfigurationStatus="DISABLED",
    )
    updated = client.describe_domain_configuration(domainConfigurationName="testConfig")
    assert updated["authorizerConfig"]["defaultAuthorizerName"] == "updatedName"
    assert updated["authorizerConfig"]["allowAuthorizerOverride"] is False
    assert updated["domainConfigurationStatus"] == "DISABLED"


@mock_iot
def test_update_domain_configuration_remove_authorizer_type():
    client = boto3.client("iot", region_name="us-east-1")
    client.create_domain_configuration(
        domainConfigurationName="testConfig",
        domainName="example.com",
        serverCertificateArns=["ARN1", "ARN2"],
        validationCertificateArn="VARN",
        authorizerConfig={
            "defaultAuthorizerName": "name",
            "allowAuthorizerOverride": True,
        },
        serviceType="DATA",
    )
    client.update_domain_configuration(
        domainConfigurationName="testConfig", removeAuthorizerConfig=True
    )
    config = client.describe_domain_configuration(domainConfigurationName="testConfig")
    assert "authorizerConfig" not in config


@mock_iot
def test_update_nonexistent_domain_configuration():
    client = boto3.client("iot", region_name="us-east-1")
    with pytest.raises(client.exceptions.ResourceNotFoundException) as exc:
        client.update_domain_configuration(domainConfigurationName="doesntExist")
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "The specified resource does not exist."


@mock_iot
def test_list_domain_configuration():
    client = boto3.client("iot", region_name="us-east-1")
    client.create_domain_configuration(domainConfigurationName="testConfig1")
    client.create_domain_configuration(domainConfigurationName="testConfig2")
    domain_configs = client.list_domain_configurations()["domainConfigurations"]
    assert len(domain_configs) == 2
    assert domain_configs[0]["domainConfigurationName"] == "testConfig1"
    assert domain_configs[1]["domainConfigurationName"] == "testConfig2"


@mock_iot
def test_delete_domain_configuration():
    client = boto3.client("iot", region_name="us-east-1")
    client.create_domain_configuration(domainConfigurationName="testConfig")
    domain_configs = client.list_domain_configurations()
    assert len(domain_configs["domainConfigurations"]) == 1
    client.delete_domain_configuration(domainConfigurationName="testConfig")
    domain_configs = client.list_domain_configurations()
    assert len(domain_configs["domainConfigurations"]) == 0


@mock_iot
def test_delete_nonexistent_domain_configuration():
    client = boto3.client("iot", region_name="us-east-1")
    with pytest.raises(client.exceptions.ResourceNotFoundException) as exc:
        client.delete_domain_configuration(domainConfigurationName="doesntExist")
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "The specified resource does not exist."
