"""Unit tests for transfer-supported APIs."""

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws


@pytest.fixture(name="client")
def fixture_transfer_client():
    with mock_aws():
        yield boto3.client("transfer", region_name="us-east-1")


@pytest.fixture(name="server")
def fixture_transfer_mock_server(client):
    yield client.create_server(
        Certificate="mock_certificate",
        Domain="S3",
        EndpointDetails={
            "AddressAllocationIds": ["allocation_1", "allocation_2"],
            "SubnetIds": ["subnet_1", "subnet_2"],
            "VpcEndpointId": "mock_vpc_endpoint_id_1",
            "VpcId": "mock_vpc_id",
            "SecurityGroupIds": ["mock_sg_id_1", "mock_sg_id_2"],
        },
        EndpointType="VPC",
        HostKey="ED25519",
        IdentityProviderDetails={
            "Url": "mock_url",
            "InvocationRole": "mock_invocation_role",
            "DirectoryId": "mock_directory_id",
            "Function": "mock_function",
            "SftpAuthenticationMethods": "PUBLIC_KEY_AND_PASSWORD",
        },
        IdentityProviderType="AWS_DIRECTORY_SERVICE",
        LoggingRole="mock_logging_role",
        PostAuthenticationLoginBanner="mock_post_authentication_login_banner",
        PreAuthenticationLoginBanner="mock_pre_authentication_login_banner",
        Protocols=["FTPS", "FTP", "SFTP"],
        ProtocolDetails={
            "PassiveIp": "mock_passive_ip",
            "TlsSessionResumptionMode": "ENABLED",
            "SetStatOption": "ENABLE_NO_OP",
            "As2Transports": ["HTTP"],
        },
        SecurityPolicyName="mock_security_policy_name",
        StructuredLogDestinations=[
            "structured_log_destinations_1",
            "structured_log_destinations_2",
        ],
        S3StorageOptions={"DirectoryListingOptimization": "ENABLED"},
        Tags=[{"Key": "Owner", "Value": "MotoUser1337"}],
        WorkflowDetails={
            "OnUpload": [
                {
                    "WorkflowId": "mock_upload_workflow_id",
                    "ExecutionRole": "mock_upload_execution_role",
                }
            ],
            "OnPartialUpload": [
                {
                    "WorkflowId": "mock_partial_upload_workflow_id",
                    "ExecutionRole": "mock_partial_upload_execution_role",
                }
            ],
        },
    )


def test_create_describe_and_delete_server(client, server):
    assert "ServerId" in server
    server_id = server["ServerId"]

    connection = client.describe_server(ServerId=server_id)
    described_server = connection["Server"]

    assert described_server["Certificate"] == "mock_certificate"
    assert described_server["Domain"] == "S3"
    assert described_server["EndpointType"] == "VPC"
    assert described_server["HostKeyFingerprint"] == "ED25519"
    assert described_server["IdentityProviderType"] == "AWS_DIRECTORY_SERVICE"
    assert described_server["LoggingRole"] == "mock_logging_role"
    assert (
        described_server["PostAuthenticationLoginBanner"]
        == "mock_post_authentication_login_banner"
    )
    assert (
        described_server["PreAuthenticationLoginBanner"]
        == "mock_pre_authentication_login_banner"
    )
    assert described_server["Protocols"] == ["FTPS", "FTP", "SFTP"]
    assert described_server["SecurityPolicyName"] == "mock_security_policy_name"
    assert described_server["StructuredLogDestinations"] == [
        "structured_log_destinations_1",
        "structured_log_destinations_2",
    ]
    assert described_server["EndpointDetails"]["AddressAllocationIds"] == [
        "allocation_1",
        "allocation_2",
    ]
    assert described_server["EndpointDetails"]["SubnetIds"] == ["subnet_1", "subnet_2"]
    assert (
        described_server["EndpointDetails"]["VpcEndpointId"] == "mock_vpc_endpoint_id_1"
    )
    assert described_server["EndpointDetails"]["VpcId"] == "mock_vpc_id"
    assert described_server["EndpointDetails"]["SecurityGroupIds"] == [
        "mock_sg_id_1",
        "mock_sg_id_2",
    ]
    assert described_server["IdentityProviderDetails"]["Url"] == "mock_url"
    assert (
        described_server["IdentityProviderDetails"]["InvocationRole"]
        == "mock_invocation_role"
    )
    assert (
        described_server["IdentityProviderDetails"]["DirectoryId"]
        == "mock_directory_id"
    )
    assert described_server["IdentityProviderDetails"]["Function"] == "mock_function"
    assert (
        described_server["IdentityProviderDetails"]["SftpAuthenticationMethods"]
        == "PUBLIC_KEY_AND_PASSWORD"
    )
    assert described_server["ProtocolDetails"]["PassiveIp"] == "mock_passive_ip"
    assert described_server["ProtocolDetails"]["TlsSessionResumptionMode"] == "ENABLED"
    assert described_server["ProtocolDetails"]["SetStatOption"] == "ENABLE_NO_OP"
    assert described_server["ProtocolDetails"]["As2Transports"] == ["HTTP"]
    assert (
        described_server["S3StorageOptions"]["DirectoryListingOptimization"]
        == "ENABLED"
    )
    assert described_server["Tags"] == [{"Key": "Owner", "Value": "MotoUser1337"}]
    assert (
        described_server["WorkflowDetails"]["OnUpload"][0]["WorkflowId"]
        == "mock_upload_workflow_id"
    )
    assert (
        described_server["WorkflowDetails"]["OnUpload"][0]["ExecutionRole"]
        == "mock_upload_execution_role"
    )
    assert (
        described_server["WorkflowDetails"]["OnPartialUpload"][0]["WorkflowId"]
        == "mock_partial_upload_workflow_id"
    )
    assert (
        described_server["WorkflowDetails"]["OnPartialUpload"][0]["ExecutionRole"]
        == "mock_partial_upload_execution_role"
    )
    assert described_server["As2ServiceManagedEgressIpAddresses"] == ["0.0.0.0/0"]
    assert "_users" not in described_server

    connection = client.delete_server(ServerId=server_id)

    assert server_id not in connection


def test_create_describe_and_delete_user(client, server):
    connection = client.create_user(
        HomeDirectory="/Users/mock_user",
        HomeDirectoryType="PATH",
        HomeDirectoryMappings=[
            {
                "Entry": "/directory1",
                "Target": "/bucket_name/home/mydirectory",
                # Type is optional
            }
        ],
        Policy="MockPolicy",
        PosixProfile={
            "Uid": 0,
            "Gid": 1,
        },
        Role="TransferFamilyAdministrator",
        ServerId=server["ServerId"],
        SshPublicKeyBody="ED25519",
        Tags=[{"Key": "Owner", "Value": "MotoUser1337"}],
        UserName="test_user",
    )
    user_name = connection["UserName"]
    server_id = connection["ServerId"]

    assert user_name == "test_user"
    assert server_id == server["ServerId"]

    connection = client.describe_user(UserName=user_name, ServerId=server_id)

    assert connection["ServerId"] == server_id
    user = connection["User"]
    assert user["HomeDirectory"] == "/Users/mock_user"
    assert user["HomeDirectoryType"] == "PATH"
    assert user["HomeDirectoryMappings"][0]["Entry"] == "/directory1"
    assert user["HomeDirectoryMappings"][0]["Target"] == "/bucket_name/home/mydirectory"
    assert user["Policy"] == "MockPolicy"
    assert user["PosixProfile"]["Uid"] == 0
    assert user["PosixProfile"]["Gid"] == 1
    assert user["Role"] == "TransferFamilyAdministrator"
    assert user["SshPublicKeys"][0]["SshPublicKeyBody"] == "ED25519"
    assert user["Tags"][0]["Key"] == "Owner"
    assert user["Tags"][0]["Value"] == "MotoUser1337"
    assert user["UserName"] == "test_user"

    client.delete_user(UserName=user_name, ServerId=server_id)

    with pytest.raises(ClientError):
        client.describe_user(UserName=user_name, ServerId=server_id)


def test_import_and_delete_ssh_public_key(client, server):
    server_id = server["ServerId"]
    user_name = "test_user"
    client.create_user(
        HomeDirectory="/Users/mock_user",
        HomeDirectoryType="PATH",
        HomeDirectoryMappings=[
            {
                "Entry": "/directory1",
                "Target": "/bucket_name/home/mydirectory",
            }
        ],
        Policy="MockPolicy",
        PosixProfile={
            "Uid": 0,
            "Gid": 1,
        },
        Role="TransferFamilyAdministrator",
        ServerId=server_id,
        SshPublicKeyBody="ED25519",
        Tags=[{"Key": "Owner", "Value": "MotoUser1337"}],
        UserName=user_name,
    )
    client.import_ssh_public_key(
        ServerId=server_id,
        SshPublicKeyBody="RSA",
        UserName=user_name,
    )
    connection = client.describe_user(UserName=user_name, ServerId=server_id)
    assert connection["User"]["SshPublicKeys"][-1]["SshPublicKeyBody"] == "RSA"
    client.delete_ssh_public_key(
        ServerId=server_id,
        UserName=user_name,
        SshPublicKeyId=connection["User"]["SshPublicKeys"][-1]["SshPublicKeyId"],
    )
    connection = client.describe_user(UserName=user_name, ServerId=server_id)
    assert connection["User"]["SshPublicKeys"][-1]["SshPublicKeyBody"] == "ED25519"


@mock_aws
def test_create_multiple_servers():
    """Test that creating multiple servers results in unique entries."""
    client = boto3.client("transfer", region_name="us-east-1")

    client.create_server()
    client.create_server()

    response = client.list_servers()
    assert len(response["Servers"]) == 2


def test_list_servers_empty(client):
    response = client.list_servers()
    assert response["Servers"] == []


def test_list_servers(client, server):
    server_id = server["ServerId"]
    response = client.list_servers()

    assert len(response["Servers"]) == 1
    listed_server = response["Servers"][0]

    assert listed_server["ServerId"] == server_id
    assert listed_server["Domain"] == "S3"
    assert listed_server["EndpointType"] == "VPC"
    assert listed_server["IdentityProviderType"] == "AWS_DIRECTORY_SERVICE"
    assert listed_server["LoggingRole"] == "mock_logging_role"
    assert listed_server["State"] == "ONLINE"
    assert listed_server["UserCount"] == 0
    assert "Arn" in listed_server


def test_list_servers_multiple(client):
    client.create_server(Domain="S3")
    client.create_server(Domain="EFS")

    response = client.list_servers()
    assert len(response["Servers"]) == 2


def test_create_and_describe_connector_with_sftp_config(client):
    create_response = client.create_connector(
        Url="sftp://example.com",
        AccessRole="arn:aws:iam::123456789012:role/TransferAccessRole",
        LoggingRole="arn:aws:iam::123456789012:role/TransferLoggingRole",
        Tags=[{"Key": "Environment", "Value": "Test"}],
        SftpConfig={
            "UserSecretId": "arn:aws:secretsmanager:us-east-1:123456789012:secret:my-secret",
            "TrustedHostKeys": ["mock_trusted_host_key"],
        },
        SecurityPolicyName="TransferSFTPConnectorSecurityPolicy-2024-01",
    )

    assert "ConnectorId" in create_response
    connector_id = create_response["ConnectorId"]
    assert connector_id.startswith("c-")

    response = client.describe_connector(ConnectorId=connector_id)
    connector = response["Connector"]

    assert connector["ConnectorId"] == connector_id
    assert connector["Url"] == "sftp://example.com"
    assert (
        connector["AccessRole"] == "arn:aws:iam::123456789012:role/TransferAccessRole"
    )
    assert (
        connector["LoggingRole"] == "arn:aws:iam::123456789012:role/TransferLoggingRole"
    )
    assert connector["Tags"] == [{"Key": "Environment", "Value": "Test"}]
    assert (
        connector["SftpConfig"]["UserSecretId"]
        == "arn:aws:secretsmanager:us-east-1:123456789012:secret:my-secret"
    )
    assert connector["SftpConfig"]["TrustedHostKeys"] == ["mock_trusted_host_key"]
    assert (
        connector["SecurityPolicyName"] == "TransferSFTPConnectorSecurityPolicy-2024-01"
    )
    assert "Arn" in connector
    assert "ServiceManagedEgressIpAddresses" in connector


def test_create_and_describe_connector_with_as2_config(client):
    create_response = client.create_connector(
        Url="http://partner.example.com/as2",
        AccessRole="arn:aws:iam::123456789012:role/TransferAccessRole",
        As2Config={
            "LocalProfileId": "p-mock_local_profile",
            "PartnerProfileId": "p-mock_partner_profile",
            "MessageSubject": "mock_message_subject",
            "Compression": "ZLIB",
            "EncryptionAlgorithm": "AES256_CBC",
            "SigningAlgorithm": "SHA256",
            "MdnSigningAlgorithm": "SHA256",
            "MdnResponse": "SYNC",
            "BasicAuthSecretId": "arn:aws:secretsmanager:us-east-1:123456789012:secret:mock-auth",
        },
    )

    assert "ConnectorId" in create_response
    connector_id = create_response["ConnectorId"]
    assert connector_id.startswith("c-")

    response = client.describe_connector(ConnectorId=connector_id)
    connector = response["Connector"]

    assert connector["As2Config"]["LocalProfileId"] == "p-mock_local_profile"
    assert connector["As2Config"]["PartnerProfileId"] == "p-mock_partner_profile"
    assert connector["As2Config"]["MessageSubject"] == "mock_message_subject"
    assert connector["As2Config"]["Compression"] == "ZLIB"
    assert connector["As2Config"]["EncryptionAlgorithm"] == "AES256_CBC"
    assert connector["As2Config"]["SigningAlgorithm"] == "SHA256"
    assert connector["As2Config"]["MdnSigningAlgorithm"] == "SHA256"
    assert connector["As2Config"]["MdnResponse"] == "SYNC"


def test_describe_connector_not_found(client):
    with pytest.raises(ClientError) as exc:
        client.describe_connector(ConnectorId="c-01234567890abcdef")
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"


def test_delete_connector(client):
    create_response = client.create_connector(
        Url="sftp://example.com",
        AccessRole="arn:aws:iam::123456789012:role/TransferAccessRole",
    )
    connector_id = create_response["ConnectorId"]

    client.delete_connector(ConnectorId=connector_id)

    with pytest.raises(ClientError) as exc:
        client.describe_connector(ConnectorId=connector_id)
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"


def test_delete_connector_not_found(client):
    with pytest.raises(ClientError) as exc:
        client.delete_connector(ConnectorId="c-12345678901abcdef")
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"


def test_list_connectors_empty(client):
    response = client.list_connectors()
    assert response["Connectors"] == []


def test_list_connectors(client):
    client.create_connector(
        Url="sftp://server1.example.com",
        AccessRole="arn:aws:iam::123456789012:role/Role1",
    )
    client.create_connector(
        Url="sftp://server2.example.com",
        AccessRole="arn:aws:iam::123456789012:role/Role2",
    )

    response = client.list_connectors()

    assert len(response["Connectors"]) == 2
    urls = [c["Url"] for c in response["Connectors"]]
    assert "sftp://server1.example.com" in urls
    assert "sftp://server2.example.com" in urls
    for connector in response["Connectors"]:
        assert "Arn" in connector
        assert "ConnectorId" in connector
        assert "Url" in connector


def test_update_connector(client):
    create_response = client.create_connector(
        Url="sftp://example.com",
        AccessRole="arn:aws:iam::123456789012:role/TransferAccessRole",
        SftpConfig={
            "UserSecretId": "arn:aws:secretsmanager:us-east-1:123456789012:secret:old-secret",
            "TrustedHostKeys": ["mock_old_host_key"],
        },
    )
    connector_id = create_response["ConnectorId"]

    client.update_connector(
        ConnectorId=connector_id,
        Url="sftp://updated.example.com",
        SftpConfig={
            "UserSecretId": "arn:aws:secretsmanager:us-east-1:123456789012:secret:new-secret",
            "TrustedHostKeys": ["mock_new_host_key"],
        },
    )

    describe_response = client.describe_connector(ConnectorId=connector_id)
    connector = describe_response["Connector"]

    assert connector["Url"] == "sftp://updated.example.com"
    assert (
        connector["SftpConfig"]["UserSecretId"]
        == "arn:aws:secretsmanager:us-east-1:123456789012:secret:new-secret"
    )
    assert connector["SftpConfig"]["TrustedHostKeys"] == ["mock_new_host_key"]


def test_update_connector_not_found(client):
    with pytest.raises(ClientError) as exc:
        client.update_connector(
            ConnectorId="c-01234567890abcdef",
            Url="sftp://example.com",
        )
    assert exc.value.response["Error"]["Code"] == "ResourceNotFoundException"
