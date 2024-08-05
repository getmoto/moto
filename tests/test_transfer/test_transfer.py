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


@mock_aws
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


@mock_aws
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


@mock_aws
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
