import boto3
import pytest

from moto import mock_iot


@mock_iot
def test_create_domain_configuration_only_name():
    client = boto3.client("iot", region_name="us-east-1")
    domain_config = client.create_domain_configuration(
        domainConfigurationName="testConfig"
    )
    domain_config.should.have.key("domainConfigurationName").which.should.equal(
        "testConfig"
    )
    domain_config.should.have.key("domainConfigurationArn").which.should_not.be.none


@mock_iot
def test_create_duplicate_domain_configuration_fails():
    client = boto3.client("iot", region_name="us-east-1")
    domain_config = client.create_domain_configuration(
        domainConfigurationName="testConfig"
    )
    domain_config.should.have.key("domainConfigurationName").which.should.equal(
        "testConfig"
    )
    domain_config.should.have.key("domainConfigurationArn").which.should_not.be.none
    with pytest.raises(client.exceptions.ResourceAlreadyExistsException) as exc:
        client.create_domain_configuration(domainConfigurationName="testConfig")
    err = exc.value.response["Error"]
    err["Code"].should.equal("ResourceAlreadyExistsException")
    err["Message"].should.equal("Domain configuration with given name already exists.")


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
    domain_config.should.have.key("domainConfigurationName").which.should.equal(
        "testConfig"
    )
    domain_config.should.have.key("domainConfigurationArn").which.should_not.be.none


@mock_iot
def test_create_domain_configuration_invalid_service_type():
    client = boto3.client("iot", region_name="us-east-1")
    with pytest.raises(client.exceptions.InvalidRequestException) as exc:
        client.create_domain_configuration(
            domainConfigurationName="testConfig", serviceType="INVALIDTYPE"
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("InvalidRequestException")
    err["Message"].should.equal(
        "An error occurred (InvalidRequestException) when calling the DescribeDomainConfiguration operation: Service type INVALIDTYPE not recognized."
    )


@mock_iot
def test_describe_nonexistent_domain_configuration():
    client = boto3.client("iot", region_name="us-east-1")
    with pytest.raises(client.exceptions.ResourceNotFoundException) as exc:
        client.describe_domain_configuration(domainConfigurationName="doesntExist")
    err = exc.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.equal("The specified resource does not exist.")


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
    described_config.should.have.key("domainConfigurationName").which.should.equal(
        "testConfig"
    )
    described_config.should.have.key("domainConfigurationArn")
    described_config.should.have.key("serverCertificates")
    described_config.should.have.key("authorizerConfig")
    described_config.should.have.key("domainConfigurationStatus").which.should.equal(
        "ENABLED"
    )
    described_config.should.have.key("serviceType").which.should.equal("DATA")
    described_config.should.have.key("domainType")
    described_config.should.have.key("lastStatusChangeDate")


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
    described_updated_config = client.describe_domain_configuration(
        domainConfigurationName="testConfig"
    )
    described_updated_config.should.have.key("authorizerConfig").which.should.have.key(
        "defaultAuthorizerName"
    ).which.should.equal("updatedName")
    described_updated_config.should.have.key("authorizerConfig").which.should.have.key(
        "allowAuthorizerOverride"
    ).which.should.equal(False)
    described_updated_config.should.have.key(
        "domainConfigurationStatus"
    ).which.should.equal("DISABLED")


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
    described_updated_config = client.describe_domain_configuration(
        domainConfigurationName="testConfig"
    )
    described_updated_config.should_not.have.key("authorizerConfig")


@mock_iot
def test_update_nonexistent_domain_configuration():
    client = boto3.client("iot", region_name="us-east-1")
    with pytest.raises(client.exceptions.ResourceNotFoundException) as exc:
        client.update_domain_configuration(domainConfigurationName="doesntExist")
    err = exc.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.equal("The specified resource does not exist.")


@mock_iot
def test_list_domain_configuration():
    client = boto3.client("iot", region_name="us-east-1")
    client.create_domain_configuration(domainConfigurationName="testConfig1")
    client.create_domain_configuration(domainConfigurationName="testConfig2")
    domain_configs = client.list_domain_configurations()
    domain_configs.should.have.key("domainConfigurations").which.should.have.length_of(
        2
    )
    domain_configs["domainConfigurations"][0].should.have.key(
        "domainConfigurationName"
    ).which.should.equal("testConfig1")
    domain_configs["domainConfigurations"][1].should.have.key(
        "domainConfigurationName"
    ).which.should.equal("testConfig2")


@mock_iot
def test_delete_domain_configuration():
    client = boto3.client("iot", region_name="us-east-1")
    client.create_domain_configuration(domainConfigurationName="testConfig")
    domain_configs = client.list_domain_configurations()
    domain_configs.should.have.key("domainConfigurations").which.should.have.length_of(
        1
    )
    client.delete_domain_configuration(domainConfigurationName="testConfig")
    domain_configs = client.list_domain_configurations()
    domain_configs.should.have.key("domainConfigurations").which.should.have.length_of(
        0
    )


@mock_iot
def test_delete_nonexistent_domain_configuration():
    client = boto3.client("iot", region_name="us-east-1")
    with pytest.raises(client.exceptions.ResourceNotFoundException) as exc:
        client.delete_domain_configuration(domainConfigurationName="doesntExist")
    err = exc.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.equal("The specified resource does not exist.")
